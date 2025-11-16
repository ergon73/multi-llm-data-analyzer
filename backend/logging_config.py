"""
Конфигурация централизованного логирования с JSON форматом и correlation IDs.
"""
import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from flask import request, has_request_context, g


class JSONFormatter(logging.Formatter):
    """
    Форматтер для JSON логирования с поддержкой correlation IDs.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Форматирует лог запись в JSON формат.
        
        Args:
            record: LogRecord для форматирования
            
        Returns:
            JSON строка с лог записью
        """
        log_data: Dict[str, Any] = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Добавляем correlation ID если доступен
        if has_request_context():
            correlation_id = getattr(g, 'correlation_id', None)
            if correlation_id:
                log_data['correlation_id'] = correlation_id
            
            # Добавляем информацию о запросе
            log_data['request'] = {
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr,
            }
        
        # Добавляем exception информацию если есть
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Добавляем дополнительные поля из extra
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data, ensure_ascii=False)


class CorrelationIDFilter(logging.Filter):
    """
    Фильтр для добавления correlation ID в лог записи.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Добавляет correlation ID в record если доступен.
        
        Args:
            record: LogRecord для фильтрации
            
        Returns:
            True всегда (не фильтрует записи)
        """
        if has_request_context():
            correlation_id = getattr(g, 'correlation_id', None)
            if correlation_id:
                record.correlation_id = correlation_id
        return True


def setup_logging(
    level: str = 'INFO',
    json_format: bool = False,
    log_file: Optional[str] = None
) -> None:
    """
    Настраивает логирование для приложения.
    
    Args:
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Использовать JSON формат вместо стандартного
        log_file: Путь к файлу для записи логов (опционально)
    """
    # Получаем root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Удаляем существующие handlers
    root_logger.handlers.clear()
    
    # Создаем formatter
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(formatter)
    console_handler.addFilter(CorrelationIDFilter())
    root_logger.addHandler(console_handler)
    
    # File handler (если указан файл)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        file_handler.addFilter(CorrelationIDFilter())
        root_logger.addHandler(file_handler)
    
    # Настраиваем логирование для внешних библиотек
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def generate_correlation_id() -> str:
    """
    Генерирует уникальный correlation ID для запроса.
    
    Returns:
        UUID строка для correlation ID
    """
    import uuid
    return str(uuid.uuid4())


def get_correlation_id() -> Optional[str]:
    """
    Получает correlation ID из текущего контекста запроса.
    
    Returns:
        Correlation ID или None если не в контексте запроса
    """
    if has_request_context():
        return getattr(g, 'correlation_id', None)
    return None

