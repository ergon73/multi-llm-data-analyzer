# API

Базовый URL: `http://localhost:5000/api`

## GET /api/test
- Проверка работоспособности сервера
- Ответ: `{ status, message, timestamp, version }`

## POST /api/upload
- Загрузка файла (CSV, Excel, PDF) с пагинацией
- Form-data: `file`
- Query: `page` (int, default 1), `page_size` (int, default 1000, max 5000)
- Ответ: `{ table_data, columns, total_rows, current_page, page_size, total_pages, basic_analysis }`

## POST /api/analyze
- Анализ данных с выбором LLM
- Body (JSON):
```json
{
  "provider": "openai" | "yandex" | "giga",
  "model": "gpt-4.1 | yandexgpt | GigaChat:latest | ...",
  "table_data": [ { "...": "..." } ]
}
```
- Ответ: `{ model, analysis, timestamp }`

## POST /api/report
- Генерация PDF отчёта на основе HTML
- Body (JSON): `{ "report_html": "<html>..." }`
- Ответ: PDF-файл

## POST /api/fill-missing-ai
- ИИ-подсказки для заполнения пропусков на основе похожих строк
- Body (JSON): `{ table_data, columns, missing_info }`
- Ответ: `{ recommendations: { [col]: [{ row_idx, suggested, confidence, explanation }] } }`


