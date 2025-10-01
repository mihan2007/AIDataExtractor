# -*- coding: utf-8 -*-
"""Tkinter GUI for Vector Store operations with localization support."""
from __future__ import annotations

import json
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from typing import Any, Callable, Dict, List, Optional

from pydantic import ValidationError

from core.pipeline import PipelineResult, run_pipeline
from core.vector_store_query import run_extraction_with_vector_store
from infra.config import (
    SYSTEM_PROMPT_PATH,
    DEFAULT_MODEL,
    WINDOW_SIZE,
    WINDOW_TITLE,
    AUTO_DELETE_DEFAULT_MIN,
    AUTO_DELETE_MIN_LIMIT,
    LOG_FONT,
    PAD_X,
    PAD_Y,
    JOURNAL_WINDOW_SIZE,
    JOURNAL_MAX_RECORDS,
)
from infra import localization as i18n

i18n.reload_language_from_settings()
T = i18n.translate

try:
    from infra.log_journal import append_upload_entry, read_last  # type: ignore
    _JOURNAL_OK = True
except Exception:  # pragma: no cover - optional dependency
    append_upload_entry = None  # type: ignore
    read_last = None  # type: ignore
    _JOURNAL_OK = False


class SettingsDialog(Toplevel):
    """Simple settings window to select the interface language."""

    def __init__(self, app: "VectorStoreGUI") -> None:
        super().__init__(app)
        self.app = app
        self._updating = False

        self.title(T("dialog.settings.title"))
        self.geometry("360x200")
        self.resizable(False, False)
        self.transient(app)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._close)

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self._build_widgets()
        self.refresh_texts()
        self.bind("<Escape>", lambda _event: self._close())

    def _build_widgets(self) -> None:
        padding = {"padx": PAD_X, "pady": (PAD_Y, 4)}
        self.lbl_language = tk.Label(self, anchor="w")
        self.lbl_language.grid(row=0, column=0, sticky="w", **padding)

        self.lang_var = tk.StringVar(value=i18n.language_name(i18n.get_language()))
        self.cbo_language = ttk.Combobox(self, state="readonly", textvariable=self.lang_var, width=24)
        self.cbo_language.grid(row=1, column=0, columnspan=2, sticky="we", padx=PAD_X)
        self.cbo_language.bind("<<ComboboxSelected>>", lambda _event: self._on_language_selected())

        self.lbl_hint = tk.Label(self, anchor="w")
        self.lbl_hint.grid(row=2, column=0, columnspan=2, sticky="w", padx=PAD_X, pady=(8, 4))

        self.lbl_applied = tk.Label(self, anchor="w", fg="#008000")
        self.lbl_applied.grid(row=3, column=0, columnspan=2, sticky="w", padx=PAD_X, pady=(0, 8))

        self.btn_close = ttk.Button(self, command=self._close)
        self.btn_close.grid(row=4, column=1, sticky="e", padx=PAD_X, pady=(0, PAD_Y))

    def _on_language_selected(self) -> None:
        if self._updating:
            return
        selected_name = self.lang_var.get()
        code = self._name_to_code.get(selected_name)
        if not code:
            return
        i18n.set_language(code)
        self.refresh_texts()

    def refresh_texts(self) -> None:
        self._updating = True
        try:
            self.title(T("dialog.settings.title"))
            self.lbl_language.config(text=T("settings.language_label"))
            self.lbl_hint.config(text=T("settings.language_hint"))
            self.btn_close.config(text=T("settings.close"))

            codes = list(i18n.available_languages())
            self._code_to_name = {code: i18n.language_name(code) for code in codes}
            self._name_to_code = {name: code for code, name in self._code_to_name.items()}

            values = [self._code_to_name[code] for code in codes]
            self.cbo_language.config(values=values)

            current_code = i18n.get_language()
            self.lang_var.set(self._code_to_name.get(current_code, current_code))
            self.lbl_applied.config(
                text=T(
                    "settings.language_applied",
                    language_name=self._code_to_name.get(current_code, current_code),
                )
            )
        finally:
            self._updating = False

    def _close(self) -> None:
        self.app._settings_closed(self)
        self.destroy()


