from flask import Flask, request, send_file, jsonify, Response
from weasyprint import HTML, CSS
from io import BytesIO
import pandas as pd
import pdfplumber
import tempfile
import os
import json
from typing import List, Optional, Dict, Tuple, Any, Union
from pathlib import Path
from flask_cors import CORS
import logging
from werkzeug.utils import secure_filename
from backend.types import (
    BasicAnalysis,
    FileUploadResponse,
    LLMAnalysisRequest,
    LLMAnalysisResponse,
    ReportRequest,
    FillMissingRequest,
    FillMissingResponse,
    UploadPageRequest,
    UploadPageResponse,
    TestResponse
)
from backend.services import AnalysisCache, perform_basic_analysis, get_incremental_analysis
from bleach.sanitizer import Cleaner
from backend.errors import register_error_handlers, ValidationError
from backend.config import Config
from backend.logging_config import setup_logging, generate_correlation_id, get_correlation_id
import time
import hashlib
from itertools import islice
from collections import deque

# Настраиваем логирование с JSON форматом и correlation IDs
setup_logging(
    level=Config.LOG_LEVEL,
    json_format=Config.LOG_JSON_FORMAT,
    log_file=Config.LOG_FILE
)
logger = logging.getLogger(__name__)

# Импортируем LLM-обработчик после загрузки Config
from llm.main_processor import get_analysis

app = Flask(__name__)
register_error_handlers(app)

# Настраиваем максимальный размер файла (100 МБ)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

# Ограничение на размер HTML отчёта (байт)
MAX_REPORT_HTML_BYTES = 200_000

# Санитайзер HTML (белый список тегов/атрибутов)
_html_cleaner = Cleaner(
    tags=[
        'p', 'b', 'strong', 'i', 'em', 'u',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'blockquote', 'code', 'pre', 'span', 'div', 'br', 'hr'
    ],
    attributes={
        '*': ['style'],
        'table': ['border', 'cellpadding', 'cellspacing'],
        'th': ['colspan', 'rowspan', 'align'],
        'td': ['colspan', 'rowspan', 'align'],
        'span': ['class'],
        'div': ['class']
    },
    strip=True
)

# Блокируем любые внешние обращения (URL) при генерации PDF
def _block_external_url_fetcher(url: str) -> None:
    """Блокирует внешние URL при генерации PDF для безопасности."""
    raise ValueError("External references are disabled in PDF generation")

# Настраиваем CORS более специфично
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "X-API-Key"]
    }
})

# API-авторизация и rate limiting
API_KEY = Config.API_KEY
RATE_LIMIT_WINDOW_SEC = Config.RATE_LIMIT_WINDOW_SEC
RATE_LIMIT_MAX_REQ = Config.RATE_LIMIT_MAX_REQ
_rate_limit_store: dict[str, deque[float]] = {}

