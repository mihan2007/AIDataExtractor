# -*- coding: utf-8 -*-
"""
Удаление ВСЕХ Vector Stores:
- Удаляет все файлы в каждом хранилище
- Удаляет само хранилище
- Никаких аргументов указывать не нужно

Запуск:
  python vector_store_cleanup_all.py
"""

import os
import requests

API_KEY_FILE = r"C:\API_keys\API_key_GPT.txt"
API_BASE_URL = "https://api.openai.com/v1"
REQUEST_TIMEOUT = (10, 90)


def load_api_key(path=API_KEY_FILE):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Файл с API ключом не найден: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def _auth_headers(api_key: str, json_content: bool = False) -> dict:
    h = {"Authorization": f"Bearer {api_key}"}
    if json_content:
        h["Content-Type"] = "application/json"
    return h


def list_all_vector_stores(api_key: str):
    """Получаем список ВСЕХ Vector Stores"""
    url = f"{API_BASE_URL}/vector_stores"
    stores = []
    after = None

    while True:
        params = {"limit": 100}
        if after:
            params["after"] = after

        resp = requests.get(url, headers=_auth_headers(api_key), params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data", [])
        stores.extend(items)

        if data.get("has_more"):
            after = data.get("last_id") or (items[-1]["id"] if items else None)
            if not after:
                break
        else:
            break

    return stores


def list_files(api_key: str, store_id: str):
    """Список файлов в конкретном хранилище"""
    url = f"{API_BASE_URL}/vector_stores/{store_id}/files"
    resp = requests.get(url, headers=_auth_headers(api_key), timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json().get("data", [])


def delete_file(api_key: str, store_id: str, file_id: str):
    """Удаляем файл из Vector Store"""
    url = f"{API_BASE_URL}/vector_stores/{store_id}/files/{file_id}"
    resp = requests.delete(url, headers=_auth_headers(api_key), timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()


def delete_vector_store(api_key: str, store_id: str):
    """Удаляем сам Vector Store"""
    url = f"{API_BASE_URL}/vector_stores/{store_id}"
    resp = requests.delete(url, headers=_auth_headers(api_key), timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()


def main():
    api_key = load_api_key()
    stores = list_all_vector_stores(api_key)

    if not stores:
        print("✅ Нет созданных Vector Stores — очищать нечего.")
        return

    print(f"🔍 Найдено хранилищ: {len(stores)}\n")

    for store in stores:
        store_id = store.get("id")
        name = store.get("name", "(без имени)")
        print(f"🗂  Хранилище: {name} ({store_id})")

        # Удаляем файлы из хранилища
        files = list_files(api_key, store_id)
        for f in files:
            fid = f.get("id")
            try:
                delete_file(api_key, store_id, fid)
                print(f"   ✅ Файл удалён: {fid}")
            except requests.HTTPError as e:
                print(f"   ❌ Ошибка удаления файла {fid}: {e}")

        # Удаляем само хранилище
        try:
            delete_vector_store(api_key, store_id)
            print(f"   🗑 Хранилище удалено.")
        except requests.HTTPError as e:
            print(f"   ❌ Ошибка удаления хранилища {store_id}: {e}")

        print("-" * 50)

    print("\n✨ Все Vector Stores удалены.")


if __name__ == "__main__":
    main()
