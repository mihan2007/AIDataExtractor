# -*- coding: utf-8 -*-
"""
infra/models.py — Pydantic-модели под схему из system.prompt
и функция validate_and_dump_json с очисткой Markdown-кодблоков.
"""

from __future__ import annotations

import json
import re
from typing import Optional, List, Literal

from pydantic import BaseModel, Field, ConfigDict, ValidationError


# =========================== МОДЕЛИ ПОД СХЕМУ ===========================

class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = Field(default=None)
    qty: Optional[int] = Field(default=None)
    # "new" | "used" | null
    condition: Optional[Literal["new", "used"]] = Field(default=None)


class Delivery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    address: Optional[str] = None
    # Дата в формате YYYY-MM-DD или интервал/период — как строка
    deadline: Optional[str] = None


class Restriction(BaseModel):
    model_config = ConfigDict(extra="ignore")

    gov_1875_applicable: Optional[bool] = None


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    field: Optional[str] = None
    quote: Optional[str] = None
    where: Optional[str] = None


class UncertaintyItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    field: Optional[str] = None
    reason: Optional[str] = None
    hint: Optional[str] = None


class TenderExtract(BaseModel):
    """
    Корневая схема ответа по system.prompt:
      {
        "product": {...},
        "delivery": {...},
        "payment_terms": null | str,
        "restrictions": {...},
        "evidence": [ ... ],
        "uncertainties": [ ... ]
      }
    """
    model_config = ConfigDict(extra="ignore")

    product: Product
    delivery: Delivery
    payment_terms: Optional[str] = None
    restrictions: Restriction
    evidence: List[EvidenceItem]
    uncertainties: List[UncertaintyItem]


# ======================== ОЧИСТКА И ВАЛИДАЦИЯ ==========================

_CODE_FENCE_RE = re.compile(
    r"^\s*```[a-zA-Z0-9_-]*\s*([\s\S]*?)\s*```\s*$",
    re.MULTILINE,
)

def _strip_markdown_code_fences(text: str) -> str:
    """
    Удаляет обёртку ```json ... ``` / ``` ... ``` если она есть.
    Возвращает исходный текст, если обёртки нет.
    """
    m = _CODE_FENCE_RE.match(text.strip())
    return m.group(1).strip() if m else text.strip()


def _coerce_to_json_object(text: str) -> str:
    """
    Если в тексте есть «мусор» до/после и Pydantic не смог распарсить,
    пытаемся вырезать первый JSON-объект по балансу скобок.
    Возвращаем как строку (JSON).
    """
    s = text.strip()
    # быстрый путь — уже валидный JSON-объект
    if s.startswith("{") and s.endswith("}"):
        return s

    # вырезаем самый внешний {...} по балансу
    start = s.find("{")
    if start == -1:
        return s  # пусть провалится на валидации

    depth = 0
    for i in range(start, len(s)):
        ch = s[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = s[start:i + 1]
                # проверим, что это реально JSON-объект
                try:
                    json.loads(candidate)
                    return candidate
                except Exception:
                    break
    return s  # не удалось — оставляем как есть


def validate_and_dump_json(model_output_text: str) -> str:
    """
    Валидирует JSON-строку от LLM по схеме TenderExtract.
    1) Убирает Markdown-кодблоки ```...```
    2) Пытается вырезать первый JSON-объект, если есть лишний текст
    3) Валидирует через Pydantic
    Возвращает аккуратно сериализованный JSON (exclude_none=True).
    Бросает ValidationError при несоответствии схеме.
    """
    # Шаг 1: убираем ```json ... ```
    text = _strip_markdown_code_fences(model_output_text)

    # Шаг 2: если дальше будет ошибка — попробуем «добыть» { ... }
    try:
        obj = TenderExtract.model_validate_json(text)
    except ValidationError:
        text2 = _coerce_to_json_object(text)
        obj = TenderExtract.model_validate_json(text2)

    # Шаг 3: сериализуем обратно без None и без ASCII-эскейпа
    return json.dumps(
        obj.model_dump(exclude_none=True),
        ensure_ascii=False
    )
