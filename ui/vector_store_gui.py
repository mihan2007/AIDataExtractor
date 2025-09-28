# vector_store_gui.py — облегчённый контроллер GUI
import os
import time
import threading
import tkinter as tk
import json
from tkinter import filedialog, messagebox, Toplevel
from tkinter.scrolledtext import ScrolledText
from typing import Optional, List, Tuple
from pydantic import ValidationError
from tkinter import messagebox
from core.pipeline import run_pipeline




from infra.config import (
    SYSTEM_PROMPT_PATH, DEFAULT_MODEL,
    WINDOW_SIZE, WINDOW_TITLE,
    AUTO_DELETE_DEFAULT_MIN, AUTO_DELETE_MIN_LIMIT,
    LOG_FONT, PAD_X, PAD_Y, JOURNAL_WINDOW_SIZE, JOURNAL_MAX_RECORDS
)

# Опциональный журнал
try:
    from infra.log_journal import append_upload_entry, read_last
    _JOURNAL_OK = True
except Exception:
    append_upload_entry = None  # type: ignore
    read_last = None            # type: ignore
    _JOURNAL_OK = False

# Бэкенд-операции
from core.uploader import upload_to_vector_store_ex
from core.vector_store_cleanup import schedule_cleanup
from core.vector_store_query import run_extraction_with_vector_store


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
        if also_print:
            print(msg, flush=True)

    def _set_busy(self, busy: bool):
        if busy:
            self.config(cursor="watch")
        else:
            self.config(cursor="")
        self.update_idletasks()

    # ====================== Колбэки UI ======================
    def choose_files(self):
        """Выбор файлов для загрузки."""
        paths = filedialog.askopenfilenames(
            title="Выберите файлы",
            filetypes=(("Документы", "*.pdf *.doc *.docx *.xls *.xlsx *.txt"), ("Все файлы", "*.*")),
        )
        if not paths:
            return

        self.selected_files = list(paths)
        if self.txt_logs:
            self.txt_logs.delete("1.0", tk.END)

        self._log("Выбраны файлы:")
        for p in self.selected_files:
            self._log(f" • {os.path.basename(p)}")

    def upload_files(self):
        """Загрузка + ожидание индексации + обработка через общий pipeline."""
        if not self.selected_files:
            messagebox.showwarning("Нет файлов", "Сначала выберите файлы")
            return

        self._set_busy(True)
        self._log("\n— Начинаю загрузку…")

        def on_progress(msg: str):
            # Пишем в UI и, благодаря self._log, дублируем в консоль
            self._log(msg)

        def worker():
            try:
                res = run_pipeline(
                    self.selected_files,
                    wait_index=True,  # как и раньше — сразу ждём индексацию
                    save_dir=None,  # при желании сюда можно подставить путь для доп. сохранения
                    on_progress=on_progress,
                )
                self.store_id = res.store_id

                # Готовим красивый вывод результата (как и раньше)
                pretty = None
                if res.clean_json:
                    try:
                        import json
                        pretty = json.dumps(json.loads(res.clean_json), ensure_ascii=False, indent=2)
                    except Exception:
                        pretty = res.clean_json

                def done_ui():
                    if self.btn_process:
                        self.btn_process.config(state="normal")
                    if self.store_id:
                        self.status.set(f"Готово. Store ID: {self.store_id}")
                    else:
                        self.status.set("Готово.")

                    if pretty:
                        self._log("\n=== РЕЗУЛЬТАТ ИЗВЛЕЧЕНИЯ (JSON, валидация Pydantic) ===")
                        self._log(pretty)
                        self._log("=== КОНЕЦ РЕЗУЛЬТАТА ===\n")

                self.after(0, done_ui)

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
                self.after(0, lambda: self.status.set("Ошибка."))
            finally:
                self.after(0, lambda: self._set_busy(False))

        import threading
        threading.Thread(target=worker, daemon=True).start()

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
                # Запускаем извлечение по системному промпту
                result_json = run_extraction_with_vector_store(
                    store_id=self.store_id,
                    user_instruction="Извлеки данные строго по системному промпту.",
                    model=DEFAULT_MODEL,
                    system_prompt_path=SYSTEM_PROMPT_PATH,
                )

                # Красиво форматируем JSON для отображения в UI
                try:
                    pretty = json.dumps(json.loads(result_json), ensure_ascii=False, indent=2)
                except Exception:
                    pretty = result_json  # если вдруг пришёл не-JSON, показываем как есть

            except ValidationError as e:
                # Показываем пользователю понятную ошибку валидации
                self.after(0,
                           lambda: self._log("\n❌ Ошибка валидации JSON по схеме из system.prompt.", also_print=False))
                self.after(0, lambda: self._log(json.dumps(e.errors(), ensure_ascii=False, indent=2), also_print=False))
                self.after(0, lambda: messagebox.showerror("Валидация JSON",
                                                           "JSON не соответствует схеме. Подробности — в логах окна."))
                self.after(0, lambda: self.btn_process.config(state="normal") if self.btn_process else None)
                self.after(0, lambda: self.status.set("Ошибка: JSON не соответствует схеме."))
                return

            except Exception as e:
                # Любая иная ошибка обработки
                self.after(0, lambda: messagebox.showerror("Ошибка обработки", str(e)))
                self.after(0, lambda: self.btn_process.config(state="normal") if self.btn_process else None)
                self.after(0, lambda: self.status.set("Ошибка обработки."))
                return

            # Вывод результата в UI (в главном потоке)
            def show_result():
                self.status.set("Обработка завершена.")
                if self.btn_process:
                    self.btn_process.config(state="normal")
                self._log("\n=== РЕЗУЛЬТАТ ИЗВЛЕЧЕНИЯ (JSON, валидация Pydantic) ===")
                self._log(pretty)
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

        text = ScrolledText(top, font=LOG_FONT)
        text.pack(fill=tk.BOTH, expand=True)

        try:
            rows = read_last(JOURNAL_MAX_RECORDS)
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


# ====================== Построение UI ======================

def build_top_panel(app: VectorStoreGUI):
    frame = tk.Frame(app)
    frame.pack(fill=tk.X, padx=PAD_X, pady=PAD_Y)

    btn_sel = tk.Button(frame, text="Выбрать файлы", command=app.choose_files)
    btn_sel.pack(side=tk.LEFT)
    app.btn_select = btn_sel

    btn_up = tk.Button(frame, text="Загрузить", command=app.upload_files)
    btn_up.pack(side=tk.LEFT, padx=(8, 0))
    app.btn_upload = btn_up

    btn_proc = tk.Button(frame, text="Обработать", command=app.on_process_click, state="disabled")
    btn_proc.pack(side=tk.LEFT, padx=(8, 0))
    app.btn_process = btn_proc

    if app.journal_ok:
        btn_j = tk.Button(frame, text="Журнал", command=app.show_journal)
        btn_j.pack(side=tk.LEFT, padx=(8, 0))
        app.btn_show_journal = btn_j


def build_log_area(master: tk.Tk, app: VectorStoreGUI):
    txt = ScrolledText(master, font=LOG_FONT)
    txt.pack(fill=tk.BOTH, expand=True, padx=PAD_X, pady=PAD_Y)
    app.txt_logs = txt


def build_status_bar(master: tk.Tk, app: VectorStoreGUI):
    bar = tk.Frame(master)
    bar.pack(fill=tk.X, padx=PAD_X, pady=PAD_Y)

    lbl = tk.Label(bar, textvariable=app.status, anchor="w")
    lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

    app.status_bar = bar


if __name__ == "__main__":
    app = VectorStoreGUI()
    app.mainloop()
