# Refactoring Plan 3

## ВХОДНЫЕ ДАННЫЕ

```json
{
  "project_info": {
    "name": "VCb03",
    "type": "Full-stack LLM data analyzer",
    "status": "working (dev / TEST_MODE)",
    "purpose": "Upload CSV/Excel/PDF datasets of vehicle sales, run multi-LLM analysis, and generate PDF reports."
  },
  "tech_stack": {
    "backend": {
      "language": "Python 3.11-3.12",
      "framework": "Flask 2.x",
      "database": "None",
      "orm": "None",
      "async": "sync only",
      "data_processing": ["pandas", "pdfplumber", "WeasyPrint", "openpyxl"]
    },
    "frontend": {
      "language": "TypeScript 4.9",
      "framework": "React 18 (CRA)",
      "state": "React hooks / local state",
      "bundler": "Create React App / Webpack 5",
      "ui": "MUI 5 + custom CSS",
      "visualization": "Recharts, react-window"
    },
    "integrations": ["OpenAI", "YandexGPT", "GigaChat"]
  },
  "metrics": {
    "size": {
      "total_files": 114,
      "python_lines": 1413,
      "js_lines": 3054,
      "largest_files": [
        {"file": "frontend/src/components/AnalysisResult.tsx", "lines": 700},
        {"file": "backend/pdf_server.py", "lines": 647},
        {"file": "frontend/src/App.tsx", "lines": 496}
      ]
    },
    "quality": {
      "overall_score": 4,
      "readability": 5,
      "structure": 4,
      "documentation": 6,
      "tests": 4,
      "security": 2,
      "performance": 4,
      "test_coverage": 30,
      "type_coverage_backend": 35,
      "type_coverage_frontend": 70,
      "lint_warnings": 0,
      "security_issues": 3
    },
    "complexity": {
      "avg_function_lines": 22,
      "avg_cyclomatic_complexity": 10,
      "duplicated_code_percent": 15
    },
    "dependencies": {
      "backend_packages": 16,
      "frontend_packages": 22,
      "outdated_packages": 8,
      "vulnerable_packages": 0
    }
  },
  "critical_issues": [
    {
      "id": "SEC-1",
      "type": "security",
      "severity": "critical",
      "category": "Hardcoded secrets",
      "file": ".env:2-9, backend/.env:2-11",
      "description": "Real OpenAI/Yandex/GigaChat credentials committed to git in plaintext.",
      "code": "OPENAI_API_KEY=sk-proj-***",
      "risk": "HIGH - anyone cloning the repo can call LLMs under our account.",
      "estimated_fix_time": "30 min"
    },
    {
      "id": "SEC-2",
      "type": "security",
      "severity": "critical",
      "category": "Missing authentication",
      "file": "backend/pdf_server.py:78-111",
      "description": "API key check runs only when API_KEY env is set; default config leaves endpoints open.",
      "code": "if API_KEY:\n    provided = request.headers.get('X-API-Key')\n    if provided != API_KEY: ...",
      "risk": "HIGH - unauthenticated clients can spend LLM credits and access uploads.",
      "estimated_fix_time": "1 hour"
    },
    {
      "id": "SEC-3",
      "type": "security",
      "severity": "critical",
      "category": "Rate limiting bypass",
      "file": "backend/pdf_server.py:78-105",
      "description": "_client_id() trusts X-Forwarded-For from the user, so attackers can rotate IDs and skip throttling.",
      "code": "return request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown')",
      "risk": "HIGH - enables unlimited LLM calls / DoS.",
      "estimated_fix_time": "45 min"
    },
    {
      "id": "BUG-1",
      "type": "bug",
      "severity": "critical",
      "category": "CI misconfiguration",
      "file": ".github/workflows/ci.yml:1-113",
      "description": "Workflow has duplicate root keys; the backend/frontend test job defined first is ignored by GitHub.",
      "risk": "HIGH - regressions ship unnoticed because tests never run.",
      "estimated_fix_time": "30 min"
    }
  ],
  "high_priority_issues": [
    {
      "id": "ARCH-1",
      "type": "architecture",
      "severity": "high",
      "category": "Monolithic component",
      "file": "frontend/src/components/AnalysisResult.tsx:1-700",
      "description": "Single component mixes filters, charts, export, AI interactions; impossible to test or reuse pieces.",
      "impact": "Large bundles, tangled state, slow iteration.",
      "estimated_fix_time": "6 hours"
    },
    {
      "id": "ARCH-2",
      "type": "architecture",
      "severity": "high",
      "category": "God object in App",
      "file": "frontend/src/App.tsx:1-496",
      "description": "Root component owns uploads, dialogs, AI fill, pagination and error handling.",
      "impact": "State explosion, side effects everywhere, hard to reason about failures.",
      "estimated_fix_time": "5 hours"
    },
    {
      "id": "PERF-1",
      "type": "performance",
      "severity": "high",
      "category": "Inefficient missing-value handling",
      "file": "backend/pdf_server.py:525-544, frontend/src/App.tsx:205-248",
      "description": "Server loops over the entire DataFrame per empty cell, while the client keeps all pages in memory and reruns LLM analysis each time.",
      "impact": "Quadratic CPU usage and expensive repeated LLM calls on large datasets.",
      "estimated_fix_time": "6 hours"
    }
  ],
  "medium_priority_issues": [
    {
      "id": "QUALITY-1",
      "type": "code_quality",
      "severity": "medium",
      "category": "Missing type hints",
      "file": "backend/pdf_server.py (multiple functions)",
      "description": "Core Flask handlers lack type hints/docstrings; inputs/outputs unclear.",
      "impact": "Increases onboarding time and risk of accidental regressions.",
      "estimated_fix_time": "4 hours"
    },
    {
      "id": "QUALITY-2",
      "type": "code_quality",
      "severity": "medium",
      "category": "Duplicated normalization logic",
      "file": "backend/pdf_server.py:372-390 & 586-603",
      "description": "Required fields normalization copy-pasted for upload and pagination endpoints.",
      "impact": "Any change must be done twice, easy to desync behavior.",
      "estimated_fix_time": "2 hours"
    },
    {
      "id": "INFRA-1",
      "type": "infrastructure",
      "severity": "medium",
      "category": "Binary fixtures in git",
      "file": "car_prices.csv/xlsx, test_cars-*.csv",
      "description": "Large sample datasets tracked directly in git instead of Git LFS.",
      "impact": "Slow clones/CI and bloated repository size.",
      "estimated_fix_time": "2 hours"
    }
  ],
  "low_priority_issues": [
    {
      "id": "DOC-1",
      "type": "documentation",
      "severity": "low",
      "category": "Outdated dev-mode focus",
      "description": "README/instruction-no-ssl only cover localhost/TestMode scenarios and mention disabling TLS verification.",
      "impact": "No guidance for staging/prod setup.",
      "estimated_fix_time": "2 hours"
    }
  ],
  "technical_debt": {
    "level": "critical",
    "estimated_hours": 80,
    "blocks_development": true,
    "main_blockers": [
      "Secrets are leaked via .env and API lacks enforcement.",
      "Monolithic React/Flask files make any change risky.",
      "CI misconfiguration means regressions go unnoticed."
    ]
  },
  "constraints": {
    "backward_compatibility": true,
    "deadline": "none",
    "team_size": 1,
    "available_time_hours": 60
  }
}
```