class VectorStoreGUI(tk.Tk):
    """Main application window for the Vector Store workflow."""

    def __init__(self) -> None:
        super().__init__()
        self.title(T("window.title", default=WINDOW_TITLE))
        self.geometry(WINDOW_SIZE)

        self.journal_ok = _JOURNAL_OK
        self.selected_files: List[str] = []
        self.store_id: Optional[str] = None
        self._last_clean_json: Optional[str] = None

        self.status: tk.StringVar = tk.StringVar()
        self._status_key: Optional[str] = None
        self._status_kwargs: Dict[str, Any] = {}

        self.auto_delete_var: tk.BooleanVar = tk.BooleanVar(value=True)
        self.delete_delay_var: tk.StringVar = tk.StringVar(value=str(AUTO_DELETE_DEFAULT_MIN))

        # UI references
        self.btn_select: Optional[tk.Button] = None
        self.btn_upload: Optional[tk.Button] = None
        self.btn_process: Optional[tk.Button] = None
        self.btn_journal: Optional[tk.Button] = None
        self.btn_settings: Optional[tk.Button] = None
        self.chk_auto_delete: Optional[tk.Checkbutton] = None
        self.lbl_delay: Optional[tk.Label] = None
        self.entry_delay: Optional[tk.Entry] = None
        self.txt_logs: Optional[ScrolledText] = None
        self.status_label: Optional[tk.Label] = None
        self.progress: Optional[ttk.Progressbar] = None
        self.settings_window: Optional[SettingsDialog] = None

        self._build_ui()
        self._apply_language()
        self._set_status("status.ready")

        self._lang_unsub = i18n.register_listener(self._on_language_change)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- UI construction -------------------------------------------------

    def _build_ui(self) -> None:
        self._build_top_panel()
        self._build_log_area()
        self._build_status_bar()

    def _build_top_panel(self) -> None:
        frame = tk.Frame(self)
        frame.pack(fill=tk.X, padx=PAD_X, pady=PAD_Y)

        self.btn_select = tk.Button(frame, command=self.choose_files)
        self.btn_select.pack(side=tk.LEFT)

        self.btn_upload = tk.Button(frame, command=self.upload_files)
        self.btn_upload.pack(side=tk.LEFT, padx=(8, 0))

        self.btn_process = tk.Button(frame, command=self.on_process_click, state=tk.DISABLED)
        self.btn_process.pack(side=tk.LEFT, padx=(8, 0))

        if self.journal_ok:
            self.btn_journal = tk.Button(frame, command=self.show_journal)
            self.btn_journal.pack(side=tk.LEFT, padx=(8, 0))

        self.btn_settings = tk.Button(frame, command=self.open_settings)
        self.btn_settings.pack(side=tk.RIGHT)

        auto_frame = tk.Frame(frame)
        auto_frame.pack(side=tk.RIGHT, padx=(0, 12))

        self.chk_auto_delete = tk.Checkbutton(auto_frame, variable=self.auto_delete_var, command=self._on_auto_delete_toggle)
        self.chk_auto_delete.pack(side=tk.LEFT)

        self.lbl_delay = tk.Label(auto_frame)
        self.lbl_delay.pack(side=tk.LEFT, padx=(6, 0))

        self.entry_delay = tk.Entry(auto_frame, width=4, textvariable=self.delete_delay_var, justify=tk.CENTER)
        self.entry_delay.pack(side=tk.LEFT, padx=(4, 0))

        self._on_auto_delete_toggle()

    def _build_log_area(self) -> None:
        self.txt_logs = ScrolledText(self, font=LOG_FONT)
        self.txt_logs.pack(fill=tk.BOTH, expand=True, padx=PAD_X, pady=PAD_Y)
        self.txt_logs.configure(state=tk.NORMAL)

    def _build_status_bar(self) -> None:
        bar = tk.Frame(self)
        bar.pack(fill=tk.X, padx=PAD_X, pady=(0, PAD_Y))

        self.status_label = tk.Label(bar, textvariable=self.status, anchor="w")
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.progress = ttk.Progressbar(bar, mode="indeterminate", length=160)
        self.progress.pack(side=tk.RIGHT)

    # ---- Localization helpers -------------------------------------------

    def _apply_language(self) -> None:
        self.title(T("window.title", default=WINDOW_TITLE))
        if self.btn_select:
            self.btn_select.config(text=T("button.select_files"))
        if self.btn_upload:
            self.btn_upload.config(text=T("button.upload"))
        if self.btn_process:
            self.btn_process.config(text=T("button.process"))
        if self.btn_journal:
            self.btn_journal.config(text=T("button.journal"))
        if self.btn_settings:
            self.btn_settings.config(text=T("button.settings"))
        if self.chk_auto_delete:
            self.chk_auto_delete.config(text=T("checkbox.auto_delete"))
        if self.lbl_delay:
            self.lbl_delay.config(text=T("label.delete_delay"))
        if self.settings_window:
            self.settings_window.refresh_texts()

    def _refresh_status(self) -> None:
        if self._status_key:
            self.status.set(T(self._status_key, **self._status_kwargs))
        else:
            self.status.set("")

    def _set_status(self, key: str, **kwargs: Any) -> None:
        self._status_key = key
        self._status_kwargs = kwargs
        self.status.set(T(key, **kwargs))

    def _on_language_change(self, _language: str) -> None:
        self._apply_language()
        self._refresh_status()

    # ---- General helpers -------------------------------------------------

    def _on_close(self) -> None:
        if self.settings_window is not None:
            self.settings_window.destroy()
            self.settings_window = None
        if hasattr(self, "_lang_unsub") and self._lang_unsub:
            self._lang_unsub()
            self._lang_unsub = None
        self.destroy()

    def _settings_closed(self, dialog: SettingsDialog) -> None:
        if self.settings_window is dialog:
            self.settings_window = None

    def destroy(self) -> None:  # type: ignore[override]
        if hasattr(self, "_lang_unsub") and self._lang_unsub:
            self._lang_unsub()
            self._lang_unsub = None
        super().destroy()

    def _set_busy(self, busy: bool) -> None:
        if busy:
            if self.progress:
                self.progress.start(10)
            self.config(cursor="watch")
        else:
            if self.progress:
                self.progress.stop()
            self.config(cursor="")
        self.update_idletasks()

    def _set_controls_state(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        for widget in (self.btn_select, self.btn_upload, self.btn_settings):
            if widget is not None:
                widget.config(state=state)
        if self.btn_process is not None:
            # Enable the process button only when store_id is available and UI is enabled
            if enabled and self.store_id:
                self.btn_process.config(state=tk.NORMAL)
            else:
                self.btn_process.config(state=tk.DISABLED)
        self._set_auto_delete_controls_state(enabled)

    def _set_auto_delete_controls_state(self, enabled: bool) -> None:
        if self.chk_auto_delete is not None:
            self.chk_auto_delete.config(state=tk.NORMAL if enabled else tk.DISABLED)
        if self.entry_delay is not None:
            if enabled and self.auto_delete_var.get():
                self.entry_delay.config(state=tk.NORMAL)
            else:
                self.entry_delay.config(state=tk.DISABLED)

    def _on_auto_delete_toggle(self) -> None:
        self._set_auto_delete_controls_state(True)

    def _log(self, msg: str, also_print: bool = True) -> None:
        if self.txt_logs is not None:
            self.txt_logs.insert(tk.END, msg + "\n")
            self.txt_logs.see(tk.END)
        if also_print:
            print(msg, flush=True)

    @staticmethod
    def _format_json(text: str) -> str:
        try:
            return json.dumps(json.loads(text), ensure_ascii=False, indent=2)
        except Exception:
            return text

    def open_settings(self) -> None:
        if self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return
        self.settings_window = SettingsDialog(self)

    # ---- Actions ---------------------------------------------------------

    def choose_files(self) -> None:
        filetypes = (
            (T("dialog.select_files.documents"), "*.pdf *.doc *.docx *.xls *.xlsx *.txt"),
            (T("dialog.select_files.all_files"), "*.*"),
        )
        paths = filedialog.askopenfilenames(title=T("dialog.select_files.title"), filetypes=filetypes)
        if not paths:
            return

        self.selected_files = list(paths)
        self.store_id = None
        self._last_clean_json = None
        if self.btn_process is not None:
            self.btn_process.config(state=tk.DISABLED)
        if self.txt_logs is not None:
            self.txt_logs.delete("1.0", tk.END)

        self._log(T("log.files_selected"))
        for path in self.selected_files:
            self._log(T("log.files_selected_item", filename=os.path.basename(path)))

    def upload_files(self) -> None:
        if not self.selected_files:
            messagebox.showwarning(T("dialog.no_files.title"), T("dialog.no_files.message"))
            return

        delay = self._resolve_auto_delete_delay()

        self._set_controls_state(False)
        self._set_busy(True)
        self._set_status("status.uploading")
        self._log(T("log.upload_start"))

        def on_progress(msg: str) -> None:
            self.after(0, lambda m=msg: self._log(m))

        def worker() -> None:
            try:
                result = run_pipeline(
                    self.selected_files,
                    wait_index=True,
                    save_dir=None,
                    on_progress=on_progress,
                    user_instruction=T("prompt.extract_instruction"),
                    model=DEFAULT_MODEL,
                    system_prompt_path=SYSTEM_PROMPT_PATH,
                    auto_cleanup_min=delay if delay > 0 else 0,
                )
            except Exception as exc:
                self.after(0, lambda e=exc: self._handle_upload_error(e))
            else:
                self.after(0, lambda r=result: self._handle_upload_success(r))
            finally:
                self.after(0, self._finish_upload)

        threading.Thread(target=worker, daemon=True).start()

    def _resolve_auto_delete_delay(self) -> int:
        if not self.auto_delete_var.get():
            return 0
        raw = self.delete_delay_var.get().strip()
        try:
            delay = int(raw)
        except ValueError:
            self._log(T("log.invalid_delay", minutes=AUTO_DELETE_DEFAULT_MIN))
            messagebox.showwarning(
                T("dialog.invalid_delay.title"),
                T("dialog.invalid_delay.message", minimum=AUTO_DELETE_MIN_LIMIT),
            )
            self.delete_delay_var.set(str(AUTO_DELETE_DEFAULT_MIN))
            return AUTO_DELETE_DEFAULT_MIN
        if delay < AUTO_DELETE_MIN_LIMIT:
            self._log(T("log.invalid_delay", minutes=AUTO_DELETE_MIN_LIMIT))
            messagebox.showwarning(
                T("dialog.invalid_delay.title"),
                T("dialog.invalid_delay.message", minimum=AUTO_DELETE_MIN_LIMIT),
            )
            delay = AUTO_DELETE_MIN_LIMIT
            self.delete_delay_var.set(str(delay))
        return delay

    def _handle_upload_success(self, result: PipelineResult) -> None:
        self._log(T("log.upload_complete"))
        self.store_id = result.store_id
        self._last_clean_json = result.clean_json

        if self.store_id:
            self._set_status("status.ready_with_id", store_id=self.store_id)
        else:
            self._set_status("status.ready")

        if result.clean_json:
            pretty = self._format_json(result.clean_json)
            self._log(T("log.extraction_header"))
            self._log(pretty)
            self._log(T("log.extraction_footer"))

        if result.saved_copy:
            self._log(T("log.saved_copy", path=result.saved_copy))

    def _handle_upload_error(self, exc: Exception) -> None:
        messagebox.showerror(T("dialog.error.title"), str(exc))
        self._set_status("status.error")

    def _finish_upload(self) -> None:
        self._set_busy(False)
        self._set_controls_state(True)

    def on_process_click(self) -> None:
        self._process_now()

    def _process_now(self) -> None:
        if not self.store_id:
            messagebox.showerror(T("dialog.error.title"), T("dialog.no_store_id.message"))
            return

        if self.btn_process is not None:
            self.btn_process.config(state=tk.DISABLED)
        self._set_busy(True)
        self._set_status("status.processing")
        self._log(T("log.processing_start"))

        def worker() -> None:
            try:
                result_json = run_extraction_with_vector_store(
                    store_id=self.store_id,
                    user_instruction=T("prompt.extract_instruction"),
                    model=DEFAULT_MODEL,
                    system_prompt_path=SYSTEM_PROMPT_PATH,
                )
            except ValidationError as exc:
                self.after(0, lambda e=exc: self._handle_validation_error(e))
            except Exception as exc:
                self.after(0, lambda e=exc: self._handle_processing_error(e))
            else:
                self.after(0, lambda payload=result_json: self._handle_processing_success(payload))
            finally:
                self.after(0, self._processing_finish)

        threading.Thread(target=worker, daemon=True).start()

    def _handle_processing_success(self, payload: str) -> None:
        self._last_clean_json = payload
        pretty = self._format_json(payload)
        self._log(T("log.extraction_header"))
        self._log(pretty)
        self._log(T("log.extraction_footer"))
        self._set_status("status.processing_done")

    def _handle_validation_error(self, exc: ValidationError) -> None:
        self._log(T("log.validation_error"))
        self._log(json.dumps(exc.errors(), ensure_ascii=False, indent=2), also_print=False)
        messagebox.showerror(T("dialog.validation_error.title"), T("dialog.validation_error.message"))
        self._set_status("status.validation_error")

    def _handle_processing_error(self, exc: Exception) -> None:
        messagebox.showerror(T("dialog.processing_error.title"), str(exc))
        self._set_status("status.processing_error")

    def _processing_finish(self) -> None:
        self._set_busy(False)
        if self.btn_process is not None:
            if self.store_id:
                self.btn_process.config(state=tk.NORMAL)
            else:
                self.btn_process.config(state=tk.DISABLED)

    # ---- Journal ---------------------------------------------------------

    def show_journal(self) -> None:
        if not self.journal_ok or read_last is None:
            messagebox.showwarning(T("dialog.journal.title"), T("dialog.journal.missing"))
            return

        top = Toplevel(self)
        top.title(T("journal.window_title"))
        top.geometry(JOURNAL_WINDOW_SIZE)

        text = ScrolledText(top, font=LOG_FONT)
        text.pack(fill=tk.BOTH, expand=True)

        try:
            rows = read_last(JOURNAL_MAX_RECORDS)
        except Exception as exc:  # pragma: no cover - defensive UI path
            top.destroy()
            messagebox.showerror(T("dialog.journal.error_title"), str(exc))
            return

        if not rows:
            text.insert(tk.END, T("journal.empty"))
        else:
            for row in rows:
                try:
                    pretty = json.dumps(row, ensure_ascii=False, indent=2)
                except Exception:
                    pretty = str(row)
                text.insert(tk.END, pretty + "\n\n")
        text.see(tk.END)


__all__ = ["VectorStoreGUI", "SettingsDialog"]