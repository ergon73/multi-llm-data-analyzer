"""
Сервис для кэширования результатов LLM анализа.
"""
import time
import hashlib
import logging
from typing import Optional
from backend.config import Config

logger = logging.getLogger(__name__)


class AnalysisCache:
    """
    Кэш для результатов LLM анализа с TTL и ограничением размера.
    
    Использует LRU-подобную стратегию: при достижении максимума удаляется
    самый старый элемент.
    """
    
    def __init__(
        self,
        ttl_sec: Optional[int] = None,
        max_size: Optional[int] = None
    ):
        """
        Инициализирует кэш анализа.
        
        Args:
            ttl_sec: Время жизни записи в секундах (по умолчанию из Config)
            max_size: Максимальное количество записей (по умолчанию из Config)
        """
        self._ttl_sec = ttl_sec or Config.ANALYSIS_CACHE_TTL_SEC
        self._max_size = max_size or Config.ANALYSIS_CACHE_MAX
        self._cache: dict[str, tuple[float, str]] = {}
    
    def make_key(self, provider: str, model: str, table_string: str) -> str:
        """
        Создает ключ кэша для анализа на основе провайдера, модели и данных.
        
        Args:
            provider: Провайдер LLM ('openai', 'yandex', 'giga')
            model: Название модели
            table_string: Строковое представление таблицы
            
        Returns:
            Ключ кэша в формате "provider:model:hash"
        """
        h = hashlib.sha256(table_string.encode("utf-8")).hexdigest()
        return f"{provider}:{model}:{h}"
    
    def get(self, key: str) -> Optional[str]:
        """
        Получает закэшированный анализ по ключу.
        
        Args:
            key: Ключ кэша
            
        Returns:
            Закэшированный анализ или None если кэш истек или отсутствует
        """
        item = self._cache.get(key)
        if not item:
            return None
        
        timestamp, value = item
        now = time.time()
        
        if now - timestamp <= self._ttl_sec:
            return value
        
        # Кэш истек - удаляем запись
        self._cache.pop(key, None)
        return None
    
    def put(self, key: str, value: str) -> None:
        """
        Сохраняет анализ в кэш с автоматической очисткой старых записей.
        
        Args:
            key: Ключ кэша
            value: Результат анализа для сохранения
        """
        if len(self._cache) >= self._max_size:
            # Удаляем самый старый элемент (LRU)
            oldest_key = min(self._cache, key=lambda k: self._cache[k][0])
            self._cache.pop(oldest_key, None)
            logger.debug(f"Cache full, removed oldest entry: {oldest_key[:20]}...")
        
        self._cache[key] = (time.time(), value)
        logger.debug(f"Cached analysis with key: {key[:20]}...")
    
    def clear(self) -> None:
        """Очищает весь кэш."""
        self._cache.clear()
        logger.debug("Analysis cache cleared")
    
    def size(self) -> int:
        """Возвращает текущее количество записей в кэше."""
        return len(self._cache)
    
    def cleanup_expired(self) -> int:
        """
        Удаляет все истекшие записи из кэша.
        
        Returns:
            Количество удаленных записей
        """
        now = time.time()
        expired_keys = [
            key for key, (timestamp, _) in self._cache.items()
            if now - timestamp > self._ttl_sec
        ]
        
        for key in expired_keys:
            self._cache.pop(key, None)
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)


# Глобальный экземпляр кэша
_global_cache: Optional[AnalysisCache] = None


def get_cache() -> AnalysisCache:
    """
    Возвращает глобальный экземпляр кэша анализа (singleton).
    
    Returns:
        Глобальный экземпляр AnalysisCache
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = AnalysisCache()
    return _global_cache

