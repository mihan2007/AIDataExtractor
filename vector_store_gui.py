# -*- coding: utf-8 -*-
import os
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from typing import Callable, Optional, List

import vector_store_cleanup as vsc


class VectorStoreGUI(tk.Tk):
    """
    Окно выбора файлов и отправки в Vector Store.

    Возможности:
      • Выбор и загрузка файлов с живым логом и замером времени/скорости.
      • Кнопка «Очистить все хранилища» (удаляет файлы и сами хранилища).
    """

    def __init__(self, on_upload: Optional[Callable] = None):
        super().__init__()
        self.title("Vector Store Uploader")
        self.geometry("820x560")

        self.selected_files: List[str] = []
        self.on_upload = on_upload  # upload_to_vector_store(paths, on_progress, wait_index)

        # ---------- Верхняя панель ----------
        top = tk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=8)

        self.btn_select = tk.Button(top, text="Выбрать файлы", command=self.select_files)
        self.btn_select.pack(side=tk.LEFT)

        self.btn_upload = tk.Button(top, text="Отправить в Vector Store", command=self.upload_files)
        self.btn_upload.pack(side=tk.LEFT, padx=8)

        self.btn_cleanup = tk.Button(top, text="Очистить все хранилища", command=self.cleanup_all_stores)
        self.btn_cleanup.pack(side=tk.LEFT, padx=8)

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
        """Пишем в лог UI (и опционально дублируем в консоль)."""
        self.txt_logs.insert(tk.END, msg + "\n")
        self.txt_logs.see(tk.END)
        self.update_idletasks()
        if also_print:
            print(msg, flush=True)

    def _set_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        self.btn_select.config(state=state)
        self.btn_upload.config(state=state)
        self.btn_cleanup.config(state=state)
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

        if not callable(self.on_upload):
            names = [os.path.basename(f) for f in self.selected_files]
            messagebox.showinfo("Отправка файлов",
                                "Файлы были бы отправлены в Vector Store:\n\n" + "\n".join(names))
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
                result_msg = self.on_upload(self.selected_files, on_progress=on_progress, wait_index=False)
                elapsed = time.perf_counter() - start

                speed_kb_s = None
                if total_size_bytes > 0 and elapsed > 0:
                    speed_kb_s = (total_size_bytes / 1024.0) / elapsed

                def done_ui():
                    self._log(f"\n⏱ Время отправки (без индексации): {elapsed:.2f} сек.")
                    if speed_kb_s is not None:
                        self._log(f"⚡ Средняя скорость: {speed_kb_s:.2f} КБ/сек.")
                    final = result_msg + f"\n\n⏱ Время: {elapsed:.2f} сек."
                    if speed_kb_s is not None:
                        final += f"\n⚡ Скорость: {speed_kb_s:.2f} КБ/сек."
                    messagebox.showinfo("Готово", final)

                self.after(0, done_ui)

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
            finally:
                self.after(0, lambda: self._set_busy(False))

        threading.Thread(target=bg_task, daemon=True).start()

    def cleanup_all_stores(self):
        """Полная очистка: удаляет все файлы из каждого Vector Store и сами хранилища."""
        self._set_busy(True)
        self._log("\n🧹 Запускаю очистку всех Vector Stores…")

        def bg_cleanup():
            try:
                api_key = vsc.load_api_key()
                stores = vsc.list_all_vector_stores(api_key)

                if not stores:
                    self.after(0, lambda: self._log("✅ Нет созданных Vector Stores — очищать нечего."))
                    return

                self.after(0, lambda: self._log(f"🔍 Найдено хранилищ: {len(stores)}\n"))

                for store in stores:
                    store_id = store.get("id")
                    name = store.get("name", "(без имени)")
                    self.after(0, lambda n=name, sid=store_id: self._log(f"🗂  Хранилище: {n} ({sid})"))

                    try:
                        files = vsc.list_files(api_key, store_id)
                    except Exception as e:
                        self.after(0, lambda e=e: self._log(f"   ❌ Ошибка получения списка файлов: {e}"))
                        continue

                    for f in files:
                        fid = f.get("id")
                        try:
                            vsc.delete_file(api_key, store_id, fid)
                            self.after(0, lambda fid=fid: self._log(f"   ✅ Файл удалён: {fid}"))
                        except Exception as e:
                            self.after(0, lambda fid=fid, e=e: self._log(f"   ❌ Ошибка удаления файла {fid}: {e}"))

                    try:
                        vsc.delete_vector_store(api_key, store_id)
                        self.after(0, lambda: self._log("   🗑 Хранилище удалено."))
                    except Exception as e:
                        self.after(0, lambda sid=store_id, e=e: self._log(f"   ❌ Ошибка удаления хранилища {sid}: {e}"))

                    self.after(0, lambda: self._log("-" * 50))

                self.after(0, lambda: self._log("\n✨ Все Vector Stores удалены."))
                self.after(0, lambda: messagebox.showinfo("Очистка завершена", "Все Vector Stores удалены."))

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Ошибка очистки", str(e)))
            finally:
                self.after(0, lambda: self._set_busy(False))

        threading.Thread(target=bg_cleanup, daemon=True).start()


if __name__ == "__main__":
    app = VectorStoreGUI(on_upload=None)
    app.mainloop()
