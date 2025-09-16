# -*- coding: utf-8 -*-
"""
vector_store_query.py — Responses API (assistants=v2) + file_search.
Вариант без attachments/tool_resources: vector_store_ids прямо в tools.
Есть:
  - test_file_search_filenames(store_id): минимальный тест (JSON только с именами/сниппетами)
  - run_extraction_with_vector_store(...): основная обработка по вашему системному промту
"""

import os
import json
import requests
from typing import Optional

from infra.config import API_KEY_PATH, BASE_URL, DEFAULT_MODEL, TIMEOUT, SYSTEM_PROMPT_PATH


def _load_api_key() -> str:
    if not os.path.exists(API_KEY_PATH):
        raise FileNotFoundError(f"Файл с API ключом не найден: {API_KEY_PATH}")
    with open(API_KEY_PATH, "r", encoding="utf-8") as f:
        return f.read().strip()


def _post_responses(payload: dict, timeout: tuple) -> dict:
    headers = {
        "Authorization": f"Bearer {_load_api_key()}",
        "OpenAI-Beta": "assistants=v2",   # важно для tools
    }
    resp = requests.post(f"{BASE_URL}/responses", headers=headers, json=payload, timeout=timeout)
    if not resp.ok:
        raise RuntimeError(f"{resp.status_code} {resp.reason} на /responses.\nТело ответа:\n{resp.text}")
    return resp.json()


def _extract_output_text(resp_json: dict) -> str:
    # Современный путь
    if isinstance(resp_json.get("output_text"), str):
        return resp_json["output_text"].strip()
    # Старый массив output[].content[].text
    chunks = []
    for item in resp_json.get("output", []):
        for c in item.get("content", []):
            if c.get("type") == "output_text" and "text" in c:
                chunks.append(c["text"])
    if chunks:
        return "\n".join(chunks).strip()
    # Фоллбек
    return (resp_json.get("message") or "").strip()


# ---------------------- МИНИ-ТЕСТ: вернуть имена файлов/сниппеты ----------------------

def test_file_search_filenames(
    store_id: str,
    model: str = DEFAULT_MODEL,
    timeout: tuple = TIMEOUT,
) -> str:
    """
    Минимальный тест file_search: просим модель вернуть JSON вида:
      {"files": [{"name": "...", "snippet": "..."}]}
    Если имена недоступны напрямую, пусть даёт короткие сниппеты (<=120 символов).
    """
    instructions = (
        "You are a JSON-only extractor. "
        "Use file_search over the attached vector store. "
        "Return JSON: {\"files\":[{\"name\":\"<file or source if available>\",\"snippet\":\"<<=120 chars snippet>\"}...]}. "
        "If names are unavailable, set name to \"unknown\". "
        "NO extra text outside JSON."
    )

    payload = {
        "model": model,
        "instructions": instructions,
        "input": [
            {"role": "user", "content": [{"type": "input_text", "text": "List files you can see with a short snippet."}]}
        ],
        # ВАЖНО: vector_store_ids прямо внутри инструмента
        "tools": [
            {
                "type": "file_search",
                "vector_store_ids": [store_id],
            }
        ],
    }

    data = _post_responses(payload, timeout)
    text = _extract_output_text(data)
    # Проверим JSON-валидность
    json.loads(text)
    return text


# ---------------------- ОСНОВНОЙ ВЫЗОВ: ваш системный промт ----------------------

def run_extraction_with_vector_store(
    store_id: str,
    user_instruction: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    system_prompt_path: str = SYSTEM_PROMPT_PATH,
    timeout: tuple = TIMEOUT,
) -> str:
    """
    Основной запуск по вашим правилам (system prompt → instructions).
    Возвращает ВАЛИДНЫЙ JSON по промту.
    """
    # Инструкции
    if os.path.exists(system_prompt_path):
        with open(system_prompt_path, "r", encoding="utf-8") as f:
            instructions = f.read()
    else:
        instructions = (
            "Ты — Экстрактор. Читай документы через file_search и верни строго JSON:\n"
            "{ \"files\": [ { \"snippet\": \"короткая цитата\", \"source\": \"при наличии\" } ] }\n"
            "Никакого текста вне JSON. Если нет данных — верни: {\"files\":[]}"
        )

    user_input = user_instruction or "Извлеки данные строго по инструкциям (JSON-only)."

    payload = {
        "model": model,
        "instructions": instructions,
        "input": [
            {"role": "user", "content": [{"type": "input_text", "text": user_input}]}
        ],
        "tools": [
            {
                "type": "file_search",
                "vector_store_ids": [store_id],
            }
        ],
    }

    data = _post_responses(payload, timeout)
    text = _extract_output_text(data)
    # Валидируем JSON (ваш промт требует JSON-only)
    json.loads(text)
    return text
