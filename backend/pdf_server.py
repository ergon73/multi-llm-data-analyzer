from flask import Flask, request, send_file, jsonify
from weasyprint import HTML, CSS
from io import BytesIO
import pandas as pd
import pdfplumber
import tempfile
import os
import json
from typing import List, Optional
from dotenv import load_dotenv
from flask_cors import CORS
import logging
from werkzeug.utils import secure_filename

# Настраиваем логирование
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения как можно раньше, до импорта LLM
load_dotenv()

# Импортируем LLM-обработчик после загрузки .env, чтобы учитывался TEST_MODE и ключи
from llm.main_processor import get_analysis

app = Flask(__name__)

# Настраиваем максимальный размер файла (100 МБ)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

# Настраиваем CORS более специфично
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

def perform_basic_analysis(df: pd.DataFrame) -> dict:
    """Выполняет базовый анализ данных DataFrame."""
    logger.debug(f"Starting basic analysis. DataFrame shape: {df.shape}")
    logger.debug(f"DataFrame columns: {df.columns.tolist()}")
    
    analysis = {
        'numeric_columns': {},
        'string_columns': {}
    }
    
    for column in df.columns:
        logger.debug(f"Analyzing column: {column}")
        if pd.api.types.is_numeric_dtype(df[column]):
            logger.debug(f"Column {column} is numeric")
            # Обрабатываем NaN значения для числовых колонок
            column_data = df[column].dropna()
            if len(column_data) > 0:
                analysis['numeric_columns'][column] = {
                    'sum': float(column_data.sum()),
                    'mean': float(column_data.mean()),
                    'min': float(column_data.min()),
                    'max': float(column_data.max())
                }
            else:
                analysis['numeric_columns'][column] = {
                    'sum': 0.0,
                    'mean': 0.0,
                    'min': 0.0,
                    'max': 0.0
                }
            logger.debug(f"Numeric analysis for {column}: {analysis['numeric_columns'][column]}")
        else:
            logger.debug(f"Column {column} is string")
            # Обрабатываем NaN значения для строковых колонок
            unique_values = df[column].dropna().unique().tolist()[:10]
            analysis['string_columns'][column] = {
                'unique_values_count': int(df[column].nunique()),
                'unique_values': unique_values
            }
            logger.debug(f"String analysis for {column}: {analysis['string_columns'][column]}")
    
    return analysis

def process_pdf(file: str) -> pd.DataFrame:
    """Извлекает таблицу из первой страницы PDF файла."""
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
    """Извлекает данные из Excel файла."""
    return pd.read_excel(file)

def process_csv(file: str, encoding: str = 'utf-8') -> pd.DataFrame:
    """Извлекает данные из CSV файла."""
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
    """Обрабатывает большой CSV файл с ограничением по размеру."""
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
def too_large(e):
    """Обработчик ошибки превышения размера файла"""
    return jsonify({
        'error': 'Файл слишком большой. Максимальный размер: 100 МБ'
    }), 413

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Простой тестовый endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'Сервер работает!',
        'timestamp': pd.Timestamp.now().isoformat(),
        'version': '1.0'
    })

