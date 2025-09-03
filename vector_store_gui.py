# -*- coding: utf-8 -*-
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

class VectorStoreGUI(tk.Tk):
    """Окно выбора файлов и отправки в Vector Store (UI-слой)."""
    def __init__(self, on_upload=None):
        super().__init__()
        self.title("Vector Store Uploader")
        self.geometry("600x400")
        self.selected_files = []
        self.on_upload = on_upload  # колбэк в бизнес-логику

        self.btn_select = tk.Button(self, text="Выбрать файлы", command=self.select_files)
        self.btn_select.pack(pady=10)

        self.txt_files = ScrolledText(self, height=10)
        self.txt_files.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.btn_upload = tk.Button(self, text="Отправить в Vector Store", command=self.upload_files)
        self.btn_upload.pack(pady=10)

    def select_files(self):
        filetypes = [("Документы", "*.pdf *.docx"), ("Все файлы", "*.*")]
        paths = filedialog.askopenfilenames(title="Выберите документы", filetypes=filetypes)
        if not paths:
            return
        self.selected_files = list(paths)
        self.txt_files.delete("1.0", tk.END)
        for p in self.selected_files:
            self.txt_files.insert(tk.END, os.path.basename(p) + "\n")

    def upload_files(self):
        if not self.selected_files:
            messagebox.showwarning("Нет файлов", "Сначала выберите файлы")
        else:
            # если передан колбэк — отдаём файлы в бизнес-логику; иначе просто заглушка
            if callable(self.on_upload):
                try:
                    result_msg = self.on_upload(self.selected_files)
                    messagebox.showinfo("Готово", result_msg)
                except Exception as e:
                    messagebox.showerror("Ошибка", str(e))
            else:
                names = [os.path.basename(f) for f in self.selected_files]
                messagebox.showinfo("Отправка файлов",
                                    "Файлы будут отправлены в Vector Store:\n\n" + "\n".join(names))
