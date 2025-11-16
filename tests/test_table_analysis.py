"""
Тесты для сервиса анализа таблиц.
"""
import pytest
import pandas as pd
import numpy as np
from backend.services.table_analysis import perform_basic_analysis
from backend.types import BasicAnalysis


class TestTableAnalysis:
    """Тесты для функции perform_basic_analysis."""
    
    def test_empty_dataframe(self):
        """Тест анализа пустого DataFrame."""
        df = pd.DataFrame()
        result = perform_basic_analysis(df)
        
        assert isinstance(result, dict)
        assert 'numeric_columns' in result
        assert 'string_columns' in result
        assert len(result['numeric_columns']) == 0
        assert len(result['string_columns']) == 0
    
    def test_numeric_columns(self):
        """Тест анализа числовых колонок."""
        df = pd.DataFrame({
            'col1': [1, 2, 3, 4, 5],
            'col2': [10.5, 20.5, 30.5, 40.5, 50.5]
        })
        
        result = perform_basic_analysis(df)
        
        assert 'col1' in result['numeric_columns']
        assert 'col2' in result['numeric_columns']
        
        col1_stats = result['numeric_columns']['col1']
        assert col1_stats['sum'] == 15.0
        assert col1_stats['mean'] == 3.0
        assert col1_stats['min'] == 1.0
        assert col1_stats['max'] == 5.0
    
    def test_string_columns(self):
        """Тест анализа строковых колонок."""
        df = pd.DataFrame({
            'name': ['Alice', 'Bob', 'Alice', 'Charlie', 'Bob'],
            'city': ['Moscow', 'SPB', 'Moscow', 'Moscow', 'SPB']
        })
        
        result = perform_basic_analysis(df)
        
        assert 'name' in result['string_columns']
        assert 'city' in result['string_columns']
        
        name_stats = result['string_columns']['name']
        assert name_stats['unique_values_count'] == 3
        assert 'Alice' in name_stats['unique_values']
        assert 'Bob' in name_stats['unique_values']
        assert 'Charlie' in name_stats['unique_values']
    
    def test_mixed_columns(self):
        """Тест анализа смешанных типов колонок."""
        df = pd.DataFrame({
            'numeric': [1, 2, 3],
            'string': ['a', 'b', 'c'],
            'mixed': [1, 'text', 3]
        })
        
        result = perform_basic_analysis(df)
        
        assert 'numeric' in result['numeric_columns']
        assert 'string' in result['string_columns']
        # mixed будет обработан как строковая колонка
        assert 'mixed' in result['string_columns']
    
    def test_nan_handling(self):
        """Тест обработки NaN значений."""
        df = pd.DataFrame({
            'numeric_with_nan': [1, 2, np.nan, 4, 5],
            'string_with_nan': ['a', 'b', None, 'd', 'e']
        })
        
        result = perform_basic_analysis(df)
        
        # Числовая колонка должна игнорировать NaN
        numeric_stats = result['numeric_columns']['numeric_with_nan']
        assert numeric_stats['sum'] == 12.0  # 1+2+4+5
        assert numeric_stats['mean'] == 3.0  # 12/4
        
        # Строковая колонка должна игнорировать NaN
        string_stats = result['string_columns']['string_with_nan']
        assert string_stats['unique_values_count'] == 4  # a, b, d, e
    
    def test_empty_numeric_column(self):
        """Тест анализа пустой числовой колонки."""
        df = pd.DataFrame({
            'empty_numeric': [np.nan, np.nan, np.nan]
        })
        
        result = perform_basic_analysis(df)
        
        stats = result['numeric_columns']['empty_numeric']
        assert stats['sum'] == 0.0
        assert stats['mean'] == 0.0
        assert stats['min'] == 0.0
        assert stats['max'] == 0.0
    
    def test_large_unique_values(self):
        """Тест ограничения уникальных значений (первые 10)."""
        df = pd.DataFrame({
            'many_values': [f'value_{i}' for i in range(20)]
        })
        
        result = perform_basic_analysis(df)
        
        stats = result['string_columns']['many_values']
        assert stats['unique_values_count'] == 20
        assert len(stats['unique_values']) == 10  # Ограничение до 10
    
    def test_return_type(self):
        """Тест типа возвращаемого значения."""
        df = pd.DataFrame({'col': [1, 2, 3]})
        result = perform_basic_analysis(df)
        
        assert isinstance(result, dict)
        assert isinstance(result['numeric_columns'], dict)
        assert isinstance(result['string_columns'], dict)

