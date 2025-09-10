# -*- coding: utf-8 -*-
import os
import requests
from typing import List


# стало:
from config import API_KEY_PATH as API_KEY_FILE, BASE_URL as API_BASE_URL, TIMEOUT as REQUEST_TIMEOUT


def load_api_key(path: str = API_KEY_FILE) -> str:
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Файл с API ключом не найден: {path}\n"
            f"Убедитесь, что ключ сохранён в этом файле."
        )
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def _auth_headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}"}


def list_all_vector_stores(api_key: str) -> List[dict]:
    """Возвращает список всех созданных Vector Stores."""
    url = f"{API_BASE_URL}/vector_stores"
    resp = requests.get(url, headers=_auth_headers(api_key), timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json().get("data", [])


def list_files(api_key: str, vector_store_id: str) -> List[dict]:
    """Возвращает список файлов в конкретном хранилище."""
    url = f"{API_BASE_URL}/vector_stores/{vector_store_id}/files"
    resp = requests.get(url, headers=_auth_headers(api_key), timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json().get("data", [])


def delete_file(api_key: str, vector_store_id: str, file_id: str) -> None:
    """Удаляет файл из Vector Store."""
    url = f"{API_BASE_URL}/vector_stores/{vector_store_id}/files/{file_id}"
    resp = requests.delete(url, headers=_auth_headers(api_key), timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()


def delete_vector_store(api_key: str, vector_store_id: str) -> None:
    """Удаляет всё хранилище."""
    url = f"{API_BASE_URL}/vector_stores/{vector_store_id}"
    resp = requests.delete(url, headers=_auth_headers(api_key), timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()


def cleanup_store(vector_store_id: str) -> None:
    """
    Удаляет все файлы из указанного Vector Store и затем само хранилище.
    """
    api_key = load_api_key()
    try:
        files = list_files(api_key, vector_store_id)
    except Exception as e:
        print(f"❌ Ошибка получения списка файлов для {vector_store_id}: {e}")
        files = []

    for f in files:
        fid = f.get("id")
        if fid:
            try:
                delete_file(api_key, vector_store_id, fid)
                print(f"   ✅ Файл удалён: {fid}")
            except Exception as e:
                print(f"   ❌ Ошибка удаления файла {fid}: {e}")

    try:
        delete_vector_store(api_key, vector_store_id)
        print(f"🗑 Хранилище удалено: {vector_store_id}")
    except Exception as e:
        print(f"❌ Ошибка удаления хранилища {vector_store_id}: {e}")


def cleanup_all() -> None:
    """Удаляет все файлы и все хранилища."""
    api_key = load_api_key()
    stores = list_all_vector_stores(api_key)

    if not stores:
        print("✅ Нет созданных Vector Stores — очищать нечего.")
        return

    print(f"🔍 Найдено хранилищ: {len(stores)}")

    for store in stores:
        store_id = store.get("id")
        name = store.get("name", "(без имени)")
        print(f"\n🗂 Хранилище: {name} ({store_id})")

        try:
            files = list_files(api_key, store_id)
        except Exception as e:
            print(f"   ❌ Ошибка получения списка файлов: {e}")
            continue

        for f in files:
            fid = f.get("id")
            try:
                delete_file(api_key, store_id, fid)
                print(f"   ✅ Файл удалён: {fid}")
            except Exception as e:
                print(f"   ❌ Ошибка удаления файла {fid}: {e}")

        try:
            delete_vector_store(api_key, store_id)
            print("   🗑 Хранилище удалено.")
        except Exception as e:
            print(f"   ❌ Ошибка удаления хранилища {store_id}: {e}")

    print("\n✨ Все Vector Stores удалены.")


if __name__ == "__main__":
    cleanup_all()
