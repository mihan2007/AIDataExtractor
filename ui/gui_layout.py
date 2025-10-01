# -*- coding: utf-8 -*-
"""Legacy layout helpers that mirror :mod:`ui.vector_store_gui` controls."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from infra.config import (
    AUTO_DELETE_DEFAULT_MIN,
    LOG_FONT,
    LOG_TEXT_HEIGHT,
    PAD_X,
    PAD_Y,
    PAD_Y_LOG,
    PAD_ENTRY,
    PAD_CHECK,
    PAD_BTN,
)
from infra import localization as i18n
from infra.localization import translate as T

i18n.reload_language_from_settings()


def build_top_panel(app) -> tk.Frame:
    master = app
    journal_ok = getattr(app, "journal_ok", False)

    top = tk.Frame(master)
    top.pack(fill=tk.X, padx=PAD_X, pady=PAD_Y)

    app.btn_select = tk.Button(top, text=T("button.select_files"), command=getattr(app, "select_files", app.choose_files))
    app.btn_select.pack(side=tk.LEFT)

    app.btn_upload = tk.Button(top, text=T("button.upload"), command=app.upload_files)
    app.btn_upload.pack(side=tk.LEFT, padx=PAD_BTN)

    app.btn_process = tk.Button(top, text=T("button.process"), command=getattr(app, "process_files", app.on_process_click))
    app.btn_process.pack(side=tk.LEFT, padx=PAD_BTN)

    app.btn_show_journal = tk.Button(
        top,
        text=T("button.journal"),
        command=app.show_journal,
        state="normal" if journal_ok else "disabled",
    )
    app.btn_show_journal.pack(side=tk.LEFT, padx=PAD_BTN)

    auto_frame = tk.Frame(top)
    auto_frame.pack(side=tk.RIGHT)

    app.auto_delete_var = getattr(app, "auto_delete_var", tk.BooleanVar(value=True))
    app.delete_delay_var = getattr(app, "delete_delay_var", tk.StringVar(value=str(AUTO_DELETE_DEFAULT_MIN)))

    app.chk_auto_delete = tk.Checkbutton(auto_frame, text=T("checkbox.auto_delete"), variable=app.auto_delete_var)
    app.chk_auto_delete.pack(side=tk.LEFT, padx=PAD_CHECK)

    tk.Label(auto_frame, text=T("label.delete_delay")).pack(side=tk.LEFT)
    app.entry_delete_delay = tk.Entry(auto_frame, width=4, textvariable=app.delete_delay_var)
    app.entry_delete_delay.pack(side=tk.LEFT, padx=PAD_ENTRY)
    return top


def build_log_area(master, app) -> None:
    app.txt_logs = ScrolledText(master, height=LOG_TEXT_HEIGHT, wrap=tk.WORD, font=LOG_FONT)
    app.txt_logs.pack(fill=tk.BOTH, expand=True, padx=PAD_X, pady=PAD_Y_LOG)


def build_status_bar(master, app) -> None:
    bottom = tk.Frame(master)
    bottom.pack(fill=tk.X, padx=PAD_X, pady=(0, PAD_Y))

    if getattr(app, "status", None) is None:
        app.status = tk.StringVar(value=T("status.ready"))

    app.status_bar = tk.Label(bottom, textvariable=app.status, anchor="w")
    app.status_bar.pack(side=tk.LEFT)

    app.progress = ttk.Progressbar(bottom, mode="determinate", length=160)
    app.progress.pack(side=tk.RIGHT)

    return bottom


__all__ = ["build_top_panel", "build_log_area", "build_status_bar"]