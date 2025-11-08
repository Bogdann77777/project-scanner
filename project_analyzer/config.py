import os
from dotenv import load_dotenv

load_dotenv()  # Загружает .env файл


class Config:
    # OpenRouter API
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

    # Модель для описаний (можно менять через UI)
    LLM_MODEL = os.getenv("LLM_MODEL", "minimax/minimax-m2")

    # Альтернативные модели (для выбора в UI)
    AVAILABLE_MODELS = [
        "anthropic/claude-3-5-haiku-20241022",
        "openai/gpt-4o-mini",
        "deepseek/deepseek-chat",  # Обновлено: deepseek-coder устарел
        "qwen/qwen-2.5-coder-32b-instruct",  # Qwen2.5 Coder 32B - отличная кодер-модель
        "google/gemini-flash-1.5",
        "minimax/minimax-m2"
    ]

    # Настройки анализа
    MAX_FUNCTIONS_PER_BATCH = 10  # Сколько функций описывать за раз
    SUPPORTED_EXTENSIONS = [".py", ".js", ".ts", ".jsx", ".tsx"]
    IGNORE_DIRS = ["node_modules", "__pycache__", ".git", "venv", "env", ".venv"]

    # UI настройки
    UI_PORT = 8000
    UI_HOST = "0.0.0.0"
    DEBUG = True

    # Timeouts
    LLM_TIMEOUT = 60  # секунд на один батч
    MAX_FILE_SIZE = 1024 * 1024  # 1MB максимум на файл
