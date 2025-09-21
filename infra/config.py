# -*- coding: utf-8 -*-
"""
Глобальные константы и настройки проекта.
"""
import os

# === Пути ===
INFRA_DIR = os.path.dirname(os.path.abspath(__file__))   # .../project-root/infra
PROJECT_ROOT = os.path.dirname(INFRA_DIR)                # .../project-root
PROMPTS_DIR = os.path.join(PROJECT_ROOT, "prompts")

API_KEY_PATH = os.path.join("C:\\", "API_keys", "API_key_GPT.txt")
SYSTEM_PROMPT_PATH = os.path.join(PROMPTS_DIR, "tender_extractor_system.prompt.md")

# === OpenAI API ===
BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4.1-mini"

# === Сетевые таймауты ===
TIMEOUT = (30, 180)  # (connect, read)

# === Размер UI окна ===
WINDOW_SIZE = "980x720"
WINDOW_TITLE = "Vector Store Uploader"

# === Шрифт UI окна ===
LOG_TEXT_HEIGHT = 28
LOG_FONT = ("Consolas", 10)

PAD_X = 10
PAD_Y = 8
PAD_Y_LOG = 6
PAD_ENTRY = (4, 0)
PAD_CHECK = (8, 4)
PAD_BTN = 10

AUTO_DELETE_DEFAULT_MIN = 30
AUTO_DELETE_MIN_LIMIT = 1

# === Логирование и файлы ===
EXTRACTION_RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
os.makedirs(EXTRACTION_RESULTS_DIR, exist_ok=True)

# === Окно журнала ===
JOURNAL_WINDOW_SIZE = "900x560"
JOURNAL_MAX_RECORDS = 1000
