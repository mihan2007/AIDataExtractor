# -*- coding: utf-8 -*-
"""
vector_store_query.py — вызов OpenAI Responses API (assistants=v2) с file_search.
Возвращает уже ВАЛИДИРОВАННЫЙ JSON по схеме из system.prompt (через Pydantic).
"""

from __future__ import annotations

import os
import json
from typing import Optional

import requests
from pydantic import ValidationError

from infra.config import (
    API_KEY_PATH,
    BASE_URL,
    DEFAULT_MODEL,
    TIMEOUT,
    SYSTEM_PROMPT_PATH,
)

# опционально: журнал (если модуль инициализирован иначе — просто не пишем в него)
try:
    from infra.log_journal import append_log
except Exception:
    append_log = None  # type: ignore[misc]


# ============================== ВСПОМОГАТЕЛЬНОЕ ===============================

def _read_api_key(path: str = API_KEY_PATH) -> str:
    with open(path, "r", encoding="utf-8") as f:
        key = f.read().strip()
    if not key:
        raise RuntimeError("Пустой API-ключ в API_KEY_PATH")
    return key


def _headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _load_system_prompt(path: str = SYSTEM_PROMPT_PATH) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _post_responses(payload: dict, timeout: tuple = TIMEOUT) -> dict:
    url = f"{BASE_URL}/responses"
    resp = requests.post(url, headers=_headers(_read_api_key()), json=payload, timeout=timeout)
    if resp.status_code >= 300:
        # пробуем вытащить тело с ошибкой
        try:
            err = resp.json()
        except Exception:
            err = resp.text
        raise RuntimeError(f"Responses API HTTP {resp.status_code}: {err}")
    try:
        return resp.json()
    except Exception as e:
        raise RuntimeError(f"Невалидный JSON от Responses API: {e}")


def _extract_output_text(resp_json: dict) -> str:
    """
    Универсальный парсер текста из ответа Responses API.
    Берёт первый текстовый фрагмент из первого item в 'output'.
    """
    output = resp_json.get("output") or []
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for piece in content:
            if isinstance(piece, dict) and piece.get("type") == "output_text":
                val = piece.get("text") or piece.get("value") or ""
                if isinstance(val, str) and val.strip():
                    return val.strip()

    # Фоллбек: иногда модель кладёт текст в 'message'
    msg = (resp_json.get("message") or "").strip()
    return msg


# ============================== ПОЛЕЗНЫЕ ЗАПРОСЫ ==============================

def test_file_search_filenames(
    store_id: str,
    model: str = DEFAULT_MODEL,
    timeout: tuple = TIMEOUT,
) -> str:
    """
    Минимальный тест: просим список имён/сниппетов доступных файлов.
    Возвращает сырой текст (НЕ обязано быть JSON).
    """
    prompt = (
        "Перечисли имена файлов и по одному короткому сниппету из каждого, доступных через file_search. "
        "Формат свободный, 5-10 строк."
    )

    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        "tools": [
            {
                "type": "file_search",
                "vector_store_ids": [store_id],
            }
        ],
    }

    data = _post_responses(payload, timeout)
    return _extract_output_text(data)


def run_extraction_with_vector_store(
    store_id: str,
    user_instruction: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    system_prompt_path: str = SYSTEM_PROMPT_PATH,
    timeout: tuple = TIMEOUT,
) -> str:
    """
    Основная функция: запускает извлечение по твоему system.prompt и file_search.
    Возвращает УЖЕ ВАЛИДИРОВАННЫЙ и «очищенный» JSON-строкой (exclude_none=True).
    """

    system_prompt = _load_system_prompt(system_prompt_path)

    # Соединяем инструкцию пользователя (если есть) с краткой подсказкой
    user_msg = (user_instruction or "").strip()
    if not user_msg:
        user_msg = "Извлеки данные по строгой JSON-схеме из system.prompt, используя file_search."

    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        "tools": [
            {
                "type": "file_search",
                "vector_store_ids": [store_id],
            }
        ],
    }

    data = _post_responses(payload, timeout)
    raw_text = _extract_output_text(data)

    # ==== ВАЛИДАЦИЯ ПО СХЕМЕ ИЗ PROMPT (через Pydantic-модели) ====
    # Модель и функция валидации живут в infra/models.py
    from infra.models import validate_and_dump_json  # локальный импорт, чтобы избежать циклов

    try:
        clean_json = validate_and_dump_json(raw_text)
    except ValidationError as e:
        # Пишем в журнал (если доступен) и пробрасываем дальше
        if append_log:
            try:
                append_log(
                    {
                        "ts": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
                        "phase": "validation_error",
                        "errors": e.errors(),
                        "note": "JSON от модели не соответствует схеме из system.prompt",
                    }
                )
            except Exception:
                pass
        raise
    # === ЗДЕСЬ ЛОГИРУЕМ УСПЕШНЫЙ ВАЛИДИРОВАННЫЙ РЕЗУЛЬТАТ ===
    try:
        from infra.log_journal import append_result_entry
        append_result_entry(clean_json, note="validated")
    except Exception:
        pass

    # Успех: возвращаем валидированный JSON (строка)
    return clean_json
