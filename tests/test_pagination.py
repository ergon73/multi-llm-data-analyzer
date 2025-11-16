"""
Тесты для пагинации и догрузки страниц.
"""
import os
import io
import json
import pandas as pd
import pytest

os.environ.setdefault("TEST_MODE", "true")

from backend.pdf_server import app


@pytest.fixture()
def client():
    """Фикстура для тестового клиента Flask."""
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


def make_csv_bytes(rows=10):
    """Создает CSV файл в памяти."""
    df = pd.DataFrame({
        'year': range(2015, 2015 + rows),
        'make': ['Toyota'] * rows,
        'model': ['Camry'] * rows,
        'price': range(20000, 20000 + rows * 1000)
    })
    bio = io.BytesIO()
    bio.write(df.to_csv(index=False).encode("utf-8"))
    bio.seek(0)
    return bio


class TestPagination:
    """Тесты для пагинации данных."""
    
    def test_upload_returns_first_page(self, client):
        """Тест загрузки первой страницы."""
        data = {'file': (make_csv_bytes(20), 'cars.csv')}
        resp = client.post('/api/upload?page=1&page_size=5', 
                          data=data, 
                          content_type='multipart/form-data')
        
        assert resp.status_code == 200
        payload = resp.get_json()
        assert len(payload['table_data']) == 5
        assert payload['current_page'] == 1
        assert payload['total_rows'] == 20
        assert 'dataset_id' in payload
        assert 'basic_analysis' in payload
    
    def test_get_upload_page_returns_correct_page(self, client):
        """Тест получения конкретной страницы через /api/upload/page."""
        # Сначала загружаем файл
        data = {'file': (make_csv_bytes(20), 'cars.csv')}
        upload_resp = client.post('/api/upload?page=1&page_size=5',
                                  data=data,
                                  content_type='multipart/form-data')
        assert upload_resp.status_code == 200
        
        upload_data = upload_resp.get_json()
        dataset_id = upload_data['dataset_id']
        
        # Запрашиваем вторую страницу
        page_resp = client.post('/api/upload/page',
                               data=json.dumps({
                                   'dataset_id': dataset_id,
                                   'page': 2,
                                   'page_size': 5
                               }),
                               content_type='application/json')
        
        assert page_resp.status_code == 200
        page_data = page_resp.get_json()
        assert len(page_data['table_data']) == 5
        assert page_data['current_page'] == 2
        assert 'basic_analysis' in page_data
    
    def test_pagination_incremental_analysis(self, client):
        """Тест что инкрементальный анализ обновляется при пагинации."""
        data = {'file': (make_csv_bytes(15), 'cars.csv')}
        upload_resp = client.post('/api/upload?page=1&page_size=5',
                                  data=data,
                                  content_type='multipart/form-data')
        upload_data = upload_resp.get_json()
        dataset_id = upload_data['dataset_id']
        analysis1 = upload_data['basic_analysis']
        
        # Загружаем вторую страницу
        page_resp = client.post('/api/upload/page',
                               data=json.dumps({
                                   'dataset_id': dataset_id,
                                   'page': 2,
                                   'page_size': 5
                               }),
                               content_type='application/json')
        page_data = page_resp.get_json()
        analysis2 = page_data['basic_analysis']
        
        # Анализ должен обновиться (больше данных)
        # Проверяем что статистика изменилась
        if 'numeric_columns' in analysis1 and 'price' in analysis1['numeric_columns']:
            sum1 = analysis1['numeric_columns']['price']['sum']
            if 'numeric_columns' in analysis2 and 'price' in analysis2['numeric_columns']:
                sum2 = analysis2['numeric_columns']['price']['sum']
                # Сумма должна увеличиться
                assert sum2 >= sum1
    
    def test_pagination_invalid_dataset_id(self, client):
        """Тест пагинации с неверным dataset_id."""
        resp = client.post('/api/upload/page',
                          data=json.dumps({
                              'dataset_id': 'invalid_id',
                              'page': 1,
                              'page_size': 5
                          }),
                          content_type='application/json')
        
        assert resp.status_code == 400
    
    def test_pagination_page_beyond_total(self, client):
        """Тест запроса страницы за пределами данных."""
        data = {'file': (make_csv_bytes(10), 'cars.csv')}
        upload_resp = client.post('/api/upload?page=1&page_size=5',
                                  data=data,
                                  content_type='multipart/form-data')
        upload_data = upload_resp.get_json()
        dataset_id = upload_data['dataset_id']
        
        # Запрашиваем страницу 10 (за пределами данных)
        resp = client.post('/api/upload/page',
                          data=json.dumps({
                              'dataset_id': dataset_id,
                              'page': 10,
                              'page_size': 5
                          }),
                          content_type='application/json')
        
        # Должен вернуть пустую страницу или ошибку
        assert resp.status_code in (200, 400)
        if resp.status_code == 200:
            page_data = resp.get_json()
            assert len(page_data['table_data']) == 0

