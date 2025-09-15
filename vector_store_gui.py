
import os
import time
import json
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel
from tkinter.scrolledtext import ScrolledText
from typing import Optional, List, Tuple

# === Локальные модули ===
from config import SYSTEM_PROMPT_PATH, DEFAULT_MODEL
from vector_store_query import run_extraction_with_vector_store
from uploader import upload_to_vector_store_ex
from vector_store_cleanup import cleanup_store

from config import (
    WINDOW_SIZE, WINDOW_TITLE,
    AUTO_DELETE_DEFAULT_MIN, AUTO_DELETE_MIN_LIMIT,
    LOG_FONT, LOG_TEXT_HEIGHT,
    PAD_X, PAD_Y, PAD_Y_LOG, PAD_ENTRY, PAD_CHECK,
    JOURNAL_WINDOW_SIZE, JOURNAL_MAX_RECORDS, PAD_BTN
)

from gui_layout import build_top_panel, build_log_area, build_status_bar

# Журнал — импортируем опционально, чтобы GUI не падал, если файл пока не создан
try:
    from log_journal import append_upload_entry, read_last
    _JOURNAL_OK = True
except Exception as _e:
    append_upload_entry = None  # type: ignore
    read_last = None            # type: ignore
    _JOURNAL_OK = False


class VectorStoreGUI(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_SIZE)

        self.selected_files: List[str] = []
        self.store_id: Optional[str] = None  # сюда положим ID созданного векторного хранилища

        build_top_panel(self, self, _JOURNAL_OK)
        build_log_area(self, self)
        build_status_bar(self, self)

    # ====================== Вспомогательные методы ======================

    def _log(self, msg: str, also_print: bool = True):
        self.txt_logs.insert(tk.END, msg + "\n")
        self.txt_logs.see(tk.END)
        self.update_idletasks()
        if also_print:
            print(msg, flush=True)

    def _set_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        self.btn_select.config(state=state)
        self.btn_upload.config(state=state)
        # Кнопку "Обработать" включаем только если есть store_id
        self.btn_process.config(state=state if self.store_id else "disabled")
        self.status.set("Выполняется…" if busy else "Готово")
        self.update_idletasks()

    # ====================== Обработчики UI ======================

    def select_files(self):
        filetypes = [
            ("Документы", "*.pdf *.docx *.doc *.xlsx *.xls *.txt *.md"),
            ("Все файлы", "*.*"),
        ]
        paths = filedialog.askopenfilenames(title="Выберите документы", filetypes=filetypes)
        if not paths:
            return

        self.selected_files = list(paths)
        self.txt_logs.delete("1.0", tk.END)

        self._log("Выбраны файлы:")
        for p in self.selected_files:
            self._log(f" • {os.path.basename(p)}")

    def upload_files(self):
        if not self.selected_files:
            messagebox.showwarning("Нет файлов", "Сначала выберите файлы")
            return

        try:
            total_size_bytes = sum(os.path.getsize(p) for p in self.selected_files)
        except OSError:
            total_size_bytes = 0

        self._set_busy(True)
        self._log("\n— Начинаю загрузку…")

        def on_progress(msg: str):
            self._log(msg, also_print=False)

        def bg_task():
            start = time.perf_counter()
            try:
                # ВАЖНО: ждём индексацию, чтобы file_search видел контент
                result = upload_to_vector_store_ex(
                    self.selected_files,
                    on_progress=on_progress,
                    wait_index=True,   # ← ключевой флаг
                )
                elapsed = time.perf_counter() - start

                speed_kb_s: Optional[float] = None
                if total_size_bytes > 0 and elapsed > 0:
                    speed_kb_s = (total_size_bytes / 1024.0) / elapsed

                # --- сохраняем store_id и включаем кнопку "Обработать"
                self.store_id = (result or {}).get("store_id")
                if self.store_id:
                    self._log(f"✅ Получен Store ID: {self.store_id}")
                else:
                    self._log("⚠️ Загрузка завершена, но store_id не получен.")

                # === ЖУРНАЛ: запись этапа загрузки ===
                if _JOURNAL_OK and append_upload_entry is not None:
                    try:
                        files_info: List[Tuple[str, int]] = []
                        for p in self.selected_files:
                            try:
                                files_info.append((p, os.path.getsize(p)))
                            except OSError:
                                files_info.append((p, 0))
                        append_upload_entry(
                            store_id=self.store_id,
                            files=files_info,
                            elapsed_sec=elapsed,
                            avg_speed_kb_s=speed_kb_s if speed_kb_s is not None else None,
                        )
                        self._log("📝 Запись о загрузке добавлена в журнал.", also_print=False)
                    except Exception as _log_err:
                        self._log(f"⚠️ Не удалось записать журнал (upload): {_log_err}", also_print=False)

                # Автоудаление по желанию
                if self.auto_delete_var.get() and self.store_id:
                    try:
                        delay_min = int(self.delete_delay_var.get().strip() or AUTO_DELETE_DEFAULT_MIN)
                    except ValueError:
                        delay_min = AUTO_DELETE_DEFAULT_MIN

                    # Минимальная задержка = 1 минута
                    if delay_min < AUTO_DELETE_MIN_LIMIT:
                        self._log("⚠️ Задержка меньше 1 минуты недопустима. Используется 30 минут.")
                        delay_min = AUTO_DELETE_DEFAULT_MIN

                    def delayed_cleanup():
                        try:
                            if delay_min > 0:
                                time.sleep(delay_min * 60)
                            cleanup_store(self.store_id)  # type: ignore[arg-type]
                            self.after(0, lambda: self._log(f"🗑 Хранилище {self.store_id} удалено."))
                        except Exception as e:
                            self.after(0, lambda err=e: self._log(f"❌ Ошибка удаления {self.store_id}: {err}"))

                    threading.Thread(target=delayed_cleanup, daemon=True).start()

                def done_ui():
                    self._log(f"\n⏱ Время отправки (с ожиданием индексации): {elapsed:.2f} сек.")
                    if speed_kb_s is not None:
                        self._log(f"⚡ Средняя скорость: {speed_kb_s:.2f} КБ/сек.")
                    # Обновляем статус и активность кнопки "Обработать"
                    if self.store_id:
                        self.status.set(f"Загрузка завершена. Store ID: {self.store_id}")
                        self.btn_process.config(state="normal")
                        self._log("\n— Запускаю обработку по системному промту…")
                        # Автообработка сразу после загрузки
                        self._process_now()
                    else:
                        self.status.set("Загрузка завершена, но store_id не получен.")
                        self.btn_process.config(state="disabled")

                    # Инфо из uploader (если есть)
                    if result and "summary" in result:
                        messagebox.showinfo("Готово", result["summary"])

                self.after(0, done_ui)

            except Exception as e:
                self.after(0, lambda err=e: messagebox.showerror("Ошибка", str(err)))
            finally:
                self.after(0, lambda: self._set_busy(False))

        threading.Thread(target=bg_task, daemon=True).start()

    def on_process_click(self):
        # Ручной запуск обработки по кнопке
        self._process_now()

    # ====================== Обработка через системный промт ======================

    def _process_now(self):
        """Запустить обработку через Responses API и вывести JSON в это же окно."""
        if not self.store_id:
            messagebox.showerror("Ошибка", "Сначала загрузите файлы и получите Store ID.")
            return

        self.btn_process.config(state="disabled")
        self.status.set("Обработка по системному промту…")

        def worker():
            try:
                json_text = run_extraction_with_vector_store(
                    store_id=self.store_id,
                    user_instruction="Извлеки данные строго по системному промту.",
                    model=DEFAULT_MODEL,
                    system_prompt_path=SYSTEM_PROMPT_PATH,
                )
            except Exception as e:
                self.after(0, lambda err=e: messagebox.showerror("Ошибка обработки", str(err)))
                self.after(0, lambda: self.btn_process.config(state="normal"))
                self.after(0, lambda: self.status.set("Ошибка обработки."))
                return

            def show_result():
                self.status.set("Обработка завершена.")
                self.btn_process.config(state="normal")
                # Пытаемся красиво форматировать JSON
                try:
                    pretty = json.dumps(json.loads(json_text), ensure_ascii=False, indent=2)
                except Exception:
                    pretty = json_text
                self._log("\n=== РЕЗУЛЬТАТ ИЗВЛЕЧЕНИЯ (JSON) ===")
                self._log(pretty, also_print=False)
                self._log("=== КОНЕЦ РЕЗУЛЬТАТА ===\n")

            self.after(0, show_result)

        threading.Thread(target=worker, daemon=True).start()

    # ====================== Просмотр журнала ======================

    def show_journal(self):
        """Показать последние N записей журнала в отдельном окне."""
        if not _JOURNAL_OK or read_last is None:
            messagebox.showwarning("Журнал", "Модуль log_journal.py не найден.")
            return

        # Берём последние 100 записей
        entries = []
        try:
            entries = read_last(JOURNAL_MAX_RECORDS)  # type: ignore[call-arg]
        except Exception as e:
            messagebox.showerror("Журнал", f"Не удалось прочитать журнал: {e}")
            return

        win = Toplevel(self)
        win.title("Журнал (последние записи)")
        win.geometry(JOURNAL_WINDOW_SIZE)

        txt = ScrolledText(win, wrap=tk.WORD, font=("Consolas", 10))
        txt.pack(fill=tk.BOTH, expand=True)

        if not entries:
            txt.insert(tk.END, "Журнал пуст или файл ещё не создан.\n")
        else:
            for row in entries:
                try:
                    txt.insert(tk.END, json.dumps(row, ensure_ascii=False, indent=2) + "\n\n")
                except Exception:
                    txt.insert(tk.END, f"{row}\n\n")
        txt.see(tk.END)


if __name__ == "__main__":
    app = VectorStoreGUI()
    app.mainloop()
