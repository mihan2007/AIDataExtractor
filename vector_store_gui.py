# -*- coding: utf-8 -*-
import os
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

class VectorStoreGUI(tk.Tk):
    """Окно выбора файлов и отправки в Vector Store (UI-слой)."""
    def __init__(self, on_upload=None):
        super().__init__()
        self.title("Vector Store Uploader")
        self.geometry("700x480")
        self.selected_files = []
        self.on_upload = on_upload  # колбэк в бизнес-логику (upload_to_vector_store)

        # Кнопка выбора файлов
        self.btn_select = tk.Button(self, text="Выбрать файлы", command=self.select_files)
        self.btn_select.pack(pady=10)

        # Окно текста: список файлов + логи прогресса
        self.txt_files = ScrolledText(self, height=18)
        self.txt_files.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Кнопка отправки
        self.btn_upload = tk.Button(self, text="Отправить в Vector Store", command=self.upload_files)
        self.btn_upload.pack(pady=10)

    def select_files(self):
        filetypes = [
            ("Документы", "*.pdf *.docx *.doc *.xlsx *.xls *.txt *.md"),
            ("Все файлы", "*.*")
        ]
        paths = filedialog.askopenfilenames(title="Выберите документы", filetypes=filetypes)
        if not paths:
            return
        self.selected_files = list(paths)
        self.txt_files.delete("1.0", tk.END)
        self.txt_files.insert(tk.END, "Выбраны файлы:\n")
        for p in self.selected_files:
            self.txt_files.insert(tk.END, f" - {os.path.basename(p)}\n")

    def upload_files(self):
        if not self.selected_files:
            messagebox.showwarning("Нет файлов", "Сначала выберите файлы")
            return

        if not callable(self.on_upload):
            names = [os.path.basename(f) for f in self.selected_files]
            messagebox.showinfo("Отправка файлов",
                                "Файлы были бы отправлены в Vector Store:\n\n" + "\n".join(names))
            return

        # Подсчёт общего размера (для скорости)
        total_size_bytes = 0
        try:
            for p in self.selected_files:
                total_size_bytes += os.path.getsize(p)
        except OSError:
            total_size_bytes = 0  # если вдруг один из файлов недоступен

        # Блокируем кнопку на время фоновой операции
        self.btn_upload.config(state="disabled")
        self.txt_files.insert(tk.END, "\n— Начинаю загрузку…\n")
        self.txt_files.see(tk.END)

        # Колбэк для живого лога из uploader.py
        def on_progress(msg: str):
            self.txt_files.insert(tk.END, msg + "\n")
            self.txt_files.see(tk.END)
            # Обновляем UI без блокировки
            self.update_idletasks()

        def bg_task():
            start = time.perf_counter()
            try:
                # Не ждём индексацию, чтобы GUI не зависал
                result_msg = self.on_upload(self.selected_files, on_progress=on_progress, wait_index=False)
                elapsed = time.perf_counter() - start

                # Подсчёт скорости (если удалось определить размер)
                speed_kb_s = None
                if total_size_bytes > 0 and elapsed > 0:
                    speed_kb_s = (total_size_bytes / 1024.0) / elapsed

                # Печать итогов в лог
                self.after(0, lambda: self.txt_files.insert(
                    tk.END,
                    f"\n⏱ Время отправки (без индексации): {elapsed:.2f} сек.\n"
                    + (f"⚡ Средняя скорость: {speed_kb_s:.2f} КБ/сек.\n" if speed_kb_s is not None else "")
                ))
                self.after(0, self.txt_files.see, tk.END)

                # Диалоговое окно с результатом
                final_msg = result_msg
                final_msg += f"\n\n⏱ Время: {elapsed:.2f} сек."
                if speed_kb_s is not None:
                    final_msg += f"\n⚡ Скорость: {speed_kb_s:.2f} КБ/сек."
                self.after(0, lambda: messagebox.showinfo("Готово", final_msg))

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
            finally:
                # Разблокируем кнопку в главном потоке
                self.after(0, lambda: self.btn_upload.config(state="normal"))

        threading.Thread(target=bg_task, daemon=True).start()
