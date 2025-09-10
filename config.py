# -*- coding: utf-8 -*-
"""
Глобальные константы и настройки проекта.
"""
import os

# === Пути ===
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
import os

API_KEY_PATH = os.path.join("C:\\", "API_keys", "API_key_GPT.txt")

SYSTEM_PROMPT_PATH = os.path.join(ROOT_DIR, "tender_extractor_system.prompt.md")

# === OpenAI API ===
BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4.1-mini"

# === Сетевые таймауты ===
TIMEOUT = (30, 180)  # (connect, read)

# === Логирование и файлы ===
EXTRACTION_RESULTS_DIR = os.path.join(ROOT_DIR, "results")
os.makedirs(EXTRACTION_RESULTS_DIR, exist_ok=True)
