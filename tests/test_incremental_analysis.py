"""
Тесты для инкрементального анализа данных.
"""
import pandas as pd
import pytest
from backend.services.incremental_analysis import IncrementalAnalysis


class TestIncrementalAnalysis:
    """Тесты для класса IncrementalAnalysis."""
    
    def test_initialize_analysis(self):
        """Тест инициализации анализа для первой страницы."""
        inc_analysis = IncrementalAnalysis()
        df = pd.DataFrame({
            'price': [100, 200, 300],
            'make': ['Toyota', 'Honda', 'Toyota']
        })
        
        analysis = inc_analysis.initialize_analysis('dataset1', df)
        
        assert 'numeric_columns' in analysis
        assert 'string_columns' in analysis
        assert 'price' in analysis['numeric_columns']
        assert 'make' in analysis['string_columns']
        assert inc_analysis.get_analyzed_rows('dataset1') == 3
    
    def test_update_analysis_adds_new_data(self):
        """Тест обновления анализа при добавлении новых данных."""
        inc_analysis = IncrementalAnalysis()
        
        # Первая страница
        df1 = pd.DataFrame({
            'price': [100, 200],
            'make': ['Toyota', 'Honda']
        })
        analysis1 = inc_analysis.initialize_analysis('dataset1', df1)
        
        # Вторая страница
        df2 = pd.DataFrame({
            'price': [300, 400],
            'make': ['Toyota', 'BMW']
        })
        analysis2 = inc_analysis.update_analysis('dataset1', df2)
        
        # Проверяем, что статистика обновилась
        assert analysis2['numeric_columns']['price']['sum'] == 1000  # 100+200+300+400
        assert analysis2['numeric_columns']['price']['min'] == 100
        assert analysis2['numeric_columns']['price']['max'] == 400
        assert inc_analysis.get_analyzed_rows('dataset1') == 4
    
    def test_update_analysis_merges_string_stats(self):
        """Тест объединения статистики строковых колонок."""
        inc_analysis = IncrementalAnalysis()
        
        df1 = pd.DataFrame({'make': ['Toyota', 'Honda']})
        inc_analysis.initialize_analysis('dataset1', df1)
        
        df2 = pd.DataFrame({'make': ['BMW', 'Toyota']})
        analysis = inc_analysis.update_analysis('dataset1', df2)
        
        # Проверяем уникальные значения
        unique_values = set(analysis['string_columns']['make']['unique_values'])
        assert 'Toyota' in unique_values
        assert 'Honda' in unique_values
        assert 'BMW' in unique_values
    
    def test_get_analysis_returns_none_for_missing_dataset(self):
        """Тест получения анализа для несуществующего датасета."""
        inc_analysis = IncrementalAnalysis()
        assert inc_analysis.get_analysis('nonexistent') is None
    
    def test_clear_analysis(self):
        """Тест очистки анализа для датасета."""
        inc_analysis = IncrementalAnalysis()
        df = pd.DataFrame({'price': [100, 200]})
        inc_analysis.initialize_analysis('dataset1', df)
        
        assert inc_analysis.get_analysis('dataset1') is not None
        
        inc_analysis.clear_analysis('dataset1')
        
        assert inc_analysis.get_analysis('dataset1') is None
        assert inc_analysis.get_analyzed_rows('dataset1') == 0
    
    def test_update_analysis_with_empty_dataframe(self):
        """Тест обновления анализа с пустым DataFrame."""
        inc_analysis = IncrementalAnalysis()
        df1 = pd.DataFrame({'price': [100, 200]})
        inc_analysis.initialize_analysis('dataset1', df1)
        
        df2 = pd.DataFrame({'price': []})
        analysis = inc_analysis.update_analysis('dataset1', df2)
        
        # Анализ должен остаться прежним
        assert analysis['numeric_columns']['price']['sum'] == 300
    
    def test_incremental_mean_calculation(self):
        """Тест корректного расчета среднего значения инкрементально."""
        inc_analysis = IncrementalAnalysis()
        
        # Первая страница: [10, 20] -> mean = 15
        df1 = pd.DataFrame({'value': [10, 20]})
        analysis1 = inc_analysis.initialize_analysis('dataset1', df1)
        assert analysis1['numeric_columns']['value']['mean'] == 15.0
        
        # Вторая страница: [30, 40] -> общий mean должен быть 25
        df2 = pd.DataFrame({'value': [30, 40]})
        analysis2 = inc_analysis.update_analysis('dataset1', df2)
        assert analysis2['numeric_columns']['value']['mean'] == 25.0
        assert analysis2['numeric_columns']['value']['sum'] == 100.0