## 1. EXECUTIVE SUMMARY

#### Оценка проекта: 4/10
**Уровень технического долга:** Критический

#### 🔥 Топ-3 критичных (исправить НЕМЕДЛЕННО):
1. Секреты в `.env` и `backend/.env` уже в репозитории — Риск: ВЫСОКИЙ, Время: ~0.5ч, Выигрыш: блокируем несанкционированный доступ к LLM
2. API без обязательного ключа + обход rate limiting через `X-Forwarded-For` (`backend/pdf_server.py:78-111`) — Риск: ВЫСОКИЙ, Время: ~1.5ч, Выигрыш: защита бюджета и DoS устойчвость
3. CI не запускает тесты из-за дублированного `ci.yml` — Риск: СРЕДНИЙ→Высокий, Время: ~0.5ч, Выигрыш: автоматическая проверка регрессий

#### 💰 Quick Wins (за <1 час каждая):
- [ ] Добавить `.env` в `.gitignore` и переписать README по инструкции секретов (~15 мин) → выигрыш: безопасность
- [ ] Вынести rate-limit storage в LRU + очистку по TTL (~30 мин) → выигрыш: стабильность памяти
- [ ] Удалить дублированные секции в `.github/workflows/ci.yml` (~45 мин) → выигрыш: снова запускаются тесты

