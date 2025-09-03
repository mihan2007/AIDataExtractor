# -*- coding: utf-8 -*-
from typing import List, Tuple, Optional, Callable
import os
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

API_KEY_FILE = r"C:\API_keys\API_key_GPT.txt"
API_BASE_URL = "https://api.openai.com/v1"

# настройки выполнения
MAX_WORKERS = 3              # параллельные загрузки (0 или 1 = последовательно)
POLL_INTERVAL_SEC = 2.0      # пауза между запросами статуса
MAX_POLL_SECONDS = 900       # максимум ожидания индексации одного файла (15 мин)
REQUEST_TIMEOUT = (10, 90)   # таймауты для requests: (connect, read)


def load_api_key(path: str = API_KEY_FILE) -> str:
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Файл с API ключом не найден: {path}\n"
            f"Убедитесь, что ключ сохранён в этом файле."
        )
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def _auth_headers(api_key: str, content_json: bool = False) -> dict:
    h = {"Authorization": f"Bearer {api_key}"}
    if content_json:
        h["Content-Type"] = "application/json"
    return h


def create_vector_store(api_key: str, store_name: str) -> str:
    url = f"{API_BASE_URL}/vector_stores"
    resp = requests.post(
        url, headers=_auth_headers(api_key, True),
        json={"name": store_name}, timeout=REQUEST_TIMEOUT
    )
    resp.raise_for_status()
    return resp.json()["id"]


def upload_raw_file(api_key: str, file_path: str) -> str:
    """
    Шаг 1: /files (multipart/form-data) -> file_id
    Обязательно передаём purpose=assistants.
    """
    url = f"{API_BASE_URL}/files"
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f)}
        data = {"purpose": "assistants"}
        resp = requests.post(
            url, headers=_auth_headers(api_key),
            files=files, data=data, timeout=REQUEST_TIMEOUT
        )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"{resp.status_code} {resp.text}")
    return resp.json()["id"]


def attach_file_to_vector_store(api_key: str, vector_store_id: str, file_id: str) -> None:
    """Шаг 2: /vector_stores/{id}/files (application/json)"""
    url = f"{API_BASE_URL}/vector_stores/{vector_store_id}/files"
    resp = requests.post(
        url, headers=_auth_headers(api_key, True),
        json={"file_id": file_id}, timeout=REQUEST_TIMEOUT
    )
    resp.raise_for_status()


def poll_file_status(api_key: str, vector_store_id: str, file_id: str) -> dict:
    """Шаг 3: опрос статуса индексации файла."""
    url = f"{API_BASE_URL}/vector_stores/{vector_store_id}/files/{file_id}"
    start = time.time()
    while True:
        resp = requests.get(url, headers=_auth_headers(api_key), timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")
        if status in ("processed", "failed"):
            return data
        if time.time() - start > MAX_POLL_SECONDS:
            data.setdefault("status", "timeout")
            return data
        time.sleep(POLL_INTERVAL_SEC)


def _upload_one(api_key: str, vector_store_id: str, path: str,
                on_progress: Optional[Callable[[str], None]] = None) -> Tuple[str, bool, Optional[str]]:
    """Загрузка одного файла (для параллельного исполнения)."""
    name = os.path.basename(path)
    log = (lambda msg: on_progress(f"[{name}] {msg}")) if on_progress else (lambda *_: None)

    if not os.path.isfile(path):
        return path, False, "Файл не найден"

    try:
        log("загрузка в /files…")
        file_id = upload_raw_file(api_key, path)

        log(f"file_id={file_id} получен, привязка к vector store…")
        attach_file_to_vector_store(api_key, vector_store_id, file_id)

        log("ожидание индексации…")
        status_info = poll_file_status(api_key, vector_store_id, file_id)

        status = status_info.get("status")
        if status == "processed":
            log("готово ✅")
            return path, True, None
        elif status == "timeout":
            log("превышено время ожидания ⏳")
            return path, False, "timeout"
        else:
            log("индексация не удалась ❌")
            return path, False, "Индексация не удалась"
    except Exception as e:
        return path, False, str(e)


def upload_to_vector_store(paths: List[str],
                           store_name: Optional[str] = None,
                           on_progress: Optional[Callable[[str], None]] = None) -> str:
    """
    Основная функция загрузки.
    - Если store_name не указан, создаёт новое хранилище: vs-YYYYMMDD-HHMMSS
    - Параллельная или последовательная загрузка файлов
    - on_progress(msg) — необязательный колбэк для "живого" лога
    """
    if not paths:
        return "Не выбрано ни одного файла."

    # имя хранилища по текущему времени
    if not store_name:
        store_name = "vs-" + datetime.now().strftime("%Y%m%d-%H%M%S")

    progress = on_progress or (lambda *_: None)
    try:
        api_key = load_api_key()
    except FileNotFoundError as e:
        return str(e)

    try:
        progress(f"создаю хранилище '{store_name}'…")
        vector_store_id = create_vector_store(api_key, store_name)
        progress(f"создано: id={vector_store_id}")

        uploaded: List[str] = []
        failed: List[Tuple[str, str]] = []

        # последовательная загрузка
        if not MAX_WORKERS or MAX_WORKERS <= 1:
            for p in paths:
                path, ok, err = _upload_one(api_key, vector_store_id, p, on_progress=on_progress)
                if ok:
                    uploaded.append(path)
                else:
                    failed.append((path, err or "ошибка"))
        else:
            # параллельная загрузка
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
                futures = [ex.submit(_upload_one, api_key, vector_store_id, p, on_progress) for p in paths]
                for fut in as_completed(futures):
                    path, ok, err = fut.result()
                    if ok:
                        uploaded.append(path)
                    else:
                        failed.append((path, err or "ошибка"))

        lines = [
            f"Хранилище: {store_name}",
            f"ID хранилища: {vector_store_id}",
            f"Загружено файлов: {len(uploaded)}",
            f"Ошибки: {len(failed)}",
        ]

        if uploaded:
            lines.append("\n✅ Успешно загружено:")
            lines += [f" - {os.path.basename(p)}" for p in uploaded]

        if failed:
            lines.append("\n❌ Ошибки загрузки:")
            lines += [f" - {os.path.basename(p)}: {err}" for p, err in failed]

        return "\n".join(lines)

    except Exception as e:
        return f"Ошибка загрузки: {e}"
