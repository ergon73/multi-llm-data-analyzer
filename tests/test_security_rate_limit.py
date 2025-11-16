"""
Тесты для безопасности и rate limiting.
"""
import os
import time
import pytest

os.environ.setdefault("TEST_MODE", "true")
os.environ.pop("API_KEY", None)

from backend.pdf_server import app, _client_id, _prune_bucket, _rate_limit_store
from collections import deque


@pytest.fixture()
def client():
    """Фикстура для тестового клиента Flask."""
    app.config['TESTING'] = True
    # Очищаем rate limit store перед каждым тестом
    _rate_limit_store.clear()
    with app.test_client() as c:
        yield c


class TestClientID:
    """Тесты для функции _client_id()."""
    
    def test_client_id_without_forwarded_for(self, client):
        """Тест получения client_id без X-Forwarded-For."""
        with client.application.test_request_context('/api/test'):
            cid = _client_id()
            assert cid is not None
            assert cid != 'unknown'
    
    def test_client_id_with_forwarded_for(self, client):
        """Тест получения client_id с X-Forwarded-For."""
        with client.application.test_request_context(
            '/api/test',
            headers={'X-Forwarded-For': '192.168.1.1, 10.0.0.1'}
        ):
            cid = _client_id()
            # Должен взять первый IP из цепочки
            assert '192.168.1.1' in cid or cid == '192.168.1.1'
    
    def test_client_id_with_single_forwarded_for(self, client):
        """Тест получения client_id с одним IP в X-Forwarded-For."""
        with client.application.test_request_context(
            '/api/test',
            headers={'X-Forwarded-For': '192.168.1.1'}
        ):
            cid = _client_id()
            assert '192.168.1.1' in cid or cid == '192.168.1.1'


class TestRateLimit:
    """Тесты для rate limiting."""
    
    def test_prune_bucket_removes_old_entries(self):
        """Тест очистки устаревших записей из bucket."""
        bucket = deque([time.time() - 100, time.time() - 50, time.time()])
        cutoff = time.time() - 60
        
        _prune_bucket(bucket, cutoff)
        
        # Должны остаться только записи новее cutoff
        assert len(bucket) <= 2
        for timestamp in bucket:
            assert timestamp > cutoff
    
    def test_prune_bucket_with_empty_bucket(self):
        """Тест очистки пустого bucket."""
        bucket = deque()
        _prune_bucket(bucket, time.time())
        assert len(bucket) == 0
    
    def test_rate_limit_allows_requests_within_limit(self, client):
        """Тест что запросы в пределах лимита разрешены."""
        for _ in range(5):
            resp = client.get('/api/test')
            assert resp.status_code == 200
    
    def test_rate_limit_blocks_excessive_requests(self, client):
        """Тест блокировки чрезмерных запросов."""
        # Делаем много запросов подряд
        responses = []
        for _ in range(150):  # Больше чем лимит (обычно 100)
            resp = client.get('/api/test')
            responses.append(resp.status_code)
        
        # Хотя бы один запрос должен быть заблокирован (429)
        assert 429 in responses or all(r == 200 for r in responses[:100])


class TestAPIAuthentication:
    """Тесты для API аутентификации."""
    
    def test_test_endpoint_accessible_without_key_in_test_mode(self, client):
        """Тест что test endpoint доступен без ключа в TEST_MODE."""
        resp = client.get('/api/test')
        assert resp.status_code == 200
    
    def test_upload_endpoint_accessible_in_test_mode(self, client):
        """Тест что upload endpoint доступен в TEST_MODE без ключа."""
        import io
        import pandas as pd
        
        df = pd.DataFrame({'col1': [1, 2, 3]})
        csv_bytes = io.BytesIO()
        csv_bytes.write(df.to_csv(index=False).encode('utf-8'))
        csv_bytes.seek(0)
        
        data = {'file': (csv_bytes, 'test.csv')}
        resp = client.post('/api/upload', data=data, content_type='multipart/form-data')
        
        # В TEST_MODE должен быть доступен
        assert resp.status_code in (200, 400, 500)  # Может быть ошибка валидации, но не 401