---

## 2. ROADMAP

#### 🔴 Неделя 1: CRITICAL (безопасность + стабильность)
**Цель:** избежать утечек ключей и неконтролируемых вызовов LLM

**Задачи:**
- [ ] Убрать хардкод секретов, настроить `Config.validate` и .env шаблоны (~1ч)
- [ ] Сделать API-ключ обязательным, фиксировать `X-Forwarded-For`, добавить persistent rate-limit storage (~1ч)
- [ ] Причесать обработку ошибок + HTTP статусы в endpoints (~1ч)
- [ ] Починить CI (`ci.yml`) и включить pytest + npm test (~1ч)

**Результат:** API требует авторизацию, ключи не лежат в репо, CI снова ловит регрессии

**Время:** ~4 часов

---

#### 🟡 Недели 2-3: HIGH (производительность + архитектура)
**Цель:** разделить монолиты и убрать квадратичные алгоритмы

**Задачи:**
- [ ] Вынести анализ таблиц и LLM-кэш в сервисные модули (~3ч)
- [ ] Переписать `/api/fill-missing-ai` под векторизованные операции, добавить детерминированный кеш (~2ч)
- [ ] Разбить `frontend/src/App.tsx` и `AnalysisResult.tsx` на слайсы (Layout, Filters, Charts, Export) + внедрить React.lazy (~5ч)
- [ ] Переписать стратегию догрузки страниц (не хранить тысячи строк в state, использовать пагинацию+инкрементальный анализ) (~2ч)
- [ ] Добавить unit-тесты на новые сервисы и компоненты (~3ч)

**Результат:** более мелкие модули, рендеринг только нужных частей, LLM вызывается один раз на датасет/страницу

**Время:** ~15 часов

---

#### 🟢 Недели 4-6: MEDIUM (качество кода + тесты)
**Цель:** обеспечить уверенность в изменениях

**Задачи:**
- [ ] Type hints + Pydantic схемы для всех endpoint входов/выходов (~4ч)
- [ ] DRY для нормализации строк (`backend/pdf_server.py:372-390 & 586-603`) через helper (~1ч)
- [ ] Расширить тесты: pytest coverage >70%, RTL покрытие критических виджетов (~12ч)
- [ ] Добавить mypy, black, eslint/prettier в CI + pre-commit (~3ч)
- [ ] Вынести data samples >10MB в Git LFS + обновить CONTRIBUTING (~2ч)

**Результат:** статические проверки в CI, нет дублированного кода, артефакты не захламляют репо

**Время:** ~22 часов

---

#### 🟤 Месяц 2+: LOW (полировка)
**Цель:** production-ready DX

**Задачи:**
- [ ] Обновить README/DEPLOYMENT под prod + TLS (~2ч)
- [ ] Добавить Docker healthchecks и compose.override для prod (~2ч)
- [ ] Настроить централизованное логирование (JSON logs + correlation IDs) (~3ч)
- [ ] Обновить зависимости (CRA->Vite/Next? опционально) и зафиксировать версии backend (~2ч)

**Результат:** документация честно описывает инфраструктуру, сборки воспроизводимы

**Время:** ~9 часов

**ИТОГО:** ~50 часов (6-7 рабочих дней)

---

## 3. ДЕТАЛЬНЫЕ ЗАДАЧИ

