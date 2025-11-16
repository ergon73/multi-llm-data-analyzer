"""
Сервис для базового анализа табличных данных.
"""
import pandas as pd
import logging
from backend.types import BasicAnalysis, NumericStats, StringStats

logger = logging.getLogger(__name__)


def perform_basic_analysis(df: pd.DataFrame) -> BasicAnalysis:
    """
    Выполняет базовый анализ данных DataFrame.
    
    Анализирует числовые и строковые колонки:
    - Числовые: сумма, среднее, минимум, максимум
    - Строковые: количество уникальных значений, первые 10 уникальных значений
    
    Args:
        df: DataFrame для анализа
        
    Returns:
        BasicAnalysis с результатами анализа по типам колонок
    """
    logger.debug(f"Starting basic analysis. DataFrame shape: {df.shape}")
    logger.debug(f"DataFrame columns: {df.columns.tolist()}")
    
    analysis: BasicAnalysis = {
        'numeric_columns': {},
        'string_columns': {}
    }
    
    for column in df.columns:
        logger.debug(f"Analyzing column: {column}")
        
        if pd.api.types.is_numeric_dtype(df[column]):
            logger.debug(f"Column {column} is numeric")
            stats = _analyze_numeric_column(df[column])
            analysis['numeric_columns'][column] = stats
            logger.debug(f"Numeric analysis for {column}: {stats}")
        else:
            logger.debug(f"Column {column} is string")
            stats = _analyze_string_column(df[column])
            analysis['string_columns'][column] = stats
            logger.debug(f"String analysis for {column}: {stats}")
    
    return analysis


def _analyze_numeric_column(series: pd.Series) -> NumericStats:
    """
    Анализирует числовую колонку.
    
    Args:
        series: Series с числовыми данными
        
    Returns:
        NumericStats с статистикой колонки
    """
    # Обрабатываем NaN значения
    column_data = series.dropna()
    
    if len(column_data) > 0:
        return {
            'sum': float(column_data.sum()),
            'mean': float(column_data.mean()),
            'min': float(column_data.min()),
            'max': float(column_data.max())
        }
    else:
        # Пустая колонка - возвращаем нули
        return {
            'sum': 0.0,
            'mean': 0.0,
            'min': 0.0,
            'max': 0.0
        }


def _analyze_string_column(series: pd.Series) -> StringStats:
    """
    Анализирует строковую колонку.
    
    Args:
        series: Series со строковыми данными
        
    Returns:
        StringStats с статистикой колонки
    """
    # Обрабатываем NaN значения
    unique_values = series.dropna().unique().tolist()[:10]
    
    return {
        'unique_values_count': int(series.nunique()),
        'unique_values': unique_values
    }

