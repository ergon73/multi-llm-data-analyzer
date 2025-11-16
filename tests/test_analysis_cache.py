"""
Тесты для сервиса кэширования LLM анализа.
"""
import pytest
import time
from backend.services.analysis_cache import AnalysisCache


class TestAnalysisCache:
    """Тесты для класса AnalysisCache."""
    
    def test_make_key(self):
        """Тест создания ключа кэша."""
        cache = AnalysisCache(ttl_sec=60, max_size=10)
        key1 = cache.make_key("openai", "gpt-4", "test data")
        key2 = cache.make_key("openai", "gpt-4", "test data")
        key3 = cache.make_key("yandex", "yandexgpt", "test data")
        
        # Одинаковые данные должны давать одинаковый ключ
        assert key1 == key2
        # Разные данные должны давать разные ключи
        assert key1 != key3
        # Ключ должен содержать провайдера и модель
        assert "openai" in key1
        assert "gpt-4" in key1
    
    def test_get_put(self):
        """Тест сохранения и получения из кэша."""
        cache = AnalysisCache(ttl_sec=60, max_size=10)
        key = cache.make_key("openai", "gpt-4", "test")
        
        # Пустой кэш должен возвращать None
        assert cache.get(key) is None
        
        # Сохраняем значение
        cache.put(key, "test analysis")
        assert cache.get(key) == "test analysis"
    
    def test_ttl_expiration(self):
        """Тест истечения TTL."""
        cache = AnalysisCache(ttl_sec=1, max_size=10)
        key = cache.make_key("openai", "gpt-4", "test")
        
        cache.put(key, "test analysis")
        assert cache.get(key) == "test analysis"
        
        # Ждем истечения TTL
        time.sleep(1.1)
        assert cache.get(key) is None
    
    def test_max_size_limit(self):
        """Тест ограничения размера кэша."""
        cache = AnalysisCache(ttl_sec=60, max_size=3)
        
        # Добавляем больше записей, чем максимум
        for i in range(5):
            key = cache.make_key("openai", "gpt-4", f"test{i}")
            cache.put(key, f"analysis{i}")
        
        # Кэш не должен превышать максимальный размер
        assert cache.size() <= 3
        
        # Самые старые записи должны быть удалены
        oldest_key = cache.make_key("openai", "gpt-4", "test0")
        assert cache.get(oldest_key) is None
    
    def test_clear(self):
        """Тест очистки кэша."""
        cache = AnalysisCache(ttl_sec=60, max_size=10)
        key = cache.make_key("openai", "gpt-4", "test")
        
        cache.put(key, "test analysis")
        assert cache.size() == 1
        
        cache.clear()
        assert cache.size() == 0
        assert cache.get(key) is None
    
    def test_cleanup_expired(self):
        """Тест очистки истекших записей."""
        cache = AnalysisCache(ttl_sec=1, max_size=10)
        
        # Добавляем записи с разным временем жизни
        key1 = cache.make_key("openai", "gpt-4", "test1")
        cache.put(key1, "analysis1")
        
        key2 = cache.make_key("openai", "gpt-4", "test2")
        cache.put(key2, "analysis2")
        
        # Ждем истечения TTL для первой записи
        time.sleep(1.1)
        
        # Очищаем истекшие записи
        removed = cache.cleanup_expired()
        assert removed >= 1
        assert cache.get(key1) is None
        assert cache.get(key2) is None or cache.get(key2) == "analysis2"
    
    def test_size(self):
        """Тест получения размера кэша."""
        cache = AnalysisCache(ttl_sec=60, max_size=10)
        assert cache.size() == 0
        
        for i in range(3):
            key = cache.make_key("openai", "gpt-4", f"test{i}")
            cache.put(key, f"analysis{i}")
        
        assert cache.size() == 3