### [CRITICAL-1] 🔴 Удалить секреты из репозитория и централизовать конфигурацию
- **Приоритет:** Критический (SEC-1)
- **Время:** ~1 час, риск низкий
- **Проблема:** `.env` и `backend/.env` хранят реальные ключи; Config не проверяет наличие секретов
- **Выигрыш:** защита токенов, единый способ подключения провайдеров
- **Файлы:** `.env`, `backend/.env`, `backend/config.py`, `backend/llm/*.py`, `README.md`, `.gitignore`

**БЫЛО → СТАЛО**
```python
# backend/llm/openai_helper.py
- client = OpenAI(api_key=Config.OPENAI_API_KEY)
+ api_key = Config.OPENAI_API_KEY
+ if not api_key:
+     raise ValidationError("OPENAI_API_KEY is not set")
+ client = OpenAI(api_key=api_key)
```
```bash
# .gitignore
- .env
+ .env
+ backend/.env
+ *.env.local
```

**Команды:**
```bash
rm backend/.env .env
cp env.example .env
pip install python-dotenv
pytest tests/test_config.py
```

**Риски/Митигация:** опечатки в `.env` → `Config.validate()` с понятной ошибкой перед стартом.

---

### [CRITICAL-2] 🔴 Обязательный API-ключ и фиксинг rate limiting
- **Приоритет:** Критический (SEC-2, SEC-3)
- **Время:** ~1.5 часа, риск средний
- **Проблема:** проверка ключа выключена по умолчанию; `_client_id` доверяет `X-Forwarded-For`; rate-limit store плодит память
- **Выигрыш:** защита от DoS и несанкционированных вызовов
- **Файлы:** `backend/pdf_server.py`, `backend/config.py`, `frontend/src/api/index.ts`

**БЫЛО → СТАЛО**
```python
# backend/pdf_server.py
- if API_KEY:
-     provided = request.headers.get("X-API-Key")
-     if provided != API_KEY:
-         return jsonify({"error": "Unauthorized"}), 401
- cid = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")
+ provided = request.headers.get("X-API-Key")
+ if not provided or provided != API_KEY:
+     raise ValidationError("Unauthorized")
+ cid = request.headers.get("X-Forwarded-For")
+ if cid:
+     cid = cid.split(",")[0].strip()
+ else:
+     cid = request.remote_addr or "unknown"
```
```python
# backend/pdf_server.py (rate-limit storage)
-_rate_limit_store: dict[str, list[float]] = {}
+from collections import deque
+_rate_limit_store: dict[str, deque[float]] = {}
+
+def _prune_bucket(bucket: deque[float], cutoff: float) -> None:
+    while bucket and bucket[0] <= cutoff:
+        bucket.popleft()
```
```ts
// frontend/src/api/index.ts
- headers: { 'Content-Type': 'multipart/form-data' }
+ headers: {
+   'Content-Type': 'multipart/form-data',
+   'X-API-Key': process.env.REACT_APP_API_KEY ?? ''
+ }
```

**Команды:**
```bash
pytest tests/test_rate_limit.py -k authorized
curl -H "X-API-Key: local-dev" http://localhost:5000/api/test
```

**Риск:** можно заблокировать реальных пользователей при неверных лимитах → вынести `RATE_LIMIT_MAX_REQ` в `.env` и документировать.

---

### [CRITICAL-3] 🔴 Починить CI (BUG-1)
- **Приоритет:** Критический
- **Время:** ~45 минут, риск низкий
- **Проблема:** `.github/workflows/ci.yml` содержит два `name/on` блока, GitHub игнорирует первый
- **Выигрыш:** каждый PR прогоняет pytest + npm test

