"""
Сервис для инкрементального анализа табличных данных.

Позволяет обновлять базовый анализ при добавлении новых страниц данных
без необходимости пересчитывать анализ для всех данных заново.
"""
import pandas as pd
import logging
from typing import Dict, Any, Optional
from backend.types import BasicAnalysis, NumericStats, StringStats

logger = logging.getLogger(__name__)


class IncrementalAnalysis:
    """
    Управляет инкрементальным анализом данных по dataset_id.
    
    Хранит и обновляет базовый анализ при добавлении новых страниц данных.
    """
    
    def __init__(self):
        """Инициализирует хранилище для инкрементального анализа."""
        self._analyses: Dict[str, BasicAnalysis] = {}
        self._row_counts: Dict[str, int] = {}  # Количество проанализированных строк
    
    def get_analysis(self, dataset_id: str) -> Optional[BasicAnalysis]:
        """
        Получает текущий анализ для датасета.
        
        Args:
            dataset_id: Идентификатор датасета
            
        Returns:
            BasicAnalysis или None если анализ отсутствует
        """
        return self._analyses.get(dataset_id)
    
    def initialize_analysis(self, dataset_id: str, df: pd.DataFrame) -> BasicAnalysis:
        """
        Инициализирует анализ для датасета на основе первой страницы данных.
        
        Args:
            dataset_id: Идентификатор датасета
            df: DataFrame с первой страницей данных
            
        Returns:
            BasicAnalysis с результатами анализа
        """
        from backend.services.table_analysis import perform_basic_analysis
        
        analysis = perform_basic_analysis(df)
        self._analyses[dataset_id] = analysis
        self._row_counts[dataset_id] = len(df)
        
        logger.debug(f"Initialized analysis for dataset {dataset_id} with {len(df)} rows")
        return analysis
    
    def update_analysis(self, dataset_id: str, new_df: pd.DataFrame) -> BasicAnalysis:
        """
        Обновляет анализ для датасета, добавляя статистику из новой страницы данных.
        
        Объединяет статистику инкрементально:
        - Для числовых колонок: пересчитывает сумму, среднее, мин, макс
        - Для строковых колонок: объединяет уникальные значения
        
        Args:
            dataset_id: Идентификатор датасета
            new_df: DataFrame с новой страницей данных
            
        Returns:
            Обновленный BasicAnalysis
        """
        if dataset_id not in self._analyses:
            # Если анализа нет, инициализируем его
            return self.initialize_analysis(dataset_id, new_df)
        
        current_analysis = self._analyses[dataset_id]
        current_rows = self._row_counts[dataset_id]
        new_rows = len(new_df)
        
        # Объединяем DataFrame для пересчета статистики
        # В реальности мы не храним все данные, поэтому используем инкрементальный подход
        updated_analysis: BasicAnalysis = {
            'numeric_columns': {},
            'string_columns': {}
        }
        
        # Обновляем числовые колонки
        for col in new_df.columns:
            if pd.api.types.is_numeric_dtype(new_df[col]):
                updated_analysis['numeric_columns'][col] = self._merge_numeric_stats(
                    current_analysis.get('numeric_columns', {}).get(col),
                    new_df[col],
                    current_rows,
                    new_rows
                )
            else:
                updated_analysis['string_columns'][col] = self._merge_string_stats(
                    current_analysis.get('string_columns', {}).get(col),
                    new_df[col],
                    current_rows,
                    new_rows
                )
        
        # Сохраняем колонки, которые были в предыдущем анализе, но отсутствуют в новой странице
        for col, stats in current_analysis.get('numeric_columns', {}).items():
            if col not in updated_analysis['numeric_columns']:
                updated_analysis['numeric_columns'][col] = stats
        
        for col, stats in current_analysis.get('string_columns', {}).items():
            if col not in updated_analysis['string_columns']:
                updated_analysis['string_columns'][col] = stats
        
        self._analyses[dataset_id] = updated_analysis
        self._row_counts[dataset_id] = current_rows + new_rows
        
        logger.debug(f"Updated analysis for dataset {dataset_id}: {current_rows} + {new_rows} = {current_rows + new_rows} rows")
        return updated_analysis
    
    def _merge_numeric_stats(
        self,
        current_stats: Optional[NumericStats],
        new_series: pd.Series,
        current_rows: int,
        new_rows: int
    ) -> NumericStats:
        """
        Объединяет статистику числовой колонки инкрементально.
        
        Args:
            current_stats: Текущая статистика (может быть None)
            new_series: Новые данные для колонки
            current_rows: Количество строк в текущем анализе
            new_rows: Количество новых строк
            
        Returns:
            Обновленная NumericStats
        """
        new_data = new_series.dropna()
        
        if current_stats is None:
            # Первая итерация
            if len(new_data) > 0:
                return {
                    'sum': float(new_data.sum()),
                    'mean': float(new_data.mean()),
                    'min': float(new_data.min()),
                    'max': float(new_data.max())
                }
            else:
                return {'sum': 0.0, 'mean': 0.0, 'min': 0.0, 'max': 0.0}
        
        # Инкрементальное обновление
        if len(new_data) == 0:
            return current_stats
        
        new_sum = float(new_data.sum())
        new_mean = float(new_data.mean())
        new_min = float(new_data.min())
        new_max = float(new_data.max())
        
        # Объединяем статистику
        total_rows = current_rows + new_rows
        total_sum = current_stats['sum'] + new_sum
        
        # Взвешенное среднее
        if total_rows > 0:
            total_mean = (
                (current_stats['mean'] * current_rows + new_mean * new_rows) / total_rows
            )
        else:
            total_mean = 0.0
        
        # Минимум и максимум
        total_min = min(current_stats['min'], new_min)
        total_max = max(current_stats['max'], new_max)
        
        return {
            'sum': total_sum,
            'mean': total_mean,
            'min': total_min,
            'max': total_max
        }
    
    def _merge_string_stats(
        self,
        current_stats: Optional[StringStats],
        new_series: pd.Series,
        current_rows: int,
        new_rows: int
    ) -> StringStats:
        """
        Объединяет статистику строковой колонки инкрементально.
        
        Args:
            current_stats: Текущая статистика (может быть None)
            new_series: Новые данные для колонки
            current_rows: Количество строк в текущем анализе
            new_rows: Количество новых строк
            
        Returns:
            Обновленная StringStats
        """
        new_unique = set(new_series.dropna().unique())
        
        if current_stats is None:
            # Первая итерация
            unique_list = list(new_unique)[:10]
            return {
                'unique_values_count': len(new_unique),
                'unique_values': unique_list
            }
        
        # Объединяем уникальные значения
        current_unique = set(current_stats.get('unique_values', []))
        all_unique = current_unique | new_unique
        
        # Ограничиваем до 10 уникальных значений для отображения
        unique_list = list(all_unique)[:10]
        
        # Приблизительный подсчет уникальных значений
        # (точный подсчет требует хранения всех данных)
        estimated_count = max(
            current_stats.get('unique_values_count', 0),
            len(all_unique)
        )
        
        return {
            'unique_values_count': estimated_count,
            'unique_values': unique_list
        }
    
    def clear_analysis(self, dataset_id: str) -> None:
        """
        Удаляет анализ для датасета.
        
        Args:
            dataset_id: Идентификатор датасета
        """
        self._analyses.pop(dataset_id, None)
        self._row_counts.pop(dataset_id, None)
        logger.debug(f"Cleared analysis for dataset {dataset_id}")
    
    def get_analyzed_rows(self, dataset_id: str) -> int:
        """
        Возвращает количество проанализированных строк для датасета.
        
        Args:
            dataset_id: Идентификатор датасета
            
        Returns:
            Количество проанализированных строк или 0
        """
        return self._row_counts.get(dataset_id, 0)


# Глобальный экземпляр для инкрементального анализа
_incremental_analysis: Optional[IncrementalAnalysis] = None


def get_incremental_analysis() -> IncrementalAnalysis:
    """
    Возвращает глобальный экземпляр IncrementalAnalysis (singleton).
    
    Returns:
        Глобальный экземпляр IncrementalAnalysis
    """
    global _incremental_analysis
    if _incremental_analysis is None:
        _incremental_analysis = IncrementalAnalysis()
    return _incremental_analysis

