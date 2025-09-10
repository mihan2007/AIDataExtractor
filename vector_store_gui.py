# === Стандартная библиотека ===
import os
import time
import json
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel
from tkinter.scrolledtext import ScrolledText
from typing import Optional, List

# === Локальные модули проекта ===
from config import SYSTEM_PROMPT_PATH, DEFAULT_MODEL
from vector_store_query import run_extraction_with_vector_store
from uploader import upload_to_vector_store_ex
from vector_store_cleanup import cleanup_store


class VectorStoreGUI(tk.Tk):
    """
    GUI для загрузки документов в Vector Store и извлечения данных
    по системному промту (tender_extractor_system.prompt.md) с помощью file_search.
    Лог работы и результат в виде JSON выводятся в этом же окне.
    """

    def __init__(self):
        super().__init__()
        self.title("Vector Store Uploader")
        self.geometry("900x640")

        self.selected_files: List[str] = []
        self.store_id: Optional[str] = None  # сюда положим ID созданного векторного хранилища

        # ---------- Верхняя панель ----------
        top = tk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=8)

        self.btn_select = tk.Button(top, text="Выбрать файлы", command=self.select_files)
        self.btn_select.pack(side=tk.LEFT)

        self.btn_upload = tk.Button(top, text="Отправить в Vector Store", command=self.upload_files)
        self.btn_upload.pack(side=tk.LEFT, padx=8)

        # Кнопка "Обработать" (изначально выключена; но обработка также запускается автоматически после загрузки)
        self.btn_process = tk.Button(top, text="Обработать", state="disabled", command=self.on_process_click)
        self.btn_process.pack(side=tk.LEFT, padx=8)

        # Автоудаление: чекбокс + задержка (мин)
        auto_frame = tk.Frame(top)
        auto_frame.pack(side=tk.RIGHT)
        self.auto_delete_var = tk.BooleanVar(value=False)
        # значение по умолчанию = 30 минут
        self.delete_delay_var = tk.StringVar(value="30")
        tk.Checkbutton(auto_frame, text="Удалить после обработки",
                       variable=self.auto_delete_var).pack(side=tk.LEFT, padx=(8, 4))
        tk.Label(auto_frame, text="Задержка (мин):").pack(side=tk.LEFT)
        tk.Entry(auto_frame, width=4, textvariable=self.delete_delay_var).pack(side=tk.LEFT, padx=(4, 0))

        # ---------- Поле логов ----------
        self.txt_logs = ScrolledText(self, height=26, wrap=tk.WORD, font=("Consolas", 10))
        self.txt_logs.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        # ---------- Панель статуса ----------
        bottom = tk.Frame(self)
        bottom.pack(fill=tk.X, padx=10, pady=(0, 8))

        self.status = tk.StringVar(value="Готово")
        tk.Label(bottom, textvariable=self.status, anchor="w").pack(side=tk.LEFT)

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

                speed_kb_s = None
                if total_size_bytes > 0 and elapsed > 0:
                    speed_kb_s = (total_size_bytes / 1024.0) / elapsed

                # --- сохраняем store_id и включаем кнопку "Обработать"
                self.store_id = (result or {}).get("store_id")
                if self.store_id:
                    self._log(f"✅ Получен Store ID: {self.store_id}")
                else:
                    self._log("⚠️ Загрузка завершена, но store_id не получен.")

                # Автоудаление по желанию
                if self.auto_delete_var.get() and self.store_id:
                    try:
                        delay_min = int(self.delete_delay_var.get().strip() or "30")
                    except ValueError:
                        delay_min = 30

                    # Минимальная задержка = 1 минута
                    if delay_min < 1:
                        self._log("⚠️ Задержка меньше 1 минуты недопустима. Используется 30 минут.")
                        delay_min = 30

                    def delayed_cleanup():
                        try:
                            if delay_min > 0:
                                time.sleep(delay_min * 60)
                            cleanup_store(self.store_id)
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


if __name__ == "__main__":
    app = VectorStoreGUI()
    app.mainloop()
