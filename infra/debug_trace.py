# -*- coding: utf-8 -*-
"""
Небольшой отладочный хелпер: при желании можно включить,
чтобы увидеть попытки прокинуть proxies в OpenAI(OpenAI.__init__).
Сейчас клиент работает через requests, этот файл не обязателен.
"""

import inspect
try:
    from openai import OpenAI  # не обязателен для работы проекта
except Exception:
    OpenAI = None


def _patch_openai_init():
    if OpenAI is None:
        return

    original_init = OpenAI.__init__

    def patched_init(*args, **kwargs):
        if "proxies" in kwargs:
            print("❌ Найден вызов OpenAI с proxies!")
            print("Значение proxies:", kwargs["proxies"])
            print("Стек вызова:")
            for frame in inspect.stack():
                print(f"  Файл: {frame.filename}, строка: {frame.lineno}, функция: {frame.function}")
        return original_init(*args, **kwargs)

    OpenAI.__init__ = patched_init


if __name__ == "__main__":
    _patch_openai_init()
    print("OpenAI.__init__ патчен (если библиотека доступна).")