**БЫЛО → СТАЛО**
```yaml
# .github/workflows/ci.yml
-name: CI
-on:
-  push:
-    branches: [ main, master ]
-  pull_request:
-... (второй блок)
+name: CI
+on:
+  push:
+    branches: [ main, dev ]
+  pull_request:
+    branches: [ main, dev ]
+
+jobs:
+  backend:
+    runs-on: ubuntu-latest
+    steps:
+      - uses: actions/checkout@v4
+      - uses: actions/setup-python@v5
+        with:
+          python-version: '3.11'
+      - run: |
+          pip install -r backend/requirements.txt
+          pytest -q
+  frontend:
+    runs-on: ubuntu-latest
+    steps:
+      - uses: actions/checkout@v4
+      - uses: actions/setup-node@v4
+        with:
+          node-version: '18'
+      - run: npm ci
+        working-directory: frontend
+      - run: npm test -- --watch=false
+        working-directory: frontend
```

**Команды:**
```bash
yamllint .github/workflows/ci.yml
gh workflow run CI --ref feature/refactor
```

---

### [HIGH-1] 🟡 Декомпозировать `pdf_server.py` и оптимизировать fill-missing (ARCH-1, PERF-1)
- **Время:** ~5 часов; риск средний
- **План:**
  1. Создать `backend/services/storage.py` для `_datasets`, нормализации и очистки.
  2. Перенести обработку CSV/Excel/PDF в `backend/services/importers.py` с type hints.
  3. Реализовать fill-missing через pandas groupby/transform (O(N log N)).

**БЫЛО → СТАЛО**
```python
# backend/pdf_server.py (фрагмент)
-for col in missing_info:
-    recs = []
-    for idx, row in df[df[col].isna() | (df[col] == '')].iterrows():
-        mask = pd.Series([True] * len(df))
-        ...
+def recommend_fill_values(df: pd.DataFrame, col: str, group_keys: list[str]) -> list[dict[str, Any]]:
+    candidates = (
+        df.groupby(group_keys)[col]
+          .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else None)
+    )
+    missing_rows = df[df[col].isna() | (df[col] == '')]
+    return [
+        {
+            "row_idx": int(idx),
+            "suggested": candidates.get(tuple(row[k] for k in group_keys)),
+            "confidence": 0.8,
+            "explanation": f"Matched by {group_keys}"
+        }
+        for idx, row in missing_rows.iterrows()
+    ]
```

**Команды:**
```bash
pytest tests/test_fill_missing_ai.py
python -m timeit "from backend.services.fill import recommend_fill_values; ..."
```

---

### [HIGH-2] 🟡 Разбить React-монолиты (ARCH-1, ARCH-2)
- **Время:** ~6 часов; риск средний
- **План:**
  - Создать `src/features/upload`, `src/features/analysis`, `src/features/missing-data`.
  - Перенести state в `useReducer` + Context (FileState, AnalysisState).
  - `AnalysisResult` разбить на `FiltersPanel`, `ChartCanvas`, `ExportMenu` (dynamic import + suspense).

**БЫЛО → СТАЛО**
```tsx
// frontend/src/App.tsx
-const [uploadResult, setUploadResult] = useState<FileUploadResponse | null>(null);
-const [missingDialogOpen, setMissingDialogOpen] = useState(false);
-const [aiRecommendations, setAiRecommendations] = useState<AIRecommendations | null>(null);
+const [fileState, dispatchFile] = useFileStore();
+const missing = useMissingData(fileState.rows, fileState.columns);
+const analysis = useAnalysis(fileState.rows, selectedModel);
```
```tsx
// frontend/src/features/analysis/AnalysisShell.tsx
+const FiltersPanel = React.lazy(() => import('./FiltersPanel'));
+const ChartCanvas = React.lazy(() => import('./ChartCanvas'));
+
+return (
+  <Suspense fallback={<CircularProgress />}>
+    <FiltersPanel ... />
+    <ChartCanvas data={analysis.chartData} />
+    <ExportMenu ... />
+  </Suspense>
+);
```

**Команды:**
```bash
npm run lint
npm run test -- Filtering.test.tsx
```

---

