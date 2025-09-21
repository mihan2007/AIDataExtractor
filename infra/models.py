# -*- coding: utf-8 -*-
"""
infra/models.py — Pydantic модели под JSON-схему из system.prompt
"""

from __future__ import annotations
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict
from pydantic import ValidationError

class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = Field(default=None)
    qty: Optional[int] = Field(default=None)
    condition: Optional[Literal["new", "used"]] = Field(default=None)


class Delivery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    address: Optional[str] = None
    deadline: Optional[str] = Field(
        default=None,
        description="Дата в формате YYYY-MM-DD или интервал (строкой)",
    )


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
    Корневая схема, полностью соответствующая system.prompt.
    """
    model_config = ConfigDict(extra="ignore")

    product: Product
    delivery: Delivery
    payment_terms: Optional[str] = None
    restrictions: Restriction
    evidence: List[EvidenceItem]
    uncertainties: List[UncertaintyItem]

def validate_and_dump_json(model_output_text: str) -> str:
    """
    Валидирует JSON-строку от LLM по схеме TenderExtract.
    Возвращает аккуратно сериализованный JSON (исключая None).
    Бросает ValidationError при несоответствии.
    """
    obj = TenderExtract.model_validate_json(model_output_text)
    return obj.model_dump_json(exclude_none=True, ensure_ascii=False)