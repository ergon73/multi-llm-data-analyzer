"""
Тесты для обработки ошибок и валидации.
"""
import os
import json
import pytest

os.environ.setdefault("TEST_MODE", "true")

from backend.pdf_server import app
from backend.errors import ValidationError


@pytest.fixture()
def client():
    """Фикстура для тестового клиента Flask."""
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


class TestErrorHandling:
    """Тесты для обработки ошибок."""
    
    def test_upload_no_file(self, client):
        """Тест загрузки без файла."""
        resp = client.post('/api/upload')
        assert resp.status_code == 400
    
    def test_upload_empty_filename(self, client):
        """Тест загрузки с пустым именем файла."""
        data = {'file': ('', '')}
        resp = client.post('/api/upload', data=data, content_type='multipart/form-data')
        assert resp.status_code == 400
    
    def test_upload_unsupported_format(self, client):
        """Тест загрузки неподдерживаемого формата."""
        data = {'file': (b'content', 'test.txt')}
        resp = client.post('/api/upload', data=data, content_type='multipart/form-data')
        assert resp.status_code == 400
    
    def test_analyze_missing_fields(self, client):
        """Тест анализа с отсутствующими полями."""
        resp = client.post('/api/analyze',
                          data=json.dumps({}),
                          content_type='application/json')
        assert resp.status_code == 400
    
    def test_analyze_missing_provider(self, client):
        """Тест анализа без provider."""
        resp = client.post('/api/analyze',
                          data=json.dumps({
                              'model': 'gpt-4.1',
                              'table_data': []
                          }),
                          content_type='application/json')
        assert resp.status_code == 400
    
    def test_analyze_missing_model(self, client):
        """Тест анализа без model."""
        resp = client.post('/api/analyze',
                          data=json.dumps({
                              'provider': 'openai',
                              'table_data': []
                          }),
                          content_type='application/json')
        assert resp.status_code == 400
    
    def test_fill_missing_ai_missing_fields(self, client):
        """Тест fill-missing-ai с отсутствующими полями."""
        resp = client.post('/api/fill-missing-ai',
                          data=json.dumps({}),
                          content_type='application/json')
        assert resp.status_code == 400
    
    def test_report_missing_html(self, client):
        """Тест генерации отчета без HTML."""
        resp = client.post('/api/report',
                          data=json.dumps({}),
                          content_type='application/json')
        assert resp.status_code == 400
    
    def test_report_too_large_html(self, client):
        """Тест генерации отчета с слишком большим HTML."""
        large_html = 'x' * 300000  # Больше лимита
        resp = client.post('/api/report',
                          data=json.dumps({'report_html': large_html}),
                          content_type='application/json')
        assert resp.status_code == 400
    
    def test_upload_page_missing_dataset_id(self, client):
        """Тест пагинации без dataset_id."""
        resp = client.post('/api/upload/page',
                          data=json.dumps({'page': 1}),
                          content_type='application/json')
        assert resp.status_code == 400


class TestValidationError:
    """Тесты для ValidationError."""
    
    def test_validation_error_message(self):
        """Тест что ValidationError содержит сообщение."""
        error = ValidationError("Test error")
        assert str(error) == "Test error"
    
    def test_validation_error_without_message(self):
        """Тест ValidationError без сообщения."""
        error = ValidationError()
        assert str(error) == "Invalid request"  # Использует public_message по умолчанию