def _client_id() -> str:
    """
    Извлекает идентификатор клиента для rate limiting.
    Безопасно обрабатывает X-Forwarded-For (берет первый IP из цепочки прокси).
    Не доверяет заголовку полностью - использует remote_addr как fallback.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Берем первый IP из цепочки (клиентский IP)
        # Разделяем по запятой и берем первый элемент
        client_ip = forwarded.split(",")[0].strip()
        # Валидируем что это похоже на IP (базовая проверка)
        if client_ip and len(client_ip.split(".")) == 4:
            return client_ip
    # Fallback на реальный remote_addr
    return request.remote_addr or "unknown"

def _prune_bucket(bucket: deque[float], cutoff: float) -> None:
    """Удаляет устаревшие записи из bucket (оптимизация памяти)."""
    while bucket and bucket[0] <= cutoff:
        bucket.popleft()

@app.before_request
def _set_correlation_id() -> None:
    """
    Устанавливает correlation ID для каждого запроса.
    Использует X-Correlation-ID из заголовка или генерирует новый.
    """
    from flask import g, after_this_request
    
    # Проверяем есть ли correlation ID в заголовке запроса
    correlation_id = request.headers.get('X-Correlation-ID')
    if not correlation_id:
        # Генерируем новый correlation ID
        correlation_id = generate_correlation_id()
    
    # Сохраняем в Flask g для доступа в других частях приложения
    g.correlation_id = correlation_id
    
    # Добавляем в response заголовки для клиента
    @after_this_request
    def add_correlation_id_header(response: Response) -> Response:
        response.headers['X-Correlation-ID'] = correlation_id
        return response


@app.before_request
def _security_and_rate_limit() -> Optional[Response]:
    """
    Проверяет авторизацию и применяет rate limiting для всех /api/ endpoints.
    В TEST_MODE без API_KEY выдает предупреждение, но не блокирует.
    
    Returns:
        Response с ошибкой авторизации/rate limit или None если запрос разрешен
    """
    if not request.path.startswith("/api/"):
        return
    
    # Проверка API ключа - обязательна (кроме TEST_MODE без ключа - только предупреждение)
    provided = request.headers.get("X-API-Key")
    if not API_KEY:
        # В TEST_MODE без ключа разрешаем, но логируем предупреждение
        if Config.TEST_MODE:
            logger.warning("API_KEY not set - endpoints are open (TEST_MODE enabled)")
        else:
            logger.error("API_KEY not set in production mode - security risk!")
            return jsonify({"error": "Server configuration error: API_KEY required"}), 500
    else:
        # API_KEY задан - проверяем обязательно
        if not provided or provided != API_KEY:
            return jsonify({"error": "Unauthorized"}), 401
    
    # Rate limiting
    now = time.time()
    cid = _client_id()
    bucket = _rate_limit_store.get(cid, deque())
    cutoff = now - RATE_LIMIT_WINDOW_SEC
    
    # Очищаем устаревшие записи
    _prune_bucket(bucket, cutoff)
    
    if len(bucket) >= RATE_LIMIT_MAX_REQ:
        retry_after = int(bucket[0] + RATE_LIMIT_WINDOW_SEC - now) + 1
        return jsonify({"error": "Too Many Requests", "retry_after": retry_after}), 429
    
    bucket.append(now)
    _rate_limit_store[cid] = bucket


# Глобальный экземпляр кэша анализа
_analysis_cache = AnalysisCache()


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    """
    Нормализует запись данных: заменяет отсутствующие/NaN значения на дефолты.
    
    Args:
        record: Словарь с данными записи
        
    Returns:
        Нормализованный словарь с замененными значениями
    """
    required_fields = ['year', 'make', 'model', 'trim', 'body', 'transmission', 'vin', 
                       'state', 'condition', 'odometer', 'color', 'interior', 'seller', 
                       'mmr', 'sellingprice', 'saledate']
    
    for field in required_fields:
        value = record.get(field)
        # Проверяем отсутствие или NaN
        if field not in record or pd.isna(value) or value == '':
            if field == 'condition':
                record[field] = 0.0
            elif field in ['year', 'odometer', 'mmr', 'sellingprice']:
                record[field] = 0
            else:
                record[field] = None
    
    return record


# Простое хранилище загруженных датасетов (только для lifetime процесса)
# dataset_id -> {'dir': Path, 'path': str, 'kind': 'csv'|'excel'|'pdf', 'columns': list[str], 'total_rows': int, 'created_at': float}
_datasets: Dict[str, Dict[str, Any]] = {}

def _make_dataset_id(file_path: str) -> str:
    """
    Создает уникальный идентификатор датасета на основе пути, размера и времени модификации файла.
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        16-символьный хеш идентификатор датасета
    """
    try:
        st = os.stat(file_path)
        payload = f"{file_path}:{st.st_size}:{st.st_mtime_ns}".encode("utf-8")
    except Exception:
        payload = f"{file_path}:{time.time()}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]

def _csv_count_rows_fast(file_path: str) -> int:
    """
    Быстрый подсчёт строк в CSV файле без полного декодирования.
    Вычитает заголовок из общего количества строк.
    
    Args:
        file_path: Путь к CSV файлу
        
    Returns:
        Количество строк данных (без заголовка)
    """
    try:
        with open(file_path, "rb") as f:
            total_lines = sum(1 for _ in f)
        return max(total_lines - 1, 0)
    except Exception:
        # Фоллбек: читаем через pandas
        try:
            return int(pd.read_csv(file_path, usecols=[0]).shape[0])
        except Exception:
            return 0

def _csv_get_page(file_path: str, page: int, page_size: int) -> Tuple[pd.DataFrame, List[str]]:
    """
    Возвращает конкретную страницу CSV, не читая весь файл.
    
    Args:
        file_path: Путь к CSV файлу
        page: Номер страницы (начинается с 1)
        page_size: Размер страницы
        
    Returns:
        Кортеж (DataFrame со страницей данных, список имен колонок)
    """
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1000
    # Быстрый путь для больших страниц: используем skiprows + nrows
    start_row = (page - 1) * page_size
    try:
        # читаем только заголовки
        header_cols = pd.read_csv(file_path, nrows=0).columns.tolist()
        if start_row == 0:
            df = pd.read_csv(file_path, nrows=page_size)
        else:
            # skiprows: пропускаем строки [1..start_row] (0 — заголовок)
            df = pd.read_csv(file_path, skiprows=range(1, start_row + 1), nrows=page_size, header=0)
            df.columns = header_cols  # восстанавливаем имена колонок
        return df, header_cols
    except Exception:
        # Фоллбек на итератор chunksize
        chunk_iter = pd.read_csv(file_path, chunksize=page_size, iterator=True)
        chunk = next(islice(chunk_iter, page - 1, page), None)
        if chunk is None:
            return pd.DataFrame(), []
        return chunk, chunk.columns.tolist()


def process_pdf(file: str) -> pd.DataFrame:
    """
    Извлекает таблицу из первой страницы PDF файла.
    
    Args:
        file: Путь к PDF файлу
        
    Returns:
        DataFrame с извлеченными данными или пустой DataFrame если таблица не найдена
    """
    with pdfplumber.open(file) as pdf:
        first_page = pdf.pages[0]
        tables = first_page.extract_tables()
        if tables and len(tables) > 0:
            # Берем первую таблицу и создаем список имен столбцов
            headers = [f"Column_{i}" if cell is None else str(cell) for i, cell in enumerate(tables[0][0])]
            # Создаем DataFrame с данными и именами столбцов
            df = pd.DataFrame(tables[0][1:], columns=pd.Index(headers))
            return df
    return pd.DataFrame()  # Возвращаем пустой DataFrame если таблица не найдена

def process_excel(file: str) -> pd.DataFrame:
    """
    Извлекает данные из Excel файла.
    
    Args:
        file: Путь к Excel файлу
        
    Returns:
        DataFrame с данными из Excel
    """
    return pd.read_excel(file)

def process_csv(file: str, encoding: str = 'utf-8') -> pd.DataFrame:
    """
    Извлекает данные из CSV файла с автоматическим определением кодировки.
    
    Args:
        file: Путь к CSV файлу
        encoding: Кодировка файла (по умолчанию utf-8)
        
    Returns:
        DataFrame с данными из CSV
        
    Raises:
        ValueError: Если не удалось определить кодировку файла
    """
    logger.debug(f"Processing CSV file with encoding: {encoding}")
    try:
        df = pd.read_csv(file, encoding=encoding)
        logger.debug(f"Successfully read CSV. Shape: {df.shape}")
        return df
    except UnicodeDecodeError:
        logger.debug("UTF-8 encoding failed, trying cp1251")
        try:
            df = pd.read_csv(file, encoding='cp1251')
            logger.debug(f"Successfully read CSV with cp1251. Shape: {df.shape}")
            return df
        except:
            logger.error("Failed to read CSV with both encodings")
            raise ValueError("Не удалось определить кодировку файла")

def process_large_csv(file_path: str, file_size: int) -> pd.DataFrame:
    """
    Обрабатывает большой CSV файл с ограничением по размеру.
    Для файлов меньше 10 МБ читает полностью, для больших - только первые 1000 строк.
    
    Args:
        file_path: Путь к CSV файлу
        file_size: Размер файла в байтах
        
    Returns:
        DataFrame с данными
        
    Raises:
        ValueError: Если произошла ошибка при обработке файла
    """
    logger.debug(f"Processing large CSV file: {file_path}, size: {file_size}")
    
    try:
        # Если файл меньше 10 МБ, читаем его полностью
        if file_size < 10 * 1024 * 1024:  # 10 MB
            return process_csv(file_path)
            
        # Для больших файлов читаем только первые 1000 строк
        df = pd.read_csv(file_path, nrows=1000)
        logger.debug(f"Read first 1000 rows. Shape: {df.shape}")
        return df
        
    except Exception as e:
        logger.error(f"Error processing large CSV: {e}")
        raise ValueError(f"Ошибка обработки CSV файла: {str(e)}")

@app.errorhandler(413)
def too_large(e: Exception) -> Response:
    """
    Обработчик ошибки превышения размера файла (413 Request Entity Too Large).
    
    Args:
        e: Исключение от Flask
        
    Returns:
        JSON ответ с ошибкой и статусом 413
    """
    return jsonify({
        'error': 'Файл слишком большой. Максимальный размер: 100 МБ'
    }), 413

@app.route('/api/test', methods=['GET'])
def test_endpoint() -> Response:
    """
    Простой тестовый endpoint для проверки работоспособности сервера.
    
    Returns:
        JSON ответ со статусом сервера
    """
    return jsonify({
        'status': 'ok',
        'message': 'Сервер работает!',
        'timestamp': pd.Timestamp.now().isoformat(),
        'version': '1.0'
    })

@app.route('/api/upload', methods=['POST'])
def upload_file() -> Response:
    """
    Загружает файл (CSV, Excel, PDF) и возвращает первую страницу данных с анализом.
    
    Query параметры:
        page: Номер страницы (по умолчанию 1)
        page_size: Размер страницы (по умолчанию 1000, максимум 5000)
        
    Form data:
        file: Загружаемый файл
        
    Returns:
        FileUploadResponse с данными таблицы, метаданными и базовым анализом
        
    Raises:
        ValidationError: Если файл не предоставлен, неверный формат или ошибка обработки
    """
    temp_file_name = None
    try:
        if 'file' not in request.files:
            raise ValidationError("No file part")
        
        file = request.files['file']
        if file.filename == '':
            raise ValidationError("No selected file")

        # Проверяем расширение файла
        if not file.filename:
            raise ValidationError("No file selected")
            
        file_extension = file.filename.lower()
        if not (file_extension.endswith('.csv') or file_extension.endswith('.xlsx') or file_extension.endswith('.xls') or file_extension.endswith('.pdf')):
            raise ValidationError("Only CSV, Excel, and PDF files are allowed")

        # Получаем параметры пагинации
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 1000, type=int)
        
        # Ограничиваем размер страницы
        page_size = min(page_size, 5000)  # Максимум 5000 строк на страницу

        # Создаём уникальную директорию для каждого загруженного файла
        temp_dir = Path(tempfile.mkdtemp(prefix="vcb03_"))
        filename = secure_filename(file.filename) if file.filename else 'uploaded_file.csv'
        temp_file_name = str(temp_dir / filename)
        file.save(temp_file_name)
        
        # Определяем тип файла и обрабатываем соответственно
        file_extension = file.filename.lower()
        
        dataset_id = _make_dataset_id(temp_file_name)

        incremental_analysis = get_incremental_analysis()
        
        if file_extension.endswith('.csv'):
            # CSV: считаем общее число строк быстро и читаем только нужную страницу
            total_rows = _csv_count_rows_fast(temp_file_name)
            df_page, columns = _csv_get_page(temp_file_name, page, page_size)
            if not columns:
                # попытка прочитать хотя бы заголовок
                try:
                    columns = pd.read_csv(temp_file_name, nrows=0).columns.tolist()
                except Exception:
                    columns = []
            df_for_analysis = df_page  # быстрый анализ по текущей странице
            kind = 'csv'
            cached_df = None  # CSV не кэшируем полностью
        elif file_extension.endswith(('.xlsx', '.xls')):
            # Excel: читаем полностью и кэшируем DataFrame
            df = process_excel(temp_file_name)
            total_rows = len(df)
            df_page = df.iloc[(page - 1) * page_size: (page - 1) * page_size + page_size]
            columns = df.columns.tolist()
            df_for_analysis = df_page  # Анализ только текущей страницы
            kind = 'excel'
            cached_df = df  # Кэшируем полный DataFrame
        elif file_extension.endswith('.pdf'):
            # PDF: читаем полностью и кэшируем DataFrame
            df = process_pdf(temp_file_name)
            total_rows = len(df)
            df_page = df.iloc[(page - 1) * page_size: (page - 1) * page_size + page_size]
            columns = df.columns.tolist()
            df_for_analysis = df_page  # Анализ только текущей страницы
            kind = 'pdf'
            cached_df = df  # Кэшируем полный DataFrame
        else:
            raise ValidationError("Unsupported file format")
            
        if df_page.empty and (file_extension.endswith('.csv') is False) and (total_rows == 0):
            raise ValidationError("Не удалось извлечь данные из файла")
        
        total_pages = (total_rows + page_size - 1) // page_size
        
        logger.debug(f"Total rows: {total_rows}, Total pages: {total_pages}")
        logger.debug(f"Page: {page}, Page size: {page_size}")
        
        # Преобразуем DataFrame в список словарей
        records = df_page.to_dict('records')
        
        # Нормализуем записи (заменяем отсутствующие/NaN значения на дефолты)
        records = [normalize_record(record) for record in records]

        # Используем инкрементальный анализ
        if page == 1:
            # Первая страница - инициализируем анализ
            basic_analysis = incremental_analysis.initialize_analysis(dataset_id, df_page)
        else:
            # Последующие страницы - обновляем анализ инкрементально
            basic_analysis = incremental_analysis.update_analysis(dataset_id, df_page)

        # Сохраняем метаданные датасета для последующих запросов страниц
        _datasets[dataset_id] = {
            'dir': temp_dir,
            'path': temp_file_name,
            'kind': kind,
            'columns': columns,
            'total_rows': total_rows,
            'created_at': time.time(),
            'cached_df': cached_df,  # Кэшированный DataFrame для Excel/PDF
        }

        # Формируем ответ
        response = {
            'table_data': records,
            'columns': columns,
            'total_rows': total_rows,
            'current_page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'basic_analysis': basic_analysis,
            'dataset_id': dataset_id
        }

        logger.debug(f"Sending response with {len(records)} records")
        logger.debug(f"Response keys: {list(response.keys())}")
        
        return jsonify(response)

    except ValidationError as e:
        raise e
    except Exception as e:
        logger.exception("Error processing file")
        # централизованный обработчик вернет 500 без детали
        raise
        
    finally:
        # Не удаляем файл сразу: он нужен для последующих страниц.
        # Файл будет удалён при завершении процесса или вручную.
        pass

@app.route('/api/analyze', methods=['POST'])
def analyze() -> Response:
    """
    Выполняет LLM анализ данных таблицы с кэшированием результатов.
    
    Request body (JSON):
        provider: Провайдер LLM ('openai', 'yandex', 'giga')
        model: Название модели
        table_data: Массив записей таблицы
        
    Returns:
        LLMAnalysisResponse с результатом анализа
        
    Raises:
        ValidationError: Если отсутствуют обязательные поля или ошибка анализа
    """
    try:
        data = request.get_json()
        if not data or 'provider' not in data or 'model' not in data or 'table_data' not in data:
            raise ValidationError("Missing required fields")
        
        provider = data['provider']
        model = data['model']
        table_data = data['table_data']
        
        logger.debug(f"Received analysis request - Provider: {provider}, Model: {model}")
        
        # Преобразуем данные в строковый формат
        df = pd.DataFrame(table_data)
        table_string = df.to_string(index=False, max_rows=100)
        
        # Кэширование по (provider, model, dataset_hash)
        cache_key = _analysis_cache.make_key(provider, model, table_string)
        cached = _analysis_cache.get(cache_key)
        
        if cached is not None:
            analysis = cached
            logger.debug("Analysis cache hit")
        else:
            # Получаем анализ от выбранной LLM
            analysis = get_analysis(provider, model, table_string)
            _analysis_cache.put(cache_key, analysis)
            logger.debug("Analysis cache miss; computed and cached")
        
        logger.debug(f"Analysis completed for {provider}:{model}")
        
        # Возвращаем ответ в формате, ожидаемом фронтендом
        return jsonify({
            'model': f"{provider}:{model}",
            'analysis': analysis,
            'timestamp': pd.Timestamp.now().isoformat()
        })

    except ValidationError as e:
        raise e
    except Exception as e:
        logger.exception("Error during analysis")
        raise

@app.route('/api/report', methods=['POST'])
def generate_report() -> Response:
    """
    Генерирует PDF отчет из HTML с санитизацией и ограничением размера.
    
    Request body (JSON):
        report_html: HTML содержимое отчета (максимум 200KB)
        
    Returns:
        PDF файл как attachment или JSON с ошибкой
        
    Raises:
        ValidationError: Если HTML отсутствует или слишком большой
    """
    try:
        data = request.get_json()
        if not data or 'report_html' not in data:
            raise ValidationError("Missing report HTML")

        raw_html: str = data['report_html']

        # Проверяем размер
        if isinstance(raw_html, str) and len(raw_html.encode('utf-8')) > MAX_REPORT_HTML_BYTES:
            raise ValidationError("Report HTML is too large")

        # Санитайз HTML
        safe_html = _html_cleaner.clean(raw_html)

        # Создаем PDF из очищенного HTML, без доступа к внешним ресурсам
        html = HTML(string=safe_html, base_url=None, url_fetcher=_block_external_url_fetcher)
        pdf = html.write_pdf()

        # Отправляем PDF
        if pdf:
            return send_file(
                BytesIO(pdf),
                mimetype='application/pdf',
                as_attachment=True,
                download_name='analysis-report.pdf'
            )
        else:
            return jsonify({'error': 'Failed to generate PDF'}), 500

    except ValidationError as e:
        raise e
    except Exception as e:
        logger.exception("Error generating report")
        raise

@app.route('/api/fill-missing-ai', methods=['POST'])
def fill_missing_ai() -> Response:
    """
    Оптимизированная версия fill-missing-ai с использованием groupby вместо квадратичных операций.
    Сложность: O(N log N) вместо O(N²).
    
    Request body (JSON):
        table_data: Массив записей таблицы
        columns: Список имен колонок
        missing_info: Словарь {column_name: [row_indices]} с информацией о пропусках
        
    Returns:
        FillMissingResponse с рекомендациями по заполнению пропусков
        
    Raises:
        ValidationError: Если отсутствуют обязательные поля или ошибка обработки
    """
    try:
        data = request.get_json()
        if not data or 'table_data' not in data or 'columns' not in data or 'missing_info' not in data:
            raise ValidationError("Missing required fields")
        table_data = data['table_data']
        columns = data['columns']
        missing_info = data['missing_info']
        df = pd.DataFrame(table_data)
        recommendations = {}
        
        for col in missing_info:
            recs = []
            # Находим строки с пропущенными значениями
            missing_mask = df[col].isna() | (df[col] == '')
            missing_rows = df[missing_mask].copy()
            
            if missing_rows.empty:
                recommendations[col] = []
                continue
            
            # Группируем по всем остальным колонкам (кроме текущей)
            group_keys = [c for c in columns if c != col]
            
            # Вычисляем самое частое значение для каждой группы
            # Используем только строки с заполненными значениями в текущей колонке
            filled_df = df[~missing_mask]
            
            if not filled_df.empty and group_keys:
                # Группируем заполненные строки и находим mode для каждой группы
                grouped = filled_df.groupby(group_keys)[col].agg(
                    lambda s: s.mode().iloc[0] if not s.mode().empty else None
                ).to_dict()
                
                # Глобальное самое частое значение (fallback)
                global_mode = df[col].mode().iloc[0] if not df[col].mode().empty else None
                
                # Обрабатываем каждую строку с пропуском
                for idx, row in missing_rows.iterrows():
                    # Формируем ключ группы из значений других колонок
                    group_key = tuple(row[k] for k in group_keys if pd.notna(row[k]) and row[k] != '')
                    
                    # Пробуем найти значение по группе
                    suggested = None
                    confidence = 0.5
                    matched_fields = []
                    
                    if group_key and group_key in grouped:
                        suggested = grouped[group_key]
                        confidence = 1.0
                        matched_fields = [k for k in group_keys if pd.notna(row[k]) and row[k] != '']
                    
                    # Fallback на глобальное mode
                    if suggested is None:
                        suggested = global_mode
                        confidence = 0.5
                    
                    explanation = (
                        f"В похожих строках с такими же {', '.join(f'{c}={row[c]}' for c in matched_fields)} чаще всего встречается '{suggested}'."
                        if matched_fields and suggested
                        else ("Нет похожих строк, поэтому выбрано самое частое значение по всей колонке." if suggested is not None else "Нет данных для подсказки.")
                    )
                    
                    recs.append({
                        'row_idx': int(idx),
                        'suggested': suggested,
                        'confidence': confidence,
                        'explanation': explanation
                    })
            else:
                # Если нет заполненных строк или нет группирующих колонок - используем глобальный mode
                global_mode = df[col].mode().iloc[0] if not df[col].mode().empty else None
                for idx, row in missing_rows.iterrows():
                    recs.append({
                        'row_idx': int(idx),
                        'suggested': global_mode,
                        'confidence': 0.5,
                        'explanation': "Нет похожих строк, поэтому выбрано самое частое значение по всей колонке." if global_mode is not None else "Нет данных для подсказки."
                    })
            
            recommendations[col] = recs
        
        return jsonify({'recommendations': recommendations})
    except ValidationError as e:
        raise e
    except Exception as e:
        logger.exception('Error in fill-missing-ai')
        raise

@app.route('/api/upload/page', methods=['POST'])
def get_upload_page() -> Response:
    """
    Возвращает страницу данных по dataset_id без повторной загрузки файла.
    
    Request body (JSON):
        dataset_id: Идентификатор датасета из предыдущего запроса upload
        page: Номер страницы (по умолчанию 1)
        page_size: Размер страницы (по умолчанию 1000)
        
    Returns:
        UploadPageResponse с данными страницы
        
    Raises:
        ValidationError: Если dataset_id неверный или отсутствует, или ошибка обработки
    """
    try:
        data = request.get_json() or {}
        dataset_id = data.get('dataset_id')
        page = int(data.get('page', 1))
        page_size = int(data.get('page_size', 1000))
        if not dataset_id or dataset_id not in _datasets:
            raise ValidationError("Invalid or missing dataset_id")
        meta = _datasets[dataset_id]
        file_path = meta['path']
        kind = meta['kind']
        columns = meta['columns']
        total_rows = int(meta['total_rows'])
        total_pages = (total_rows + page_size - 1) // page_size if total_rows > 0 else 1
        cached_df = meta.get('cached_df')  # Кэшированный DataFrame для Excel/PDF

        incremental_analysis = get_incremental_analysis()

        if kind == 'csv':
            # CSV: читаем страницу напрямую из файла
            df_page, _ = _csv_get_page(file_path, page, page_size)
            if not columns:
                columns = df_page.columns.tolist()
        elif kind == 'excel':
            # Excel: используем кэшированный DataFrame если есть, иначе читаем заново
            if cached_df is not None:
                df = cached_df
            else:
                df = process_excel(file_path)
                meta['cached_df'] = df  # Кэшируем для следующих запросов
            start_idx = (page - 1) * page_size
            df_page = df.iloc[start_idx:start_idx + page_size]
        elif kind == 'pdf':
            # PDF: используем кэшированный DataFrame если есть, иначе читаем заново
            if cached_df is not None:
                df = cached_df
            else:
                df = process_pdf(file_path)
                meta['cached_df'] = df  # Кэшируем для следующих запросов
            start_idx = (page - 1) * page_size
            df_page = df.iloc[start_idx:start_idx + page_size]
        else:
            raise ValidationError("Unsupported dataset kind")

        records = df_page.to_dict('records')

        # Нормализуем записи (используем общую функцию)
        records = [normalize_record(record) for record in records]

        # Обновляем инкрементальный анализ
        basic_analysis = incremental_analysis.update_analysis(dataset_id, df_page)

        return jsonify({
            'table_data': records,
            'columns': columns,
            'total_rows': total_rows,
            'current_page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'dataset_id': dataset_id,
            'basic_analysis': basic_analysis  # Возвращаем обновленный анализ
        })
    except ValidationError as e:
        raise e
    except Exception:
        logger.exception("Error in /api/upload/page")
        raise

def _cleanup_old_datasets() -> None:
    """
    Удаляет старые датасеты из _datasets и их директории.
    Использует TEMP_CLEANUP_AGE_MIN из конфигурации для определения возраста.
    Также очищает инкрементальный анализ для удаляемых датасетов.
    """
    now = time.time()
    age_sec = Config.TEMP_CLEANUP_AGE_MIN * 60
    to_remove = []
    incremental_analysis = get_incremental_analysis()
    
    for dataset_id, meta in _datasets.items():
        if now - meta.get('created_at', 0) > age_sec:
            to_remove.append(dataset_id)
            # Удаляем директорию
            temp_dir = meta.get('dir')
            if temp_dir and Path(temp_dir).exists():
                try:
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception as e:
                    logger.warning(f"Failed to remove temp dir {temp_dir}: {e}")
            # Очищаем инкрементальный анализ
            incremental_analysis.clear_analysis(dataset_id)
    
    for dataset_id in to_remove:
        _datasets.pop(dataset_id, None)

@app.before_request
def _cleanup_before_request() -> None:
    """
    Периодическая очистка старых датасетов.
    Выполняется примерно каждые 5 минут (проверяет каждый 100-й запрос).
    """
    # Очищаем каждые 5 минут (проверяем каждый 100-й запрос примерно)
    if len(_datasets) > 0 and time.time() % 300 < 1:
        _cleanup_old_datasets()

if __name__ == '__main__':
    # Логируем информацию о запуске
    logger.info("Starting VCb03 Backend API", extra={
        'extra_fields': {
            'test_mode': Config.TEST_MODE,
            'log_level': Config.LOG_LEVEL,
            'json_logging': Config.LOG_JSON_FORMAT,
            'api_key_set': bool(Config.API_KEY)
        }
    })
    app.run(host='0.0.0.0', port=5000, debug=Config.get_debug_flag())
