"""
Централизованная конфигурация приложения.
Читает переменные окружения, предоставляет валидацию и дефолты.
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Загружаем .env из корня проекта
_root_env_path = Path(__file__).resolve().parents[1] / '.env'
load_dotenv(dotenv_path=_root_env_path)


def _get_bool(key: str, default: str = "false") -> bool:
    """
    Преобразует строковое значение переменной окружения в булево.
    "false", "0", "no" (case-insensitive) → False, иначе True.
    """
    value = os.getenv(key, default).lower()
    return value not in ("false", "0", "no")


class Config:
    """Централизованный класс конфигурации."""
    
    # LLM API Keys
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    YANDEX_FOLDER_ID: Optional[str] = os.getenv("YANDEX_FOLDER_ID")
    YANDEX_API_KEY: Optional[str] = os.getenv("YANDEX_API_KEY")
    GIGACHAT_CREDENTIALS: Optional[str] = os.getenv("GIGACHAT_CREDENTIALS")
    GIGACHAT_CERT_PATH: Optional[str] = os.getenv("GIGACHAT_CERT_PATH")
    GIGACHAT_VERIFY_SSL_CERTS: bool = _get_bool("GIGACHAT_VERIFY_SSL_CERTS", "true")
    
    # Security & Rate Limiting
    API_KEY: Optional[str] = os.getenv("API_KEY")  # опционально, если не задан - проверка отключена
    RATE_LIMIT_WINDOW_SEC: int = int(os.getenv("RATE_LIMIT_WINDOW_SEC", "60"))
    RATE_LIMIT_MAX_REQ: int = int(os.getenv("RATE_LIMIT_MAX_REQ", "60"))
    
    # Flask
    FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "0") in ("1", "true", "True")
    
    # Test Mode
    TEST_MODE: bool = os.getenv("TEST_MODE", "false").lower() in ("true", "1")
    
    # Cache
    ANALYSIS_CACHE_TTL_SEC: int = int(os.getenv("ANALYSIS_CACHE_TTL_SEC", "600"))
    ANALYSIS_CACHE_MAX: int = int(os.getenv("ANALYSIS_CACHE_MAX", "256"))
    
    # Temp files cleanup (minutes)
    TEMP_CLEANUP_AGE_MIN: int = int(os.getenv("TEMP_CLEANUP_AGE_MIN", "30"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_JSON_FORMAT: bool = _get_bool("LOG_JSON_FORMAT", "false")
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE")
    
    @classmethod
    def validate(cls) -> None:
        """
        Проверяет наличие обязательных переменных окружения.
        В TEST_MODE не требует LLM ключей, но предупреждает об отсутствии API_KEY.
        
        Raises:
            ValueError: если отсутствуют обязательные переменные
        """
        missing = []
        warnings = []
        
        # В TEST_MODE не требуем LLM ключи, но проверяем API_KEY
        if not cls.TEST_MODE:
            # В production режиме требуем хотя бы один LLM провайдер
            has_any_provider = (
                cls.OPENAI_API_KEY or
                (cls.YANDEX_API_KEY and cls.YANDEX_FOLDER_ID) or
                cls.GIGACHAT_CREDENTIALS
            )
            
            if not has_any_provider:
                missing.append("At least one LLM provider must be configured (OPENAI_API_KEY, YANDEX_API_KEY+YANDEX_FOLDER_ID, or GIGACHAT_CREDENTIALS)")
        
        # API_KEY рекомендуется даже в TEST_MODE для безопасности
        if not cls.API_KEY:
            warnings.append("API_KEY is not set - API endpoints will be open to everyone (security risk!)")
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        if warnings:
            import warnings as py_warnings
            for warning in warnings:
                py_warnings.warn(warning, UserWarning)
    
    @classmethod
    def get_debug_flag(cls) -> bool:
        """Возвращает флаг debug для Flask."""
        return cls.FLASK_DEBUG

