# -*- coding: utf-8 -*-
"""
uploader.py
-----------
Загрузка локальных файлов в OpenAI Vector Store + (опционально) ожидание индексации.

Функция верхнего уровня:
    upload_to_vector_store_ex(files, on_progress=None, wait_index=False) -> dict

Возвращает словарь:
    {
        "store_id": "vs_xxx",
        "file_ids": ["file_...", ...],
        "attached": n,               # сколько файлов успешно привязано к хранилищу
        "summary": "Читаемое резюме для GUI"
    }

Также содержит утилиту:
    wait_until_indexed(store_id, on_progress=None, poll_sec=2.0, max_wait_sec=300)

Требуется:
    - requests
    - корректные константы в config.py (API_KEY_PATH, BASE_URL, TIMEOUT)
"""

from __future__ import annotations

import os
import time
import mimetypes
from typing import Callable, Iterable, List, Optional, Tuple

import requests

from config import API_KEY_PATH, BASE_URL, TIMEOUT


# ============================ ВСПОМОГАТЕЛЬНЫЕ ============================

def _load_api_key(path: str = API_KEY_PATH) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Файл с API ключом не найден: {path}\n"
            f"Убедитесь, что ключ сохранён в этом файле."
        )
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def _headers_json(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _headers_multipart(api_key: str) -> dict:
    # Для multipart заголовок Content-Type ставится автоматически requests'ом
    return {
        "Authorization": f"Bearer {api_key}",
    }


def _log(msg: str, cb: Optional[Callable[[str], None]]) -> None:
    if cb:
        cb(msg)


def _human_size(num_bytes: int) -> str:
    units = ["Б", "КБ", "МБ", "ГБ"]
    size = float(num_bytes)
    for u in units:
        if size < 1024.0:
            return f"{size:.2f} {u}"
        size /= 1024.0
    return f"{size:.2f} ТБ"


# ============================ HTTP ВЫЗОВЫ API ============================

def create_vector_store(name: str, api_key: str, timeout: Tuple[int, int] = TIMEOUT) -> str:
    """
    POST /vector_stores  ->  { id: "vs_..." }
    """
    url = f"{BASE_URL}/vector_stores"
    payload = {"name": name}
    resp = requests.post(url, headers=_headers_json(api_key), json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    store_id = data.get("id")
    if not store_id:
        raise RuntimeError(f"Не удалось создать Vector Store: {data}")
    return store_id


def upload_file_to_files_api(path: str, api_key: str, timeout: Tuple[int, int] = TIMEOUT) -> str:
    """
    POST /files  (multipart)  -> { id: "file_..." }
    purpose = "assistants" для последующей работы в file_search
    """
    url = f"{BASE_URL}/files"
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    with open(path, "rb") as f:
        files = {
            "file": (os.path.basename(path), f, mime),
        }
        data = {
            "purpose": "assistants",
        }
        resp = requests.post(url, headers=_headers_multipart(api_key), files=files, data=data, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    file_id = data.get("id")
    if not file_id:
        raise RuntimeError(f"Не удалось загрузить файл {path}: {data}")
    return file_id


def attach_file_to_store(store_id: str, file_id: str, api_key: str, timeout: Tuple[int, int] = TIMEOUT) -> None:
    """
    POST /vector_stores/{id}/files  -> связывает загруженный файл с хранилищем
    """
    url = f"{BASE_URL}/vector_stores/{store_id}/files"
    payload = {"file_id": file_id}
    resp = requests.post(url, headers=_headers_json(api_key), json=payload, timeout=timeout)
    resp.raise_for_status()
    # успешный ответ — достаточно 2xx; детали нам не обязательны


def get_store_status(store_id: str, api_key: str, timeout: Tuple[int, int] = TIMEOUT) -> str:
    """
    GET /vector_stores/{id} -> { status: "in_progress" | "processing" | "indexed" | "failed", ... }
    Названия статусов могут отличаться; нормализуем наиболее частые варианты.
    """
    url = f"{BASE_URL}/vector_stores/{store_id}"
    resp = requests.get(url, headers=_headers_json(api_key), timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    raw = (data.get("status") or "").lower()

    # Нормализация к трем состояниям
    if raw in {"ready", "indexed", "complete", "completed"}:
        return "indexed"
    if raw in {"in_progress", "processing", "pending"}:
        return "processing"
    if raw in {"failed", "error"}:
        return "failed"
    # если что-то новое — вернём как есть
    return raw or "unknown"


# ============================ ОЖИДАНИЕ ИНДЕКСАЦИИ ============================

def wait_until_indexed(
    store_id: str,
    on_progress: Optional[Callable[[str], None]] = None,
    poll_sec: float = 2.0,
    max_wait_sec: int = 300,
) -> None:
    """
    Пулинг статуса Vector Store до состояния 'indexed'.
    Печатает прогресс через on_progress. Бросает TimeoutError при превышении max_wait_sec.
    """
    api_key = _load_api_key()
    started = time.perf_counter()

    _log(f"⏳ Ожидаю индексацию хранилища {store_id} …", on_progress)

    last_status = None
    while True:
        st = get_store_status(store_id, api_key=api_key)
        if st != last_status:
            _log(f" • статус: {st}", on_progress)
            last_status = st

        if st == "indexed":
            _log("✅ Индексация завершена.", on_progress)
            return
        if st == "failed":
            raise RuntimeError(f"Индексация завершилась с ошибкой для store={store_id}")

        elapsed = time.perf_counter() - started
        if elapsed > max_wait_sec:
            raise TimeoutError(f"Индексация не завершилась за {max_wait_sec} сек (store={store_id}).")

        time.sleep(poll_sec)


# ============================ ВЕРХНЕУРОВНЕВАЯ ФУНКЦИЯ ============================

def upload_to_vector_store_ex(
    files: Iterable[str],
    on_progress: Optional[Callable[[str], None]] = None,
    wait_index: bool = False,
    store_name_prefix: str = "vs",
) -> dict:
    """
    Загружает список локальных файлов в /files, привязывает к созданному Vector Store
    и (опционально) ждёт завершения индексации.

    :param files: пути к файлам
    :param on_progress: колбэк для логов (строка); может быть None
    :param wait_index: ждать ли индексацию внутри вызова
    :param store_name_prefix: префикс имени хранилища

    :return: словарь с итогами операции
    """
    api_key = _load_api_key()

    file_list: List[str] = [os.path.abspath(p) for p in files if p]
    if not file_list:
        raise ValueError("Список файлов пуст.")

    # Создаём хранилище
    ts = time.strftime("%Y%m%d-%H%M%S")
    store_name = f"{store_name_prefix}-{ts}"
    _log(f"создаю хранилище '{store_name}'…", on_progress)
    store_id = create_vector_store(store_name, api_key=api_key)
    _log(f"создано: id={store_id}", on_progress)

    # Идём по файлам
    file_ids: List[str] = []
    attached = 0

    for path in file_list:
        base = os.path.basename(path)
        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0
        size_text = _human_size(size)

        _log(f"[{base}] загрузка в /files…", on_progress)

        try:
            file_id = upload_file_to_files_api(path, api_key=api_key)
        except requests.HTTPError as e:
            _log(f"[{base}] ошибка загрузки: {e.response.status_code} {e.response.reason}; пропускаю", on_progress)
            continue
        except Exception as e:
            _log(f"[{base}] ошибка загрузки: {e}; пропускаю", on_progress)
            continue

        file_ids.append(file_id)
        _log(f"[{base}] file_id={file_id}, привязка к store…", on_progress)

        # Привязываем к Store
        try:
            attach_file_to_store(store_id=store_id, file_id=file_id, api_key=api_key)
            attached += 1
            _log(f"[{base}] готово ✅ ({size_text})", on_progress)
        except requests.HTTPError as e:
            _log(
                f"[{base}] ошибка привязки: {e.response.status_code} {e.response.reason} "
                f"{e.response.request.url}",
                on_progress,
            )
        except Exception as e:
            _log(f"[{base}] ошибка привязки: {e}", on_progress)

    # Опционально ждём индексацию
    if wait_index and file_ids:
        try:
            wait_until_indexed(store_id, on_progress=on_progress, poll_sec=2.0, max_wait_sec=300)
        except Exception as e:
            _log(f"⚠️ Индексация не подтверждена: {e}", on_progress)

    summary = (
        f"Загружено файлов: {len(file_ids)}, успешно привязано: {attached}. "
        f"Store ID: {store_id}"
    )

    return {
        "store_id": store_id,
        "file_ids": file_ids,
        "attached": attached,
        "summary": summary,
    }
