"""
Тесты для вспомогательных функций backend/pdf_server.py.
"""
import os
import tempfile
import pandas as pd
import pytest

os.environ.setdefault("TEST_MODE", "true")

from backend.pdf_server import (
    _csv_count_rows_fast,
    _csv_get_page,
    normalize_record,
    _make_dataset_id
)


class TestCSVHelpers:
    """Тесты для функций работы с CSV."""
    
    def test_csv_count_rows_fast(self):
        """Тест быстрого подсчета строк в CSV."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("col1,col2\n")
            f.write("1,2\n")
            f.write("3,4\n")
            f.write("5,6\n")
            temp_path = f.name
        
        try:
            count = _csv_count_rows_fast(temp_path)
            assert count == 3  # 3 строки данных без заголовка
        finally:
            os.unlink(temp_path)
    
    def test_csv_count_rows_fast_empty_file(self):
        """Тест подсчета строк в пустом CSV."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("col1,col2\n")
            temp_path = f.name
        
        try:
            count = _csv_count_rows_fast(temp_path)
            assert count == 0
        finally:
            os.unlink(temp_path)
    
    def test_csv_get_page_first_page(self):
        """Тест получения первой страницы CSV."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            df = pd.DataFrame({'col1': range(10), 'col2': range(10, 20)})
            df.to_csv(f.name, index=False)
            temp_path = f.name
        
        try:
            df_page, columns = _csv_get_page(temp_path, page=1, page_size=5)
            assert len(df_page) == 5
            assert len(columns) == 2
            assert 'col1' in columns
            assert 'col2' in columns
        finally:
            os.unlink(temp_path)
    
    def test_csv_get_page_second_page(self):
        """Тест получения второй страницы CSV."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            df = pd.DataFrame({'col1': range(10), 'col2': range(10, 20)})
            df.to_csv(f.name, index=False)
            temp_path = f.name
        
        try:
            df_page, columns = _csv_get_page(temp_path, page=2, page_size=5)
            assert len(df_page) == 5
            assert df_page.iloc[0]['col1'] == 5  # Начинается с 5-й строки
        finally:
            os.unlink(temp_path)
    
    def test_csv_get_page_beyond_data(self):
        """Тест получения страницы за пределами данных."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            df = pd.DataFrame({'col1': [1, 2, 3]})
            df.to_csv(f.name, index=False)
            temp_path = f.name
        
        try:
            df_page, columns = _csv_get_page(temp_path, page=10, page_size=5)
            # Должен вернуть пустой DataFrame или меньше строк
            assert len(df_page) <= 5
        finally:
            os.unlink(temp_path)


class TestNormalizeRecord:
    """Тесты для функции normalize_record."""
    
    def test_normalize_record_fills_missing_fields(self):
        """Тест заполнения отсутствующих полей."""
        record = {'make': 'Toyota'}
        normalized = normalize_record(record)
        
        # Проверяем что отсутствующие поля заполнены
        assert 'year' in normalized
        assert normalized['year'] == 0  # Числовые поля = 0
        assert normalized['make'] == 'Toyota'  # Существующее значение сохранено
    
    def test_normalize_record_preserves_existing_values(self):
        """Тест сохранения существующих значений."""
        record = {'make': 'Toyota', 'model': 'Camry', 'year': 2020, 'condition': 5.0}
        normalized = normalize_record(record)
        
        assert normalized['make'] == 'Toyota'
        assert normalized['model'] == 'Camry'
        assert normalized['year'] == 2020
        assert normalized['condition'] == 5.0
    
    def test_normalize_record_handles_empty_strings(self):
        """Тест обработки пустых строк."""
        record = {'make': '', 'model': 'Camry'}
        normalized = normalize_record(record)
        
        # Пустые строки должны быть заменены на None
        assert normalized['make'] is None
    
    def test_normalize_record_handles_numeric_fields(self):
        """Тест обработки числовых полей."""
        record = {'year': None, 'odometer': '', 'condition': None}
        normalized = normalize_record(record)
        
        assert normalized['year'] == 0
        assert normalized['odometer'] == 0
        assert normalized['condition'] == 0.0  # float для condition
    
    def test_normalize_record_handles_all_required_fields(self):
        """Тест что все обязательные поля обрабатываются."""
        record = {}
        normalized = normalize_record(record)
        
        required_fields = ['year', 'make', 'model', 'trim', 'body', 'transmission', 'vin', 
                          'state', 'condition', 'odometer', 'color', 'interior', 'seller', 
                          'mmr', 'sellingprice', 'saledate']
        
        for field in required_fields:
            assert field in normalized


class TestDatasetID:
    """Тесты для функции _make_dataset_id."""
    
    def test_make_dataset_id_creates_unique_ids(self):
        """Тест создания уникальных ID для разных файлов."""
        with tempfile.NamedTemporaryFile(delete=False) as f1:
            f1.write(b'test1')
            path1 = f1.name
        
        with tempfile.NamedTemporaryFile(delete=False) as f2:
            f2.write(b'test2')
            path2 = f2.name
        
        try:
            id1 = _make_dataset_id(path1)
            id2 = _make_dataset_id(path2)
            
            assert id1 != id2
            assert len(id1) == 16  # 16-символьный хеш
            assert len(id2) == 16
        finally:
            os.unlink(path1)
            os.unlink(path2)
    
    def test_make_dataset_id_same_file_same_id(self):
        """Тест что один и тот же файл дает одинаковый ID."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'test')
            path = f.name
        
        try:
            id1 = _make_dataset_id(path)
            id2 = _make_dataset_id(path)
            
            assert id1 == id2
        finally:
            os.unlink(path)