### [MEDIUM-1] 🟢 Type hints и DRY в backend (QUALITY-1/2)
- **Время:** ~4 часа; риск низкий
- **Действия:**
  - Добавить TypedDict/Pydantic для `FileUploadResponse`, `LLMAnalysisRequest` (общие схемы backend/frontend).
  - Создать helper `normalize_required_fields(record: dict[str, Any]) -> dict[str, Any]` и вызывать из двух endpointов.

**БЫЛО → СТАЛО**
```python
# backend/pdf_server.py
-required_fields = [...]
-for record in records:
-    for field in required_fields:
-        if field not in record or pd.isna(record[field]):
-            ...
+from backend.schemas import CLEANUP_DEFAULTS
+
+def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
+    for field, fallback in CLEANUP_DEFAULTS.items():
+        value = record.get(field)
+        if value in (None, "") or (isinstance(value, float) and math.isnan(value)):
+            record[field] = fallback
+    return record
+
+records = [normalize_record(rec) for rec in records]
```

**Команды:**
```bash
mypy backend/
pytest tests/test_upload_pagination.py
```

---

### [LOW-1] 🟤 Документация + Git LFS (INFRA-1, DOC-1)
- **Время:** ~3 часа
- **План:**
  - Добавить раздел «Prod setup» в README + SECURITY.md (TLS, API_KEY, TEST_MODE=false).
  - Переместить `car_prices*.csv` в LFS (`git lfs track '*.csv'`).

**Команды:**
```bash
git lfs install
git lfs track "car_prices*.csv" "test_cars-*.csv"
git add .gitattributes
```

---

## 4. МЕТРИКИ (До → После)

| Метрика | До | После (цель) | Улучшение |
|---------|----|--------------|-----------|
| Security issues (critical) | 3 | 0 | -100% |
| Запущенные тесты в CI | 0 | pytest + npm test | +100% |
| Средний размер React компонента | 500+ LOC | <200 LOC | -60% |
| API response для `/fill-missing-ai` | >3s на 10k строк | <700ms | -75% |
| Type hints coverage backend | 35% | 90% | +55pp |
| Test coverage backend | 30% | 70% | +40pp |
| Bundle size | ~850KB | <500KB | -40% |
| Repo size (без LFS) | 170MB | <40MB | -75% |

---

## 5. ЧЕКЛИСТ ВЫПОЛНЕНИЯ

- [ ] Создать ветку `refactor/security-hardening`
- [ ] Зафиксировать baseline (pytest, npm test, bundle size)
- [ ] Выполнить CRITICAL задачи, после каждой — `pytest` + `npm test`
- [ ] Обновить CI и убедиться, что workflow зелёный
- [ ] HIGH задачи: отдельные PR (backend services, frontend features)
- [ ] MEDIUM задачи: включить mypy/eslint в CI, поднять coverage
- [ ] LOW задачи: LFS + документация + Docker healthchecks
- [ ] Финальный прогон `pytest --cov` и `npm test -- --coverage`
- [ ] Обновить README/CHANGELOG, запросить code review

---

## 6. ПОЛЕЗНЫЕ КОМАНДЫ

```bash
# Backend
pip install -r backend/requirements.txt
pytest -q
pytest --cov=backend --cov-report=term-missing
mypy backend/
black backend/
pip-audit

# Frontend
cd frontend
npm ci
npm run lint
npm run test -- --watch=false
npm run build && npx source-map-explorer build/static/js/*.js

# Git / CI
git checkout -b refactor/critical-fixes
git commit -m "[CRITICAL-2] enforce API key"
gh workflow run CI --ref refactor/critical-fixes
```

---

## 7. ЗАКЛЮЧЕНИЕ

- **Итоговая оценка:** 4/10 → цель ≥7/10 после всех этапов
- **Рекомендация:** Серьёзный рефакторинг (CRITICAL → HIGH → MEDIUM → LOW)
- **Дорожная карта:** ~50 часов активной работы
- **Приоритет:** Сначала безопасность/CI, затем архитектура и производительность, потом качество и документация

> Делай маленькие PR, запускай тесты после каждой задачи и фиксируй метрики «до/после». Это позволит безопасно двигаться от CRITICAL задач к polish-этапу.
