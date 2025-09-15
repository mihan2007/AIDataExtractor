# vector_store_gui.py — облегчённый контроллер GUI
import os
import time
import json
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel
from tkinter.scrolledtext import ScrolledText
from typing import Optional, List, Tuple

from config import (
    SYSTEM_PROMPT_PATH, DEFAULT_MODEL,
    WINDOW_SIZE, WINDOW_TITLE,
    AUTO_DELETE_DEFAULT_MIN, AUTO_DELETE_MIN_LIMIT,
    LOG_FONT, LOG_TEXT_HEIGHT,
    PAD_X, PAD_Y, PAD_Y_LOG, PAD_ENTRY, PAD_CHECK, PAD_BTN,
    JOURNAL_WINDOW_SIZE, JOURNAL_MAX_RECORDS
)

# Сборка UI
from gui_layout import build_top_panel, build_log_area, build_status_bar

# Опциональный журнал
try:
    from log_journal import append_upload_entry, read_last
    _JOURNAL_OK = True
except Exception:
    append_upload_entry = None  # type: ignore
    read_last = None            # type: ignore
    _JOURNAL_OK = False

# Бэкенд-операции
from uploader import upload_to_vector_store_ex
from vector_store_cleanup import schedule_cleanup
from vector_store_query import run_extraction_with_vector_store


