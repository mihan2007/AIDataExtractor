# core/pipeline.py
# -*- coding: utf-8 -*-
"""
Универсальный «pipeline»:
  1) Загружает файлы в Vector Store (создаёт новое хранилище)
  2) (Опционально) ждёт индексацию
  3) Запускает извлечение по system.prompt и file_search
  4) Записывает результат в общий журнал (делает run_extraction_with_vector_store)
  5) (Опционально) сохраняет копию той же записи в указанный каталог
  6) Планирует авто-удаление Vector Store через N минут (по умолчанию — из конфига)
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Callable, Optional, Sequence
from uuid import uuid4

from core.uploader import upload_to_vector_store_ex
from core.vector_store_query import run_extraction_with_vector_store
from core.vector_store_cleanup import schedule_cleanup
from infra.config import (
    DEFAULT_MODEL,
    SYSTEM_PROMPT_PATH,
    AUTO_DELETE_DEFAULT_MIN,
)

# ----------------------------- Вспомогательное -----------------------------

def _ensure_dir(path: str) -> None:
    if path:
        os.makedirs(path, exist_ok=True)

def _unique_filename(prefix: str, store_id: Optional[str], ext: str = "json") -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    sid = (store_id or "noid").replace("/", "_")
    suf = uuid4().hex[:6]
    return f"{prefix}_{stamp}_{sid}_{suf}.{ext}"

def _save_result_record(save_dir: str, store_id: str, clean_json: str) -> str:
    """
    Сохраняет в отдельный файл запись ТАКОГО ЖЕ ВИДА, что и в журнале:
      {
        "ts": "...",
        "phase": "result",
        "result": <валидированный JSON>,
        "note": "validated"
      }
    Возвращает путь к созданному файлу.
    """
    _ensure_dir(save_dir)
    out_path = os.path.join(save_dir, _unique_filename("extract", store_id, "json"))

    try:
        payload = json.loads(clean_json)
    except Exception:
        # fallback (не должен понадобиться, т.к. clean_json уже валидирован)
        payload = {"raw_text": clean_json}

    record = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "phase": "result",
        "result": payload,
        "note": "validated",
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return out_path


# ------------------------------ Результат API ------------------------------

class PipelineResult:
    """
    Итог работы pipeline:
      - store_id: созданное хранилище
      - clean_json: валидированный JSON результата (None, если не ждали индексацию)
      - saved_copy: путь к сохранённой копии записи результата (если save_dir задан)
    """
    def __init__(self, store_id: str, clean_json: Optional[str], saved_copy: Optional[str]):
        self.store_id = store_id
        self.clean_json = clean_json
        self.saved_copy = saved_copy

    def __repr__(self) -> str:
        return f"PipelineResult(store_id={self.store_id!r}, clean_json={bool(self.clean_json)}, saved_copy={self.saved_copy!r})"


# --------------------------------- Pipeline --------------------------------

def run_pipeline(
    files: Sequence[str],
    *,
    wait_index: bool = True,
    save_dir: Optional[str] = None,
    on_progress: Optional[Callable[[str], None]] = None,
    user_instruction: str = "Извлеки данные строго по системному промпту.",
    model: str = DEFAULT_MODEL,
    system_prompt_path: str = SYSTEM_PROMPT_PATH,
    auto_cleanup_min: Optional[int] = AUTO_DELETE_DEFAULT_MIN,
) -> PipelineResult:
    """
    Главная функция сценария. Бросает исключения наверх (UI/CLI сами решают, как их показывать).

    :param files: пути к локальным файлам
    :param wait_index: ждать ли индексацию внутри upload (True = как в UI)
    :param save_dir: если задан — сохранить копию записи результата «как в журнале» в отдельный файл
    :param on_progress: колбэк для прогресса (строка)
    :param user_instruction: текст пользовательской инструкции к system.prompt (можно оставить дефолт)
    :param model: модель для Responses API
    :param system_prompt_path: путь к system.prompt
    :param auto_cleanup_min: через сколько минут удалить созданное хранилище автоматически (None/0 — не удалять)
    :return: PipelineResult
    """
    log = (lambda s: on_progress(s)) if on_progress else (lambda s: None)

    # 1) Загрузка файлов и создание нового Vector Store
    log("— Начинаю загрузку…")
    up = upload_to_vector_store_ex(
        files=files,
        on_progress=on_progress,
        wait_index=wait_index,
    )
    store_id = (up or {}).get("store_id")
    if not store_id:
        raise RuntimeError("Загрузка завершилась без store_id")
    log("Загрузка завершена.")

    # 2) Планируем авто-удаление хранилища
    if auto_cleanup_min and auto_cleanup_min > 0:
        try:
            schedule_cleanup(
                vector_store_id=store_id,
                delay_min=int(auto_cleanup_min),
                on_done=lambda sid: on_progress and on_progress(f"🗑 Хранилище удалено автоматически: {sid}"),
                on_error=lambda sid, e: on_progress and on_progress(f"❌ Авто-удаление не удалось ({sid}): {e}"),
            )
            log(f"⏳ Авто-удаление хранилища запланировано через {int(auto_cleanup_min)} мин.")
        except Exception as e:
            log(f"⚠ Не удалось запланировать авто-удаление: {e}")

    # Если индексацию не ждали — возвращаем только store_id
    if not wait_index:
        return PipelineResult(store_id=store_id, clean_json=None, saved_copy=None)

    # 3) Извлечение по system.prompt (валídированный JSON вернётся строкой)
    log("— Запускаю обработку по системному промпту…")
    clean_json = run_extraction_with_vector_store(
        store_id=store_id,
        user_instruction=user_instruction,
        model=model,
        system_prompt_path=system_prompt_path,
    )
    log("Обработка завершена.")

    # 4) Сохранить копию результата в файл (как в журнале), если просят
    saved_copy = None
    if save_dir:
        try:
            saved_copy = _save_result_record(save_dir, store_id, clean_json)
            log(f"💾 Результат также сохранён: {saved_copy}")
        except Exception as e:
            log(f"⚠ Не удалось сохранить копию результата: {e}")

    return PipelineResult(store_id=store_id, clean_json=clean_json, saved_copy=saved_copy)
