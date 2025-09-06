# -*- coding: utf-8 -*-
from typing import List, Tuple, Optional, Callable, Dict, Any
import os
from datetime import datetime

from vector_store_client import VectorStoreClient

# настройки выполнения
MAX_WORKERS = 1  # последовательная загрузка (просто и предсказуемо)


def upload_to_vector_store_ex(
    paths: List[str],
    store_name: Optional[str] = None,
    on_progress: Optional[Callable[[str], None]] = None,
    wait_index: bool = False,
) -> Dict[str, Any]:
    """
    Расширенная версия: возвращает детали загрузки.
    {
      "store_id": str,
      "store_name": str,
      "uploaded": [str],
      "failed": [(path, err), ...],
      "summary": str
    }
    """
    log = on_progress or (lambda *_: None)

    if not paths:
        return {
            "store_id": "",
            "store_name": store_name or "",
            "uploaded": [],
            "failed": [],
            "summary": "Не выбрано ни одного файла.",
        }

    client = VectorStoreClient()

    # имя хранилища по текущему времени — если не задано
    if not store_name:
        store_name = "vs-" + datetime.now().strftime("%Y%m%d-%H%M%S")

    # 1) Создаём хранилище
    log(f"создаю хранилище '{store_name}'…")
    store_info = client.create_store(store_name)
    store_id = store_info["id"]
    log(f"создано: id={store_id}")

    uploaded: List[str] = []
    failed: List[Tuple[str, str]] = []

    # 2) Грузим файлы (последовательно)
    for path in paths:
        name = os.path.basename(path)
        try:
            log(f"[{name}] загрузка в /files…")
            file_info = client.upload_file(path)
            file_id = file_info["id"]
            log(f"[{name}] file_id={file_id}, привязка к store…")
            client.attach_file(store_id, file_id)

            if wait_index:
                st = client.poll_file_status(store_id, file_id)
                if st.get("status") != "processed":
                    raise RuntimeError(f"Индексация не удалась: {st.get('status')}")

            log(f"[{name}] готово ✅")
            uploaded.append(path)
        except Exception as e:
            log(f"[{name}] ошибка: {e}")
            failed.append((path, str(e)))

    # 3) Итоговый текст
    lines = [
        f"Хранилище: {store_name}",
        f"ID хранилища: {store_id}",
        f"Загружено файлов: {len(uploaded)}",
        f"Ошибки: {len(failed)}",
    ]
    if uploaded:
        lines.append("\n✅ Успешно загружено:")
        lines += [f" - {os.path.basename(p)}" for p in uploaded]
    if failed:
        lines.append("\n❌ Ошибки загрузки:")
        lines += [f" - {os.path.basename(p)}: {err}" for p, err in failed]

    return {
        "store_id": store_id,
        "store_name": store_name,
        "uploaded": uploaded,
        "failed": failed,
        "summary": "\n".join(lines),
    }


def upload_to_vector_store(
    paths: List[str],
    store_name: Optional[str] = None,
    on_progress: Optional[Callable[[str], None]] = None,
    wait_index: bool = False,
) -> str:
    """
    Обратная совместимость — возвращает строку-итог.
    """
    result = upload_to_vector_store_ex(
        paths, store_name=store_name, on_progress=on_progress, wait_index=wait_index
    )
    return result["summary"]
