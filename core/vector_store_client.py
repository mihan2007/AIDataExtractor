# -*- coding: utf-8 -*-
import os
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from infra.config import API_KEY_PATH, BASE_URL, TIMEOUT
import requests

try:
    # опционально: логирование, если модуль доступен
    from infra.log_journal import append_upload_entry
except Exception:
    append_upload_entry = None  # нет журнала — просто пропустим

class VectorStoreClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_key_path: str = API_KEY_PATH,
        base_url: str = BASE_URL,
        request_timeout: tuple = TIMEOUT,
    ):
        self.api_key = api_key or self._load_api_key(api_key_path)
        self.base_url = base_url.rstrip("/")
        self.timeout = request_timeout

        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})

    @staticmethod
    def _load_api_key(path: str) -> str:
        if not os.path.isfile(path):
            raise FileNotFoundError(
                f"Файл с API ключом не найден: {path}\n"
                f"Убедитесь, что ключ сохранён в этом файле."
            )
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()

    # -------- Vector Stores --------

    def create_store(self, name: Optional[str] = None) -> Dict[str, Any]:
        store_name = name or "vs-" + datetime.now().strftime("%Y%m%d-%H%M%S")
        url = f"{self.base_url}/vector_stores"
        resp = self.session.post(url, json={"name": store_name}, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()  # содержит id, name, и др.

    def list_stores(self) -> List[dict]:
        url = f"{self.base_url}/vector_stores"
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json().get("data", [])

    def delete_store(self, store_id: str) -> None:
        url = f"{self.base_url}/vector_stores/{store_id}"
        resp = self.session.delete(url, timeout=self.timeout)
        resp.raise_for_status()

    # -------- Files --------

    def upload_file(self, path: str) -> Dict[str, Any]:
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Файл не найден: {path}")

        url = f"{self.base_url}/files"
        with open(path, "rb") as f:
            files = {"file": (os.path.basename(path), f)}
            data = {"purpose": "assistants"}
            resp = self.session.post(url, files=files, data=data, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()  # содержит id и др.

    def attach_file(self, store_id: str, file_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/vector_stores/{store_id}/files"
        resp = self.session.post(url, json={"file_id": file_id}, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def list_files(self, store_id: str) -> List[dict]:
        url = f"{self.base_url}/vector_stores/{store_id}/files"
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json().get("data", [])

    def delete_file(self, store_id: str, file_id: str) -> None:
        url = f"{self.base_url}/vector_stores/{store_id}/files/{file_id}"
        resp = self.session.delete(url, timeout=self.timeout)
        resp.raise_for_status()

    def poll_file_status(
        self,
        store_id: str,
        file_id: str,
        interval: float = 2.0,
        max_wait: float = 900.0,
    ) -> dict:
        """Ожидание индексации файла (опционально)."""
        url = f"{self.base_url}/vector_stores/{store_id}/files/{file_id}"
        start = time.time()
        while True:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status")
            if status in ("processed", "failed"):
                return data
            if time.time() - start > max_wait:
                return {"status": "timeout"}
            time.sleep(interval)

    def upload_and_attach_files(self, store_id: str, paths: list[str]) -> dict:
        """
        Загружает файлы в /files, привязывает к vector store, ждёт индексацию (необязательно),
        и записывает в журнал: id хранилища, суммарное время и среднюю скорость.
        Возвращает метрики для UI.
        """
        start = time.time()
        file_sizes = []
        for p in paths:
            size = os.path.getsize(p)
            file_sizes.append((p, size))

            fmeta = self.upload_file(p)  # POST /files
            fid = fmeta.get("id")
            if fid:
                self.attach_file(store_id, fid)  # POST /vector_stores/{id}/files

        elapsed = time.time() - start
        total_bytes = sum(sz for _, sz in file_sizes) or 0
        avg_speed_kb_s = (total_bytes / 1024.0 / elapsed) if elapsed > 0 else None

        # запись в журнал (если доступен модуль журнала)
        if append_upload_entry:
            try:
                append_upload_entry(
                    store_id=store_id,
                    files=file_sizes,
                    elapsed_sec=elapsed,
                    avg_speed_kb_s=avg_speed_kb_s,
                )
            except Exception:
                pass

        return {
            "store_id": store_id,
            "elapsed_sec": round(elapsed, 3),
            "avg_speed_kb_s": round(avg_speed_kb_s, 3) if avg_speed_kb_s is not None else None,
            "total_bytes": total_bytes,
            "files": [{"name": os.path.basename(p), "size_bytes": sz} for p, sz in file_sizes],
        }