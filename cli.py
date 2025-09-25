# -*- coding: utf-8 -*-
import argparse
import sys
import json
import os
from datetime import datetime
from uuid import uuid4

import tkinter as tk
from tkinter import filedialog

from core.uploader import upload_to_vector_store_ex
from core.vector_store_query import run_extraction_with_vector_store  # пишет в журнал через append_result_entry:contentReference[oaicite:4]{index=4}
from infra.config import DEFAULT_MODEL, SYSTEM_PROMPT_PATH

def pick_files_via_dialog() -> list[str]:
    root = tk.Tk()
    root.withdraw()
    try:
        paths = filedialog.askopenfilenames(
            title="Выберите файлы для загрузки",
            filetypes=(
                ("Документы", "*.pdf *.doc *.docx *.xls *.xlsx *.txt"),
                ("Все файлы", "*.*"),
            ),
        )
        return list(paths or [])
    finally:
        root.destroy()

def _save_result_record(save_dir: str, store_id: str, clean_json: str) -> str:
    """
    Сохраняет в отдельный файл запись того же вида, что и в журнале:
    {"ts": "...", "phase": "result", "result": <parsed clean_json>, "note": "validated"}
    Возвращает путь к созданному файлу.
    """
    os.makedirs(save_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = uuid4().hex[:6]
    base = f"extract_{stamp}_{(store_id or 'noid').replace('/', '_')}_{suffix}.json"
    out_path = os.path.join(save_dir, base)

    try:
        payload = json.loads(clean_json)
    except Exception:
        # на всякий случай — если это не JSON (не должно быть, но пусть будет устойчиво)
        payload = {"raw_text": clean_json}

    record = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "phase": "result",
        "result": payload,
        "note": "validated"
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    return out_path

def main():
    parser = argparse.ArgumentParser(
        description="CLI загрузки и обработки файлов через Vector Store"
    )
    parser.add_argument("files", nargs="*", help="Пути к файлам.")
    parser.add_argument(
        "--no-wait-index",
        dest="no_wait_index",
        action="store_true",
        help="Не ждать индексацию (по умолчанию ждём).",
    )
    parser.add_argument(
        "--save-dir",
        dest="save_dir",
        help="Папка, куда дополнительно сохранить запись результата (как в журнале).",
    )
    args = parser.parse_args()

    files = args.files or pick_files_via_dialog()
    if not files:
        print("Файлы не выбраны. Выход.", flush=True)
        sys.exit(0)

    def on_progress(msg: str):
        print(msg, flush=True)

    print("— Начинаю загрузку…", flush=True)
    try:
        result = upload_to_vector_store_ex(
            files=files,
            on_progress=on_progress,
            wait_index=not args.no_wait_index,
        )
    except Exception as e:
        print(f"Ошибка: {e}", flush=True)
        sys.exit(1)

    store_id = result.get("store_id")
    print("\n=== РЕЗУЛЬТАТ ЗАГРУЗКИ ===", flush=True)
    print(result.get("summary") or result, flush=True)
    if not store_id:
        sys.exit(2)

    if args.no_wait_index:
        print("⚠ Индексация отключена (--no-wait-index). Обработка не запускается.", flush=True)
        return

    print("\n— Запускаю обработку по системному промпту…", flush=True)
    try:
        clean_json = run_extraction_with_vector_store(
            store_id=store_id,
            user_instruction="Извлеки данные строго по системному промпту.",
            model=DEFAULT_MODEL,
            system_prompt_path=SYSTEM_PROMPT_PATH,
        )
        # Красиво в консоль
        try:
            pretty = json.dumps(json.loads(clean_json), ensure_ascii=False, indent=2)
        except Exception:
            pretty = clean_json
        print("\n=== РЕЗУЛЬТАТ ИЗВЛЕЧЕНИЯ (JSON, валидация Pydantic) ===", flush=True)
        print(pretty, flush=True)
        print("=== КОНЕЦ РЕЗУЛЬТАТА ===\n", flush=True)

        # Дополнительное сохранение «как в журнале», если задано
        if args.save_dir:
            out_path = _save_result_record(args.save_dir, store_id, clean_json)
            print(f"💾 Результат также сохранён: {out_path}", flush=True)

    except Exception as e:
        print(f"Ошибка обработки: {e}", flush=True)

if __name__ == "__main__":
    main()
