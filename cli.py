# -*- coding: utf-8 -*-
import argparse
import sys
import json
import tkinter as tk
from tkinter import filedialog

from core.uploader import upload_to_vector_store_ex          # загрузка + индексация
from core.vector_store_query import run_extraction_with_vector_store  # извлечение JSON
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
    args = parser.parse_args()

    files = args.files or pick_files_via_dialog()
    if not files:
        print("Файлы не выбраны. Выход.", flush=True)
        sys.exit(0)

    def on_progress(msg: str):
        # Дублирует прогресс в консоль
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

    # Автоматическая обработка — как в UI
    print("\n— Запускаю обработку по системному промпту…", flush=True)
    try:
        clean_json = run_extraction_with_vector_store(
            store_id=store_id,
            user_instruction="Извлеки данные строго по системному промпту.",
            model=DEFAULT_MODEL,
            system_prompt_path=SYSTEM_PROMPT_PATH,
        )
        try:
            pretty = json.dumps(json.loads(clean_json), ensure_ascii=False, indent=2)
        except Exception:
            pretty = clean_json

        print("\n=== РЕЗУЛЬТАТ ИЗВЛЕЧЕНИЯ (JSON, валидация Pydantic) ===", flush=True)
        print(pretty, flush=True)
        print("=== КОНЕЦ РЕЗУЛЬТАТА ===\n", flush=True)

    except Exception as e:
        print(f"Ошибка обработки: {e}", flush=True)

if __name__ == "__main__":
    main()
