import tkinter as tk
from tkinter.scrolledtext import ScrolledText

from config import (
    WINDOW_SIZE, WINDOW_TITLE,
    AUTO_DELETE_DEFAULT_MIN, AUTO_DELETE_MIN_LIMIT,
    LOG_FONT, LOG_TEXT_HEIGHT,
    PAD_X, PAD_Y, PAD_Y_LOG, PAD_ENTRY, PAD_CHECK, PAD_BTN,
    JOURNAL_WINDOW_SIZE, JOURNAL_MAX_RECORDS
)

def build_top_panel(master, app, journal_ok: bool):
    """Создаёт верхнюю панель управления и возвращает контейнер Frame."""
    top = tk.Frame(master)
    top.pack(fill=tk.X, padx=PAD_X, pady=PAD_Y)

    # Кнопка выбора файлов
    app.btn_select = tk.Button(top, text="Выбрать файлы", command=app.select_files)
    app.btn_select.pack(side=tk.LEFT)

    # Кнопка отправки в Vector Store
    app.btn_upload = tk.Button(top, text="Отправить в Vector Store", command=app.upload_files)
    app.btn_upload.pack(side=tk.LEFT, padx=PAD_BTN)

    # Кнопка обработки (по умолчанию выключена)
    app.btn_process = tk.Button(top, text="Обработать", state="disabled", command=app.on_process_click)
    app.btn_process.pack(side=tk.LEFT, padx=PAD_BTN)

    # Кнопка журнала
    app.btn_show_journal = tk.Button(
        top,
        text=("Журнал (вкл.)" if journal_ok else "Журнал (модуль не найден)"),
        command=app.show_journal,
        state=("normal" if journal_ok else "disabled"),
    )
    app.btn_show_journal.pack(side=tk.LEFT, padx=PAD_BTN)

    # Блок автоудаления (справа)
    auto_frame = tk.Frame(top)
    auto_frame.pack(side=tk.RIGHT)

    app.auto_delete_var = tk.BooleanVar(value=True)
    app.delete_delay_var = tk.StringVar(value=str(AUTO_DELETE_DEFAULT_MIN))

    tk.Checkbutton(
        auto_frame,
        text="Удалить после обработки",
        variable=app.auto_delete_var
    ).pack(side=tk.LEFT, padx=PAD_CHECK)

    tk.Label(auto_frame, text="Задержка (мин):").pack(side=tk.LEFT)

    tk.Entry(
        auto_frame,
        width=4,
        textvariable=app.delete_delay_var
    ).pack(side=tk.LEFT, padx=PAD_ENTRY)

    return top



def build_log_area(master, app):
    app.txt_logs = ScrolledText(master, height=LOG_TEXT_HEIGHT, wrap=tk.WORD, font=LOG_FONT)
    app.txt_logs.pack(fill=tk.BOTH, expand=True, padx=PAD_X, pady=PAD_Y_LOG)

def build_status_bar(master, app):
    bottom = tk.Frame(master)
    bottom.pack(fill=tk.X, padx=PAD_X, pady=(0, PAD_Y))
    app.status = tk.StringVar(value="Готово")
    tk.Label(bottom, textvariable=app.status, anchor="w").pack(side=tk.LEFT)
    return bottom