### Refactoring Plan v2

Цель: закрыть дефекты, обнаруженные при проверке `refactoring.md`, и вывести проект на состояние, пригодное для сборки, тестирования и безопасного деплоя.

---

#### 1. Config & Secrets Hygiene (CRITICAL)
- **Задачи**
  1. Ввести `backend/config.py` с классом `Config`: чтение переменных окружения, дефолты, `validate()` с обязательными ключами (LLM API, security options, rate-limit).  
  2. Все импорты (`pdf_server`, `llm/*`) переводим на `from backend.config import Config`. Убираем прямые `load_dotenv` и обращения к `os.getenv`.  
  3. Обновляем `.env.example`, удаляем реальные ключи из `.env` / `backend/.env`, документируем процесс в README (как скопировать `.env.example`).  
  4. Добавляем sanity-check команду в Make/README: `python -c "from backend.config import Config; Config.validate()"`.
- **Верификация**: `pytest tests/config` (новые тесты на валидацию) + ручной запуск `Config.validate()`.

#### 2. Backend: CSV Streaming & Dataset Delta (HIGH)
- **Chunked CSV**
  - Переписать `_csv_get_page`: использовать `pd.read_csv(..., skiprows=start_row, nrows=page_size)` только при необходимости, иначе читать через iterator + `islice` (не ловим исключение, а выбираем стратегию по размеру).
  - Добавить benchmark/pytest (`tests/test_upload_pagination.py`) на файлы 50k+ строк (можно синтетический CSV).
- **Dataset registry**
  - `upload_file`: сохранять файл в уникальную директорию (`tempfile.mkdtemp(prefix="vcb03_")`), хранить путь к каталогу/файлу в `_datasets`.  
  - Добавить фоновой clean-up (например, cron-like при `before_request` → удаляем записи старше N минут).
- **LLM delta flow**
  - `/api/analyze` принимает `dataset_id`, `page_cursor`, `table_data_delta`. При наличии dataset_id сервер сам читает нужный кусок (через `_datasets`).  
  - Кэш-ключ строим из `dataset_id + provider + model`.  
  - На фронте `handleLoadMore` отправляет только дельту и datasetId.
- **Верификация**: интеграционные тесты `tests/test_analyze_delta.py`, `tests/test_large_csv_stream.py`.

#### 3. Frontend Stability (HIGH)
- **AnalysisResult rebuild**
  - Разделить состояние `autoCharts`: оставить `const [autoCharts, setAutoCharts]` и переименовать значение из hook (`const generatedCharts = useAutoCharts(...)`), либо избавиться от локального стейта — цель: устранить двойное объявление.  
  - Прогнать `npm run build` (должен отработать).
- **Virtualized table**
  - Перейти на `TableBody` с `component={List}` (MUI pattern) или собственный контейнер: `<Table component={Paper}>` + `<Box>` внутри для `react-window`. Важно не вставлять `<div>` напрямую в `<tbody>`.  
  - Покрыть snapshot/RTL тестом (`VirtualizedTable.test.tsx`) проверяющим структуру.
- **Logging**
  - Завести флаг `REACT_APP_DEBUG`, завраппить `console.log`/`console.debug`. При PROD сборке флаг выключен.
- **Верификация**: `npm run lint`, `npm run test -- --runInBand`, `npm run build`.

#### 4. Report & PDF Security (MEDIUM)
- **HTML sanitization** уже есть, но нужно:
  - Добавить allowlist CSS (убрать inline `background:url` и др.).  
  - Написать тест `test_report_sanitize_blocks_styles` (проверяет, что `style` с внешними URL режется).  
  - Опционально добавить конфиг `ALLOW_REPORT_INLINE_STYLE` для dev.
- **Верификация**: `pytest tests/test_report_sanitize.py`.

#### 5. Temp File Safety (MEDIUM)
- В каждом upload создаём уникальную директорию (`tmpdir = Path(tempfile.mkdtemp())`; `file_path = tmpdir / secure_filename`).  
- `_datasets[dataset_id]` хранит `{"dir": tmpdir, "file": file_path, "created_at": time.time()}`.  
- При выдаче следующей страницы проверяем, что файл существует, иначе возвращаем `410 Gone`.  
- Фоновый cleanup (см. пункт 2) удаляет каталог и запись.
- **Верификация**: интеграционный тест, имитирующий два одновременных аплоада с одинаковыми именами.

#### 6. Testing Infrastructure (MEDIUM)
- Добавить `pytest` и плагины в `backend/requirements.txt`; создать `requirements-dev.txt`.  
- CI: GitHub Actions workflow → `pip install -r requirements.txt -r requirements-dev.txt`, `pytest`, `npm ci`, `npm run test`, `npm run build`.  
- Для WeasyPrint/pd зависимостей описать в README требуемые system packages.

#### 7. Documentation & Developer UX (LOW)
- README обновить разделами: настройки env, запуск тестов, работа с большими CSV, политика temp cleanup.  
- Добавить `docs/architecture.md` с описанием dataset cache/delta pipeline и новых API контрактов.  
- Обновить `refactoring.md` (или завести changelog) после реализации.

---

##### Риски и контрольные точки
- **Большие CSV**: измерить память/время до и после (добавить раздел “Performance Benchmarks”).  
- **LLM квоты**: убедиться, что кэш очищается (TTL + max size).  
- **PDF**: только whitelisted стили → коммуникация с UX, чтобы не сломать верстку.

##### Общая последовательность
1. Config + Secrets → чтобы разработка встала на единый конфиг.  
2. Backend streaming + temp dirs → влияет на API.  
3. Frontend адаптация под новые API + фиксы сборки.  
4. Тесты/CI → фиксируем регрессии.  
5. Документация и cleanup.

Каждый этап завершается прогоном pytest + npm build и апдейтом отчета в `refactoring-report.md`.
