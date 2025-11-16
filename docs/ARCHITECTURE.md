# Архитектура

## Обзор
- Backend: Python (Flask), модули `backend/llm/*` для интеграции с LLM (OpenAI, YandexGPT, GigaChat)
- Frontend: React + TypeScript (CRA), UI для загрузки, анализа и визуализации данных

## Backend
- `backend/pdf_server.py` — основной сервер и API маршруты
- `backend/llm/main_processor.py` — маршрутизация к провайдерам LLM
- `backend/llm/*_helper.py` — конкретные провайдеры
- Логи: DEBUG; валидация входных данных; устойчивость к NaN/кодировкам

## Frontend
- `frontend/src/App.tsx` — основной поток: загрузка → обработка пропусков → анализ → графики
- `components/*` — диалоги, таблица, визуализация, выбор модели
- `api/index.ts` — HTTP-клиент с валидацией

## Данные/UX
- Пагинация, фильтры, авто-диаграммы, экспорт PDF
- Заполнение пропусков: вручную и с ИИ-подсказками


