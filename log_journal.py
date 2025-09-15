# -*- coding: utf-8 -*-
"""
Журнал логов (JSONL): одна запись на строку.
Хранит метрики загрузки файлов и вызова Responses API.

По умолчанию кладём файл в <results>/logs/vector_store_journal.jsonl
(папка results берётся из config.EXCTRACTION_RESULTS_DIR)
"""

from __future__ import annotations
import os
import json
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from config import EXTRACTION_RESULTS_DIR

# === Где хранить журнал ===
LOGS_DIR = os.path.join(EXTRACTION_RESULTS_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOGS_DIR, "vector_store_journal.jsonl")

# === Таблица цен (USD за 1M токенов) — подправьте при необходимости ===
# Если модель отсутствует в таблице — стоимость просто не будет посчитана.
PRICE_TABLE = {
    "gpt-4.1-mini": {"input": 0.3, "output": 0.6},  # Примерные значения; при необходимости обновите
    # добавляйте другие модели здесь
}


def _iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_jsonl_file() -> None:
    # Просто убеждаемся, что директория существует; сам файл будет создан при первой записи.
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


def _estimate_cost_usd(model: Optional[str], input_tokens: Optional[int], output_tokens: Optional[int]) -> Optional[float]:
    if not model or model not in PRICE_TABLE:
        return None
    input_rate = PRICE_TABLE[model].get("input")
    output_rate = PRICE_TABLE[model].get("output")
    if input_rate is None or output_rate is None:
        return None
    itok = float(input_tokens or 0)
    otok = float(output_tokens or 0)
    # Цена = (токены / 1_000_000) * ставка
    return round((itok / 1_000_000.0) * input_rate + (otok / 1_000_000.0) * output_rate, 6)


def append_log(record: Dict[str, Any]) -> None:
    """Добавляет произвольную запись в журнал (как JSON в одну строку)."""
    _ensure_jsonl_file()
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False)
        f.write("\n")


def append_upload_entry(
    *,
    store_id: Optional[str],
    files: Iterable[Tuple[str, int]],
    elapsed_sec: float,
    avg_speed_kb_s: Optional[float],
) -> None:
    """Логирует этап отправки/индексации."""
    entry = {
        "ts": _iso_now(),
        "phase": "upload",
        "store_id": store_id,
        "files": [{"name": os.path.basename(p), "size_bytes": int(sz)} for p, sz in files],
        "upload": {
            "elapsed_sec": round(float(elapsed_sec), 3),
            "avg_speed_kb_s": round(float(avg_speed_kb_s), 3) if avg_speed_kb_s is not None else None,
            "total_bytes": int(sum(sz for _, sz in files)),
        },
    }
    append_log(entry)


def append_response_entry(
    *,
    store_id: Optional[str],
    model: Optional[str],
    elapsed_sec: float,
    input_tokens: Optional[int],
    output_tokens: Optional[int],
    total_tokens: Optional[int],
) -> None:
    """Логирует этап получения ответа от Responses API."""
    cost = _estimate_cost_usd(model, input_tokens, output_tokens)
    entry = {
        "ts": _iso_now(),
        "phase": "response",
        "store_id": store_id,
        "model": model,
        "response": {
            "elapsed_sec": round(float(elapsed_sec), 3),
            "input_tokens": int(input_tokens) if input_tokens is not None else None,
            "output_tokens": int(output_tokens) if output_tokens is not None else None,
            "total_tokens": int(total_tokens) if total_tokens is not None else None,
            "cost_usd_est": cost,
        },
    }
    append_log(entry)


def read_last(n: int = 50) -> List[Dict[str, Any]]:
    """Читает последние n записей журнала (если нужно быстро посмотреть в консоли/GUI)."""
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    lines = lines[-n:]
    out: List[Dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out
