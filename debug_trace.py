import inspect
from openai import OpenAI

def patched_init(*args, **kwargs):
    if "proxies" in kwargs:
        print("❌ Найден вызов OpenAI с proxies!")
        print("Значение proxies:", kwargs["proxies"])
        print("Стек вызова:")
        for frame in inspect.stack():
            print(f"  Файл: {frame.filename}, строка: {frame.lineno}, функция: {frame.function}")
    # вызываем оригинальный __init__
    return original_init(*args, **kwargs)

# Подменяем конструктор клиента
original_init = OpenAI.__init__
OpenAI.__init__ = patched_init

# Импортируем твой код — он вызовет OpenAI как обычно
import uploader

# Тестовая загрузка (можно выбрать любой путь к файлам)
print(uploader.upload_to_vector_store([]))
