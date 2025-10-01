# -*- coding: utf-8 -*-
"""Persisted user settings for the Vector Store tooling."""
from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict

from infra.config import PROJECT_ROOT

SETTINGS_PATH = os.path.join(PROJECT_ROOT, "settings.json")
DEFAULT_SETTINGS: Dict[str, Any] = {
    "language": "ru",
}

_lock = threading.RLock()
_cached_settings: Dict[str, Any] | None = None


def _load_from_disk() -> Dict[str, Any]:
    if not os.path.exists(SETTINGS_PATH):
        return dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as fp:
            data = json.load(fp)
    except (OSError, ValueError, TypeError):
        return dict(DEFAULT_SETTINGS)
    if not isinstance(data, dict):
        return dict(DEFAULT_SETTINGS)
    merged = dict(DEFAULT_SETTINGS)
    merged.update(data)
    return merged


def _ensure_loaded() -> Dict[str, Any]:
    global _cached_settings
    if _cached_settings is None:
        _cached_settings = _load_from_disk()
    return _cached_settings


def load_settings() -> Dict[str, Any]:
    with _lock:
        return dict(_ensure_loaded())


def _write(settings: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(SETTINGS_PATH) or ".", exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as fp:
        json.dump(settings, fp, ensure_ascii=False, indent=2)
    global _cached_settings
    _cached_settings = dict(settings)


def save_settings(settings: Dict[str, Any]) -> None:
    with _lock:
        _write(dict(settings))


def update_settings(**updates: Any) -> Dict[str, Any]:
    with _lock:
        current = dict(_ensure_loaded())
        current.update(updates)
        _write(current)
        return dict(current)


def get_language(default: str = DEFAULT_SETTINGS["language"]) -> str:
    with _lock:
        value = _ensure_loaded().get("language", default)
        return str(value or default)


def set_language(language: str) -> None:
    update_settings(language=language)


__all__ = [
    "DEFAULT_SETTINGS",
    "SETTINGS_PATH",
    "load_settings",
    "save_settings",
    "update_settings",
    "get_language",
    "set_language",
]