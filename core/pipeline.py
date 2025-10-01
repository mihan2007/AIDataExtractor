# -*- coding: utf-8 -*-
"""High-level orchestration pipeline for Vector Store operations."""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Callable, Optional, Sequence

from core.uploader import upload_to_vector_store_ex
from core.vector_store_cleanup import schedule_cleanup
from core.vector_store_query import run_extraction_with_vector_store
from infra.config import AUTO_DELETE_DEFAULT_MIN, DEFAULT_MODEL, SYSTEM_PROMPT_PATH
from infra import localization as i18n
from infra.localization import translate as T

i18n.reload_language_from_settings()


def _ensure_dir(path: str) -> None:
    if path:
        os.makedirs(path, exist_ok=True)


def _unique_filename(prefix: str, store_id: Optional[str], ext: str = "json") -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    sid = (store_id or "noid").replace("/", "_")
    from uuid import uuid4
    suffix = uuid4().hex[:6]
    return f"{prefix}_{stamp}_{sid}_{suffix}.{ext}"


def _save_result_record(save_dir: str, store_id: str, clean_json: str) -> str:
    """Persist the validated extraction result in the same format as the journal."""
    _ensure_dir(save_dir)
    out_path = os.path.join(save_dir, _unique_filename("extract", store_id, "json"))

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


class PipelineResult:
    """Outcome produced by :func:`run_pipeline`."""

    def __init__(self, store_id: str, clean_json: Optional[str], saved_copy: Optional[str]):
        self.store_id = store_id
        self.clean_json = clean_json
        self.saved_copy = saved_copy

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            "PipelineResult(store_id={!r}, clean_json={}, saved_copy={!r})".format(
                self.store_id,
                bool(self.clean_json),
                self.saved_copy,
            )
        )


def run_pipeline(
    files: Sequence[str],
    *,
    wait_index: bool = True,
    save_dir: Optional[str] = None,
    on_progress: Optional[Callable[[str], None]] = None,
    user_instruction: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    system_prompt_path: str = SYSTEM_PROMPT_PATH,
    auto_cleanup_min: Optional[int] = AUTO_DELETE_DEFAULT_MIN,
) -> PipelineResult:
    """Upload, optionally wait for indexing, and run the extraction pipeline."""

    emit = on_progress or (lambda _msg: None)
    instruction = user_instruction or T("prompt.extract_instruction")

    emit(T("log.upload_start"))
    upload_summary = upload_to_vector_store_ex(
        files=files,
        on_progress=on_progress,
        wait_index=wait_index,
    )
    store_id = (upload_summary or {}).get("store_id")
    if not store_id:
        raise RuntimeError(T("pipeline.missing_store_id"))
    emit(T("log.upload_complete"))

    if auto_cleanup_min and auto_cleanup_min > 0:
        try:
            schedule_cleanup(
                vector_store_id=store_id,
                delay_min=int(auto_cleanup_min),
                on_done=lambda sid: emit(T("log.cleanup_done", store_id=sid)),
                on_error=lambda sid, err: emit(
                    T("log.cleanup_error", store_id=sid, error=str(err))
                ),
            )
            emit(T("log.cleanup_scheduled", minutes=int(auto_cleanup_min)))
        except Exception as exc:  # pragma: no cover - defensive path
            emit(T("log.cleanup_failed", error=str(exc)))

    if not wait_index:
        return PipelineResult(store_id=store_id, clean_json=None, saved_copy=None)

    emit(T("log.processing_start"))
    clean_json = run_extraction_with_vector_store(
        store_id=store_id,
        user_instruction=instruction,
        model=model,
        system_prompt_path=system_prompt_path,
    )
    emit(T("log.processing_done"))

    saved_copy = None
    if save_dir:
        try:
            saved_copy = _save_result_record(save_dir, store_id, clean_json)
            emit(T("log.saved_copy", path=saved_copy))
        except Exception as exc:  # pragma: no cover - defensive path
            emit(T("log.save_copy_failed", error=str(exc)))

    return PipelineResult(store_id=store_id, clean_json=clean_json, saved_copy=saved_copy)


__all__ = ["PipelineResult", "run_pipeline"]