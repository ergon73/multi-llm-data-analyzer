### 1. EXECUTIVE SUMMARY

#### Оценка проекта: 4/10  
**Уровень технического долга:** Критический

#### 🔥 Топ-3 критичных (исправить НЕМЕДЛЕННО)
1. Хардкод секретов в `.env`, backend/*.py и репозитории — Риск: ВЫСОКИЙ, Время: ~0.5ч, Выигрыш: защита аккаунтов OpenAI/Yandex/GigaChat и возможность развёртывать код публично.
2. `/api/report` принимает произвольный HTML и сразу печатает PDF — Риск: ВЫСОКИЙ, Время: ~1ч, Выигрыш: защита от SSRF/XSS и изоляция PDF-пайплайна.
3. `gigachat_helper` бросает `ValueError` при импортe без переменной `GIGACHAT_CREDENTIALS` — Риск: СРЕДНИЙ, Время: ~0.5ч, Выигрыш: сервер перестаёт падать и можно запускать без российских ключей.

#### 💰 Quick Wins (за <1 час каждая)
- [ ] Удалить реальные ключи из `.env` и переписать `.gitignore` (~20 мин) → выигрыш: безопасность + репозиторий снова можно шарить.
- [ ] Выключить `debug=True` перед production и добавить переменную `FLASK_DEBUG` (~15 мин) → выигрыш: нет удалённого дебаггера.
- [ ] Заменить `console.log` чувствительных данных в `frontend/src/api/index.ts` на `debug` флаг (~30 мин) → выигрыш: нет утечки данных в логах браузера.

---

### 2. ROADMAP

#### 🔴 Неделя 1: CRITICAL (безопасность + стабильность)
**Цель:** закрыть уязвимости, чтобы код можно было запускать на сервере.

- [ ] Перенести секреты в .env.example + Config (CRITICAL-1) (~0.5ч)  
- [ ] Санитайз HTML перед WeasyPrint и добавить allowlist (CRITICAL-2) (~1ч)  
- [ ] Исправить аварийный импорт GigaChat + добавить graceful fallback (CRITICAL-3) (~0.5ч)  
- [ ] Включить централизованные обработчики ошибок, убрать `debug=True`, добавить healthcheck (CRITICAL-4) (~1.5ч)  

**Результат:** безопасный сервер, который запускается без всех ключей, отдаёт понятные ошибки и не выполняет произвольный HTML.  
**Время:** ~3.5–4 часа.

#### 🟡 Недели 2-3: HIGH (производительность + архитектура)
**Цель:** уменьшить нагрузку на LLM и RAM, упростить React-компоненты.

- [ ] Потоковая обработка CSV (chunked чтение и реальное использование `process_large_csv`) (~3ч)  
- [ ] Кэширование результатов LLM по `dataset_hash+model` и debounce load-more запросов (~2ч)  
- [ ] Разделение `frontend/src/App.tsx` и `components/AnalysisResult.tsx` на контейнер + представление + сервисы (~6ч)  
- [ ] Вынести API baseURL в `.env` + axios instance, убрать `fetch('http://localhost:5000')` дубли (HIGH-4) (~2ч)  
- [ ] Добавить rate limiting / auth placeholder (например, simple API key) (~2ч)  

**Результат:** меньше повторных обращений к LLM, UI не подвисает, код делится на слои.  
**Время:** ~15 часов.

#### 🟢 Недели 4-6: MEDIUM (качество кода + тесты)
**Цель:** обеспечить возможность дальнейших изменений без страха.

- [ ] Type hints для backend, mypy в CI (~4ч)  
- [ ] Покрыть Flask API unit/integration тестами (pytest + Flask client) и React компонентов (RTL) (~16ч)  
- [ ] Включить TS strict + заменить `any` на конкретные интерфейсы (~4ч)  
- [ ] Очистить логи, вынести магические числа (page_size, required_fields) в константы (~2ч)  
- [ ] Настроить eslint/prettier + black/flake8 + pre-commit (~4ч)  

**Результат:** >60% покрытия тестами, строгая типизация, чистые логи.  
**Время:** ~30 часов.

#### 🟤 Месяц 2+: LOW (полировка + DevOps)
**Цель:** подготовить к production.

- [ ] Обновить документацию (`frontend/README.md`, `docs/*`, добавить диаграммы) (~2ч)  
- [ ] Docker Compose (Flask + React + reverse proxy) (~3ч)  
- [ ] Логирование и мониторинг (структурированные JSON-логи, Sentry или аналог) (~2ч)  
- [ ] Обновить зависимости (npm audit/pip-audit) и настроить renovate (~1ч)  

**Результат:** reproducible окружение и актуальные зависимости.  
**Время:** ~8 часов.

**Итого:** ~57 часов ≈ 7-8 рабочих дней.

---

### 3. ВХОДНЫЕ ДАННЫЕ (JSON из аудита)

```json
{
  "project_info": {
    "name": "Multi-LLM Analyzer",
    "type": "Full-stack web app",
    "status": "partially working",
    "purpose": "Загрузка табличных данных, очистка пропусков и получение AI‑аналитики/PDF от OpenAI, YandexGPT и GigaChat",
    "structure": "project/ -> backend/pdf_server.py (Flask API), backend/llm/* helpers, frontend/src/App.tsx + components (React), docs/*, sample CSV/XLSX, .env с ключами"
  },
  "tech_stack": {
    "backend": {
      "language": "Python 3.x",
      "framework": "Flask 2.x",
      "database": "None",
      "orm": "None",
      "async": "sync only",
      "data_processing": ["pandas", "pdfplumber", "WeasyPrint"],
      "file_storage": "temp files on disk",
      "auth": "None"
    },
    "frontend": {
      "language": "TypeScript 4.9",
      "framework": "React 18 (CRA/Webpack)",
      "state": "React useState/useEffect",
      "bundler": "react-scripts 5",
      "ui": "MUI 5",
      "visualization": "Recharts"
    },
    "integrations": ["OpenAI", "YandexGPT", "GigaChat", "WeasyPrint"]
  },
  "metrics": {
    "size": {
      "total_files": 30,
      "python_lines": 596,
      "js_lines": 2434,
      "largest_files": [
        {"file": "frontend/src/components/AnalysisResult.tsx", "lines": 1110},
        {"file": "frontend/src/App.tsx", "lines": 477},
        {"file": "backend/pdf_server.py", "lines": 329},
        {"file": "README.md", "lines": 233},
        {"file": "frontend/src/api/index.ts", "lines": 144}
      ]
    },
    "quality": {
      "overall_score": 4,
      "readability": 4,
      "structure": 3,
      "documentation": 3,
      "tests": 1,
      "security": 2,
      "performance": 4,
      "test_coverage": 0,
      "type_coverage_backend": 40,
      "type_coverage_frontend": 60,
      "lint_warnings": null,
      "security_issues": 3
    },
    "complexity": {
      "avg_function_lines": 33,
      "avg_cyclomatic_complexity": 9,
      "duplicated_code_percent": 20
    },
    "dependencies": {
      "backend_packages": 13,
      "frontend_packages": 21,
      "outdated_packages": 10,
      "vulnerable_packages": null
    }
  },
  "critical_issues": [
    {
      "id": "SEC-1",
      "type": "security",
      "severity": "critical",
      "category": "Hardcoded secrets",
      "file": ".env:2-12",
      "description": "YANDEX/OpenAI/GigaChat ключи лежат в репозитории и совпадают в backend/.env",
      "code": "OPENAI_API_KEY=sk-proj-Try...; YANDEX_API_KEY=AQVN1OxX...",
      "risk": "HIGH — компрометация аккаунтов и платных квот",
      "estimated_fix_time": "30m"
    },
    {
      "id": "SEC-2",
      "type": "security",
      "severity": "critical",
      "category": "Unsanitized HTML",
      "file": "backend/pdf_server.py:296-315",
      "description": "report_html клиента вставляется в WeasyPrint без фильтрации",
      "risk": "HIGH — SSRF/XSS через PDF генератор",
      "estimated_fix_time": "1h"
    },
    {
      "id": "BUG-1",
      "type": "bug",
      "severity": "critical",
      "category": "Startup failure",
      "file": "backend/llm/gigachat_helper.py:8-23",
      "description": "Модуль бросает ValueError при отсутствии GIGACHAT_CREDENTIALS",
      "risk": "HIGH — backend не запускается вне TEST_MODE",
      "estimated_fix_time": "45m"
    }
  ],
  "high_priority_issues": [
    {
      "id": "ARCH-1",
      "type": "architecture",
      "severity": "high",
      "category": "Monolithic component",
      "file": "frontend/src/components/AnalysisResult.tsx:1-1110",
      "description": "Один компонент содержит визуализацию, экспорт, анализ и вызовы API",
      "impact": "Трудно тестировать и оптимизировать, дублирование HTML шаблонов",
      "estimated_fix_time": "4h"
    },
    {
      "id": "PERF-1",
      "type": "performance",
      "severity": "high",
      "category": "Full-file reads",
      "file": "backend/pdf_server.py:173-214",
      "description": "pandas читает весь CSV/Excel перед пагинацией",
      "impact": "Большие файлы кладут память и блокируют сервер",
      "estimated_fix_time": "3h"
    },
    {
      "id": "PERF-2",
      "type": "performance",
      "severity": "high",
      "category": "Repeated full LLM calls",
      "file": "frontend/src/App.tsx:213-244",
      "description": "Каждое добавление строк повторно отправляет весь массив в /api/analyze",
      "impact": "Латентность и квоты растут линейно от объёма данных",
      "estimated_fix_time": "3h"
    }
  ],
  "medium_priority_issues": [
    {
      "id": "QUALITY-1",
      "type": "code_quality",
      "severity": "medium",
      "category": "Loose typing/logging",
      "file": "frontend/src/components/AnalysisResult.tsx",
      "description": "Состояния объявлены как any и выводят полные данные в консоль",
      "impact": "Повышенный риск регрессий и утечек",
      "estimated_fix_time": "4h"
    },
    {
      "id": "TEST-1",
      "type": "testing",
      "severity": "medium",
      "category": "No automated tests",
      "file": "frontend/src/App.test.tsx",
      "description": "Остался шаблон CRA; тесты падают сразу",
      "impact": "Невозможно внедрить CI/CD и безопасный рефакторинг",
      "estimated_fix_time": "8h"
    }
  ],
  "low_priority_issues": [
    {
      "id": "DOC-1",
      "type": "documentation",
      "severity": "low",
      "category": "Outdated README",
      "file": "frontend/README.md",
      "description": "Фронтовый README остаётся шаблоном Create React App и не описывает продукт",
      "impact": "Новым разработчикам сложно понять сценарии запуска",
      "estimated_fix_time": "1h"
    }
  ],
  "technical_debt": {
    "level": "critical",
    "estimated_hours": 80,
    "blocks_development": true,
    "main_blockers": [
      "API ключи в репозитории — нельзя публиковать код",
      "Отсутствие тестов/CI делает любые изменения рискованными",
      "Монолитные компоненты App/AnalysisResult затрудняют расширение"
    ]
  },
  "constraints": {
    "backward_compatibility": false,
    "deadline": "none",
    "team_size": 1,
    "available_time_hours": 40,
    "environment": "local dev only",
    "expected_load": "до 1000 строк на страницу (100 МБ upload limit)"
  }
}
```

---

### 4. ДЕТАЛЬНЫЕ ЗАДАЧИ

#### [CRITICAL-1] 🔴 Убрать хардкод API ключей и дубли `.env`
**Категория:** Безопасность **Время:** ~30 мин **Риск:** Низкий **Зависимости:** нет  

**Проблема:** `.env` (и `backend/.env`) с реальными ключами лежат в Git, LLM helper'ы читают их напрямую и падают без них.  
**Выигрыш:** секреты не утекут, можно отделить dev/prod.

- Создать `backend/config.py`, подружить его с `dotenv`, добавить `Config.validate()` (пример кода уже в PRD).  
- Перенести чтение ключей из `os.getenv`/строк в Config.  
- Обновить `.gitignore`, оставить только `env.example`.  

```python
# Было (backend/llm/openai_helper.py)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Стало
from backend.config import Config
client = OpenAI(api_key=Config.OPENAI_API_KEY)
```

**Команды:**
```bash
cd backend
pip install python-dotenv
python -c "from backend.config import Config; Config.validate(); print('OK')"
```
**Откат:** `git checkout -- backend/config.py backend/llm/*.py .gitignore`.

---

#### [CRITICAL-2] 🔴 Санитайз HTML перед WeasyPrint
**Категория:** Безопасность **Время:** ~1 ч **Риск:** Средний **Зависимости:** CRITICAL-1 (Config для DEBUG флага)

**Проблема:** `/api/report` слепо принимает HTML и отдаёт WeasyPrint → XSS/SSRF/чтение локальных файлов.  
**Выигрыш:** можно безопасно встраивать отчёты.

**Шаги:**
1. Добавить белый список тегов + атрибутов (например, `bleach`).
2. Ограничить длину HTML (`len(report_html) < MAX_REPORT_BYTES`).  
3. Включить sandbox WeasyPrint (disable network).  

```python
# Было
html = HTML(string=data['report_html'])
pdf = html.write_pdf()

# Стало
from bleach.sanitizer import Cleaner
cleaner = Cleaner(tags=['p','b','i','table','tr','td','img'], attributes={'img': ['src', 'alt']}, strip=True)
safe_html = cleaner.clean(data['report_html'])
html = HTML(string=safe_html, base_url=None, url_fetcher=lambda url: (_ for _ in ()).throw(ValueError("External refs disabled")))
pdf = html.write_pdf()
```

**Команды:**
```bash
pip install bleach
pytest tests/test_report_endpoint.py -k sanitize -v
```
**Риск/откат:** если отчёт ломается → добавить feature flag `ALLOW_RAW_HTML`.

---

#### [CRITICAL-3] 🔴 Исправить краш `gigachat_helper` без ENV
**Категория:** Стабильность **Время:** ~30 мин **Риск:** Низкий  

**Проблема:** модуль поднимает `ValueError` при импорте, если нет `GIGACHAT_CREDENTIALS`, даже если пользователь не выбирает провайдера `giga`.  
**Решение:** лениво инициализировать клиента внутри `get_giga_response`, а в `TEST_MODE` возвращать мок.  

```python
# Было (верх файла)
if os.getenv("TEST_MODE", "false").lower() != "true":
    credentials = os.getenv("GIGACHAT_CREDENTIALS")
    if not credentials:
        raise ValueError("GIGACHAT_CREDENTIALS ...")

# Стало
def _init_client():
    credentials = Config.GIGACHAT_CREDENTIALS
    if not credentials:
        raise APIError("GigaChat credentials missing", status_code=500)
    return GigaChat(...)

def get_giga_response(...):
    if Config.TEST_MODE:
        return "Mock"
    client = _init_client()
    ...
```

**Команды:** `pytest tests/test_giga_fallback.py`.  

---

#### [CRITICAL-4] 🔴 Централизованные HTTP ошибки + выключить debug
**Категория:** Стабильность **Время:** ~1.5ч  

1. Создать `backend/errors.py` с `APIError`, `ValidationError`, `register_error_handlers`.  
2. Заменить `return jsonify({'error': str(e)}), 500` на `raise FileProcessingError("...")`.  
3. В `pdf_server.py` использовать `app.config['DEBUG']=Config.DEBUG` и запуск через `flask run` (а не `app.run(debug=True)`).  

```python
# Было
except Exception as e:
    logger.exception("Error during analysis")
    return jsonify({'error': str(e)}), 500

# Стало
from backend.errors import LLMError
...
except Exception as e:
    logger.exception("Error during analysis")
    raise LLMError("Failed to get LLM response") from e
```

**Команды:** `pytest tests/test_errors.py -v`, `FLASK_DEBUG=0 flask run`.  

---

#### [HIGH-1] 🟡 Stream CSV вместо чтения целиком
**Категория:** Производительность **Время:** ~3ч  

- Использовать `pandas.read_csv(..., chunksize=page_size)` и отдавать нужный chunk.  
- Реально подключить `process_large_csv` (сейчас мёртвый код).  
- Добавить тесты на 50k строк (заготовки `test_cars-1000.csv`).  

```python
# Было
df = pd.read_csv(temp_file_name, encoding='utf-8')
df_page = df.iloc[start:end]

# Стало
chunks = pd.read_csv(temp_file_name, chunksize=page_size, iterator=True)
df_page = next(islice(chunks, page-1, page), pd.DataFrame())
```

**Команды:** `pytest tests/test_upload_large.py -k chunk`.  

---

#### [HIGH-2] 🟡 Оптимизировать React (load more + монолиты)
**Категория:** Архитектура **Время:** ~6ч  

- Вынести логику загрузки в `hooks/useDataset.ts`.  
- Сохранить `datasetId` и `pageCursor`, чтобы отправлять только новые строки.  
- В `AnalysisResult` создавать подкомпоненты: `FilterPanel`, `Charts`, `ReportExporter`, `MissingDataPanel`.  

```ts
// Было (App.tsx)
const response = await analyzeLLM({ table_data: newAllData });

// Стало
const delta = newData.slice(lastAnalyzedRows);
const response = await analyzeLLM({ table_data_delta: delta, datasetId });
```

**Команды:** `npm run lint`, `npm test`, `npm run build`.  

---

#### [HIGH-3] 🟡 Вынести API baseURL и убрать raw fetch
**Категория:** Архитектура **Время:** ~2ч  

- Создать `frontend/src/api/client.ts` с axios instance, который использует `process.env.REACT_APP_API_URL`.  
- Переписать `handleAIFillStart` и PDF экспорт на этот клиент, убрать `http://localhost:5000`.  

```ts
// Было
const response = await fetch('http://localhost:5000/api/report', { ... });

// Стало
const client = axios.create({ baseURL: process.env.REACT_APP_API_URL });
const response = await client.post('/report', { report_html: htmlContent }, { responseType: 'blob' });
```

**Команды:** `REACT_APP_API_URL=https://api.example.com npm run build`.  

---

#### [MEDIUM-1] 🟢 Type hints и константы
**Категория:** Качество **Время:** ~4ч  

- Добавить `TypedDict` для `TableRow`, `BasicAnalysis`.  
- Вынести `REQUIRED_FIELDS`, `NUMERIC_COLUMNS` в `backend/constants.py`.  
- Проверить `mypy backend -p backend`.  

---

#### [MEDIUM-2] 🟢 Тесты
**Категория:** Тестирование **Время:** ~16ч  

1. Backend: pytest для `/api/upload`, `/api/analyze`, `/api/report`, `/api/fill-missing-ai`.  
2. Frontend: заменить CRA-тесты на React Testing Library (ререндер без load).  
3. Настроить GitHub Actions (pytest + npm test).  

---

#### [LOW-1] 🟤 Документация и DevOps
**Категория:** DX **Время:** ~3ч  

- `frontend/README.md`: описать реальные шаги (env vars, API URL).  
- Docker Compose с `services: backend, frontend, nginx`.  
- Обновить `docs/DEPLOYMENT.md` и добавить screenshot.  

---

### 5. МЕТРИКИ (До → После)

| Метрика | До | Цель | Улучшение |
|---------|----|------|-----------|
| Security issues | 3 critical | 0 | -100% |
| Backend OOM на 100MB CSV | Да | Нет (chunked) | стабильность |
| Среднее время ответа `/api/analyze` | >3s | <1s (кэш/дельта) | -66% |
| React bundle | ~850 KB | <450 KB (code splitting, убраны неиспользуемые пакеты) | -47% |
| Test coverage backend | 0% | ≥60% | +60pp |
| Test coverage frontend | 0% | ≥50% | +50pp |
| Type hints backend | 40% | 90% | +50pp |
| Type coverage frontend | 60% | 90% | +30pp |

---

### 6. ЧЕКЛИСТ

- [ ] Создать ветку `refactor/security`  
- [ ] Удалить секреты, обновить `.gitignore`, прогнать `git ls-files | grep '.env'`  
- [ ] Интегрировать `bleach`, протестировать `/api/report`  
- [ ] Реализовать центральный error handler, `pytest tests/test_errors.py`  
- [ ] Включить chunked CSV и протестировать на `test_cars-1000.csv`  
- [ ] Рефакторить React по шагам (hooks → компоненты → API client)  
- [ ] Добавить тесты и CI  
- [ ] Обновить документацию и Docker  

---

### 7. ПОЛЕЗНЫЕ КОМАНДЫ

```bash
# Backend
pip install -r backend/requirements.txt
black backend && isort backend
pytest tests -v --maxfail=1
FLASK_DEBUG=0 flask run

# Frontend
npm install
REACT_APP_API_URL=http://localhost:5000 npm start
npm run lint && npm test -- --watch=false
npm run build

# Security
pip-audit
npm audit && npm audit fix

# Docker (после настройки)
docker compose up --build
```

---

### 8. ЗАКЛЮЧЕНИЕ

**Итоговая оценка:** 4/10 → после рефакторинга целимcя ≥7/10.  
**Рекомендация:** Серьёзный рефакторинг (без переписывания с нуля).  

1. **Сначала безопасность** (секреты, HTML, error handling).  
2. **Далее производительность** (chunked CSV, уменьшение LLM нагрузок).  
3. **Затем тесты + типизация** (медиум).  
4. **В конце** документация и DevOps.  

План рассчитан на одиночного разработчика на 7-8 рабочих дней. Выполняем по приоритету, коммитим атомарно:  
`git commit -m "[CRITICAL-2] Sanitize report HTML"` и т.д.  

> **Не пытайся чинить всё сразу.** Закрой критические вещи — и только потом берись за глубокий рефакторинг UI/архитектуры. Это позволит повысить доверие к проекту и безопасно включить его в CI/CD.