class VectorStoreGUI(tk.Tk):
    """
    Тонкий контроллер:
      - хранит состояние (selected_files, store_id),
      - делегирует операции в uploader/vector_store_query/vector_store_cleanup,
      - обновляет UI (логи/кнопки/статус).
    """
    def __init__(self):
        super().__init__()
        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_SIZE)

        # Флаг для build_top_panel(app)
        self.journal_ok = _JOURNAL_OK

        # ---------- Данные/состояние ----------
        self.selected_files: List[str] = []
        self.store_id: Optional[str] = None

        # ---------- Tk-переменные ----------
        self.status: tk.StringVar = tk.StringVar(value="Готово")
        self.auto_delete_var: tk.BooleanVar = tk.BooleanVar(value=True)
        self.delete_delay_var: tk.StringVar = tk.StringVar(value=str(AUTO_DELETE_DEFAULT_MIN))

        # ---------- Виджеты (заполнятся билдерами) ----------
        self.btn_select = None
        self.btn_upload = None
        self.btn_process = None
        self.btn_show_journal = None
        self.txt_logs: Optional[ScrolledText] = None
        self.status_bar = None
        self.progress = None

        # ---------- Сборка UI ----------
        build_top_panel(self)           # только app
        build_log_area(self, self)      # master, app
        build_status_bar(self, self)    # master, app

    # ====================== Утилиты UI ======================
    def _log(self, msg: str, also_print: bool = True):
        if self.txt_logs:
            self.txt_logs.insert(tk.END, msg + "\n")
            self.txt_logs.see(tk.END)
            self.update_idletasks()
        if also_print:
            print(msg, flush=True)

    def _set_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        if self.btn_select:  self.btn_select.config(state=state)
        if self.btn_upload:  self.btn_upload.config(state=state)
        if self.btn_process: self.btn_process.config(state=state if self.store_id else "disabled")
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
        if self.txt_logs:
            self.txt_logs.delete("1.0", tk.END)

        self._log("Выбраны файлы:")
        for p in self.selected_files:
            self._log(f" • {os.path.basename(p)}")

    def upload_files(self):
        """Запуск загрузки в Vector Store (делегируется uploader'у)."""
        if not self.selected_files:
            messagebox.showwarning("Нет файлов", "Сначала выберите файлы")
            return

        # Примерная оценка для UI-метрики
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
                result = upload_to_vector_store_ex(
                    self.selected_files,
                    on_progress=on_progress,
                    wait_index=True,  # ждём индексацию, чтобы сразу обрабатывать
                )
                elapsed = time.perf_counter() - start

                speed_kb_s: Optional[float] = None
                if total_size_bytes > 0 and elapsed > 0:
                    speed_kb_s = (total_size_bytes / 1024.0) / elapsed

                # Store ID
                self.store_id = (result or {}).get("store_id")
                if self.store_id:
                    self._log(f"✅ Получен Store ID: {self.store_id}")
                else:
                    self._log("⚠️ Загрузка завершена, но store_id не получен.")

                # ЖУРНАЛ (по возможности)
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

                # Автоудаление — делегировано в vector_store_cleanup
                if self.auto_delete_var.get() and self.store_id:
                    try:
                        delay_min = int(self.delete_delay_var.get().strip() or AUTO_DELETE_DEFAULT_MIN)
                    except ValueError:
                        delay_min = AUTO_DELETE_DEFAULT_MIN

                    if delay_min < AUTO_DELETE_MIN_LIMIT:
                        self._log("⚠️ Задержка меньше 1 минуты недопустима. Используется 30 минут.")
                        delay_min = AUTO_DELETE_DEFAULT_MIN

                    schedule_cleanup(
                        self.store_id,
                        delay_min,
                        on_done=lambda sid: self.after(0, lambda: self._log(f"🗑 Хранилище {sid} удалено.")),
                        on_error=lambda sid, e: self.after(0, lambda: self._log(f"❌ Ошибка удаления {sid}: {e}")),
                    )

                def done_ui():
                    self._log(f"\n⏱ Время отправки (с ожиданием индексации): {elapsed:.2f} сек.")
                    if speed_kb_s is not None:
                        self._log(f"⚡ Средняя скорость: {speed_kb_s:.2f} КБ/сек.")
                    if self.store_id:
                        self.status.set(f"Загрузка завершена. Store ID: {self.store_id}")
                        if self.btn_process:
                            self.btn_process.config(state="normal")
                        self._log("\n— Запускаю обработку по системному промту…")
                        self._process_now()  # автообработка сразу после загрузки
                    else:
                        self.status.set("Загрузка завершена, но store_id не получен.")
                        if self.btn_process:
                            self.btn_process.config(state="disabled")
                    if result and "summary" in result:
                        messagebox.showinfo("Готово", result["summary"])

                self.after(0, done_ui)

            except Exception as e:
                self.after(0, lambda err=e: messagebox.showerror("Ошибка", str(err)))
            finally:
                self.after(0, lambda: self._set_busy(False))

        threading.Thread(target=bg_task, daemon=True).start()

    def on_process_click(self):
        self._process_now()

    def _process_now(self):
        """Запустить извлечение по системному промту (делегируется vector_store_query)."""
        if not self.store_id:
            messagebox.showerror("Ошибка", "Сначала загрузите файлы и получите Store ID.")
            return

        if self.btn_process:
            self.btn_process.config(state="disabled")
        self.status.set("Обработка по системному промту…")

        def worker():
            try:
                pretty_json = run_extraction_with_vector_store(
                    store_id=self.store_id,
                    user_instruction="Извлеки данные строго по системному промту.",
                    model=DEFAULT_MODEL,
                    system_prompt_path=SYSTEM_PROMPT_PATH,
                )
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Ошибка обработки", str(e)))
                self.after(0, lambda: self.btn_process.config(state="normal") if self.btn_process else None)
                self.after(0, lambda: self.status.set("Ошибка обработки."))
                return

            def show_result():
                self.status.set("Обработка завершена.")
                if self.btn_process:
                    self.btn_process.config(state="normal")
                self._log("\n=== РЕЗУЛЬТАТ ИЗВЛЕЧЕНИЯ (JSON) ===")
                self._log(pretty_json, also_print=False)
                self._log("=== КОНЕЦ РЕЗУЛЬТАТА ===\n")

            self.after(0, show_result)

        threading.Thread(target=worker, daemon=True).start()

    # ====================== Просмотр журнала ======================
    def show_journal(self):
        """Показывает последние N записей журнала (если модуль доступен)."""
        if not self.journal_ok or read_last is None:
            messagebox.showwarning("Журнал", "Модуль log_journal.py не найден.")
            return

        top = Toplevel(self)
        top.title("Журнал загрузок")
        top.geometry(JOURNAL_WINDOW_SIZE)

        text = ScrolledText(top, wrap=tk.WORD, font=LOG_FONT)
        text.pack(fill=tk.BOTH, expand=True, padx=PAD_X, pady=PAD_Y)

        try:
            rows = read_last(JOURNAL_MAX_RECORDS)  # type: ignore[misc]
        except Exception as e:
            messagebox.showerror("Журнал", str(e))
            return

        if not rows:
            text.insert(tk.END, "Пока записей нет.\n")
        else:
            for row in rows:
                try:
                    text.insert(tk.END, json.dumps(row, ensure_ascii=False, indent=2) + "\n\n")
                except Exception:
                    text.insert(tk.END, str(row) + "\n\n")

        text.see(tk.END)