@app.route('/api/upload', methods=['POST'])
def upload_file():
    temp_file_name = None
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        # Проверяем расширение файла
        if not file.filename:
            return jsonify({'error': 'No file selected'}), 400
            
        file_extension = file.filename.lower()
        if not (file_extension.endswith('.csv') or file_extension.endswith('.xlsx') or file_extension.endswith('.xls') or file_extension.endswith('.pdf')):
            return jsonify({'error': 'Only CSV, Excel, and PDF files are allowed'}), 400

        # Получаем параметры пагинации
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 1000, type=int)
        
        # Ограничиваем размер страницы
        page_size = min(page_size, 5000)  # Максимум 5000 строк на страницу

        # Сохраняем файл во временную директорию
        filename = secure_filename(file.filename) if file.filename else 'uploaded_file.csv'
        temp_file_name = os.path.join(tempfile.gettempdir(), filename)
        file.save(temp_file_name)
        
        # Определяем тип файла и обрабатываем соответственно
        file_extension = file.filename.lower()
        
        if file_extension.endswith('.csv'):
            df = process_csv(temp_file_name)
        elif file_extension.endswith(('.xlsx', '.xls')):
            df = process_excel(temp_file_name)
        elif file_extension.endswith('.pdf'):
            df = process_pdf(temp_file_name)
        else:
            return jsonify({'error': 'Unsupported file format'}), 400
            
        if df.empty:
            return jsonify({'error': 'Не удалось извлечь данные из файла'}), 400
        
        # Вычисляем общее количество строк
        total_rows = len(df)
        total_pages = (total_rows + page_size - 1) // page_size
        
        logger.debug(f"Total rows: {total_rows}, Total pages: {total_pages}")
        logger.debug(f"Page: {page}, Page size: {page_size}")
        
        # Применяем пагинацию
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        df_page = df.iloc[start_idx:end_idx]
        
        # Преобразуем DataFrame в список словарей
        records = df_page.to_dict('records')
        
        # Проверяем целостность данных и заменяем NaN на null
        required_fields = ['year', 'make', 'model', 'trim', 'body', 'transmission', 'vin', 'state', 'condition', 'odometer', 'color', 'interior', 'seller', 'mmr', 'sellingprice', 'saledate']
        
        for record in records:
            for field in required_fields:
                if field not in record or pd.isna(record[field]):
                    if field == 'condition':
                        record[field] = 0.0
                    elif field in ['year', 'odometer', 'mmr', 'sellingprice']:
                        record[field] = 0
                    else:
                        record[field] = None
                elif pd.isna(record[field]):
                    # Заменяем NaN на null для JSON совместимости
                    if field == 'condition':
                        record[field] = 0.0
                    elif field in ['year', 'odometer', 'mmr', 'sellingprice']:
                        record[field] = 0
                    else:
                        record[field] = None

        # Выполняем базовый анализ для всех данных
        basic_analysis = perform_basic_analysis(df)

        # Формируем ответ
        response = {
            'table_data': records,
            'columns': df.columns.tolist(),
            'total_rows': total_rows,
            'current_page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'basic_analysis': basic_analysis
        }

        logger.debug(f"Sending response with {len(records)} records")
        logger.debug(f"Response keys: {list(response.keys())}")
        
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return jsonify({'error': str(e)}), 500
        
    finally:
        if temp_file_name and os.path.exists(temp_file_name):
            try:
                os.remove(temp_file_name)
            except Exception as e:
                logger.error(f"Error removing temp file: {str(e)}")

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        if not data or 'provider' not in data or 'model' not in data or 'table_data' not in data:
            return jsonify({'error': 'Missing required fields'}), 400
        
        provider = data['provider']
        model = data['model']
        table_data = data['table_data']
        
        logger.debug(f"Received analysis request - Provider: {provider}, Model: {model}")
        
        # Преобразуем данные в строковый формат
        df = pd.DataFrame(table_data)
        table_string = df.to_string(index=False, max_rows=100)
        
        # Получаем анализ от выбранной LLM
        analysis = get_analysis(provider, model, table_string)
        
        logger.debug(f"Analysis completed for {provider}:{model}")
        
        # Возвращаем ответ в формате, ожидаемом фронтендом
        return jsonify({
            'model': f"{provider}:{model}",
            'analysis': analysis,
            'timestamp': pd.Timestamp.now().isoformat()
        })

    except Exception as e:
        logger.exception("Error during analysis")
        return jsonify({'error': str(e)}), 500

@app.route('/api/report', methods=['POST'])
def generate_report():
    try:
        data = request.get_json()
        if not data or 'report_html' not in data:
            return jsonify({'error': 'Missing report HTML'}), 400

        # Создаем PDF из HTML
        html = HTML(string=data['report_html'])
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

    except Exception as e:
        logger.exception("Error generating report")
        return jsonify({'error': str(e)}), 500

@app.route('/api/fill-missing-ai', methods=['POST'])
def fill_missing_ai():
    try:
        data = request.get_json()
        if not data or 'table_data' not in data or 'columns' not in data or 'missing_info' not in data:
            return jsonify({'error': 'Missing required fields'}), 400
        table_data = data['table_data']
        columns = data['columns']
        missing_info = data['missing_info']
        df = pd.DataFrame(table_data)
        recommendations = {}
        for col in missing_info:
            recs = []
            for idx, row in df[df[col].isna() | (df[col] == '')].iterrows():
                mask = pd.Series([True] * len(df))
                matched_fields = []
                for c in columns:
                    if c != col and pd.notna(row[c]) and row[c] != '':
                        mask = mask & (df[c] == row[c])
                        matched_fields.append(c)
                candidates = df[mask & df[col].notna() & (df[col] != '')]
                if not candidates.empty:
                    value = candidates[col].mode().iloc[0]
                    explanation = f"В похожих строках с такими же {', '.join(f'{c}={row[c]}' for c in matched_fields)} чаще всего встречается '{value}'."
                    recs.append({'row_idx': int(idx), 'suggested': value, 'confidence': 1.0, 'explanation': explanation})
                else:
                    value = df[col].mode().iloc[0] if not df[col].mode().empty else None
                    explanation = "Нет похожих строк, поэтому выбрано самое частое значение по всей колонке." if value is not None else "Нет данных для подсказки."
                    recs.append({'row_idx': int(idx), 'suggested': value, 'confidence': 0.5, 'explanation': explanation})
            recommendations[col] = recs
        return jsonify({'recommendations': recommendations})
    except Exception as e:
        logger.exception('Error in fill-missing-ai')
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
