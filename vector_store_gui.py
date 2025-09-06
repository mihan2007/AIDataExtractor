# -*- coding: utf-8 -*-
import os
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from typing import Optional, List

from uploader import upload_to_vector_store_ex
from vector_store_cleanup import cleanup_store


class VectorStoreGUI(tk.Tk):
    """
    Простой режим:
      • Каждый запуск создаёт новое хранилище и грузит в него выбранные файлы.
      • Без выбора существующего хранилища.
      • Опция автоудаления созданного хранилища: через указанную задержку (мин).
      • Минимальная задержка удаления — 1 минута.
    """

    def __init__(self):
        super().__init__()
        self.title("Vector Store Uploader")
        self.geometry("820x580")

        self.selected_files: List[str] = []

        # ---------- Верхняя панель ----------
        top = tk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=8)

        self.btn_select = tk.Button(top, text="Выбрать файлы", command=self.select_files)
        self.btn_select.pack(side=tk.LEFT)

        self.btn_upload = tk.Button(top, text="Отправить в Vector Store", command=self.upload_files)
        self.btn_upload.pack(side=tk.LEFT, padx=8)

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
        self.txt_logs = ScrolledText(self, height=24, wrap=tk.WORD)
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
                result = upload_to_vector_store_ex(
                    self.selected_files,
                    on_progress=on_progress,
                    wait_index=False,  # не ждём индексацию: UI не блокируем
                )
                elapsed = time.perf_counter() - start

                speed_kb_s = None
                if total_size_bytes > 0 and elapsed > 0:
                    speed_kb_s = (total_size_bytes / 1024.0) / elapsed

                store_id = result.get("store_id")

                # Автоудаление по желанию
                if self.auto_delete_var.get() and store_id:
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
                            cleanup_store(store_id)
                            self.after(0, lambda: self._log(f"🗑 Хранилище {store_id} удалено."))
                        except Exception as e:
                            self.after(0, lambda: self._log(f"❌ Ошибка удаления {store_id}: {e}"))

                    threading.Thread(target=delayed_cleanup, daemon=True).start()

                def done_ui():
                    self._log(f"\n⏱ Время отправки (без индексации): {elapsed:.2f} сек.")
                    if speed_kb_s is not None:
                        self._log(f"⚡ Средняя скорость: {speed_kb_s:.2f} КБ/сек.")
                    messagebox.showinfo("Готово", result["summary"])

                self.after(0, done_ui)

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
            finally:
                self.after(0, lambda: self._set_busy(False))

        threading.Thread(target=bg_task, daemon=True).start()


if __name__ == "__main__":
    app = VectorStoreGUI()
    app.mainloop()
