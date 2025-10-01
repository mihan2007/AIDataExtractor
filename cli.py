# -*- coding: utf-8 -*-
"""Command-line interface for the Vector Store pipeline with localization."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from uuid import uuid4

import tkinter as tk
from tkinter import filedialog

from core.uploader import upload_to_vector_store_ex
from core.vector_store_query import run_extraction_with_vector_store
from infra.config import DEFAULT_MODEL, SYSTEM_PROMPT_PATH
from infra import localization as i18n
from infra.localization import translate as T

i18n.reload_language_from_settings()


def pick_files_via_dialog() -> list[str]:
    root = tk.Tk()
    root.withdraw()
    try:
        paths = filedialog.askopenfilenames(
            title=T("dialog.select_files.title"),
            filetypes=(
                (T("dialog.select_files.documents"), "*.pdf *.doc *.docx *.xls *.xlsx *.txt"),
                (T("dialog.select_files.all_files"), "*.*"),
            ),
        )
        return list(paths or [])
    finally:
        root.destroy()


def _save_result_record(save_dir: str, store_id: str, clean_json: str) -> str:
    """Persist a copy of the validated extraction result alongside CLI usage."""
    os.makedirs(save_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = uuid4().hex[:6]
    base = f"extract_{stamp}_{(store_id or 'noid').replace('/', '_')}_{suffix}.json"
    out_path = os.path.join(save_dir, base)

    try:
        payload = json.loads(clean_json)
    except Exception:
        payload = {"raw_text": clean_json}

    record = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "phase": "result",
        "store_id": store_id,
        "result": payload,
        "note": "validated",
    }
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(record, fp, ensure_ascii=False, indent=2)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=T("cli.description"))
    parser.add_argument("files", nargs="*", help=T("cli.arg.files"))
    parser.add_argument(
        "--no-wait-index",
        dest="no_wait_index",
        action="store_true",
        help=T("cli.arg.no_wait_index"),
    )
    parser.add_argument(
        "--save-dir",
        dest="save_dir",
        help=T("cli.arg.save_dir"),
    )
    parser.add_argument(
        "--language",
        dest="language",
        choices=i18n.available_languages(),
        help=T("cli.arg.language"),
    )

    args = parser.parse_args()

    if args.language:
        code = i18n.set_language(args.language)
        print(
            T(
                "cli.language_set",
                language_name=i18n.language_name(code),
                language_code=code,
            ),
            flush=True,
        )
    else:
        i18n.reload_language_from_settings()

    files = args.files or pick_files_via_dialog()
    if not files:
        print(T("cli.no_files"), flush=True)
        sys.exit(0)

    def on_progress(msg: str) -> None:
        print(msg, flush=True)

    print(T("log.upload_start"), flush=True)
    try:
        upload_summary = upload_to_vector_store_ex(
            files=files,
            on_progress=on_progress,
            wait_index=not args.no_wait_index,
        )
    except Exception as exc:
        print(T("cli.upload_error", error=exc), flush=True)
        sys.exit(1)

    store_id = (upload_summary or {}).get("store_id")
    print(T("log.upload_result_header"), flush=True)
    print(upload_summary.get("summary") or upload_summary, flush=True)
    if not store_id:
        sys.exit(2)

    if args.no_wait_index:
        print(T("cli.wait_index_disabled"), flush=True)
        return

    print(T("cli.processing_start"), flush=True)
    try:
        clean_json = run_extraction_with_vector_store(
            store_id=store_id,
            user_instruction=T("prompt.extract_instruction"),
            model=DEFAULT_MODEL,
            system_prompt_path=SYSTEM_PROMPT_PATH,
        )
        try:
            pretty = json.dumps(json.loads(clean_json), ensure_ascii=False, indent=2)
        except Exception:
            pretty = clean_json
        print(T("log.extraction_header"), flush=True)
        print(pretty, flush=True)
        print(T("log.extraction_footer"), flush=True)

        if args.save_dir:
            out_path = _save_result_record(args.save_dir, store_id, clean_json)
            print(T("cli.saved_result", path=out_path), flush=True)

    except Exception as exc:
        print(T("cli.processing_error", error=exc), flush=True)


if __name__ == "__main__":
    main()