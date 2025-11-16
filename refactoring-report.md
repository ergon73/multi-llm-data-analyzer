### Refactoring QA Report

#### Summary
- Critical roadmap items are still missing: there is no centralized `Config`, CSV uploads still read the whole file, and every LLM call still receives the full dataset.
- The frontend build (`npm run build`) fails because of conflicts in `AnalysisResult`, and the new virtualized table breaks the table DOM structure.
- Testing infrastructure (pytest env, secrets hygiene) was not implemented, so the current code cannot be validated end-to-end.

#### Key findings
1. **Frontend build fails.** `frontend/src/components/AnalysisResult.tsx:62` declares `const [autoCharts, setAutoCharts]`, and `frontend/src/components/AnalysisResult.tsx:85` declares `const autoCharts = useAutoCharts(...)`. `npm run build` aborts with `Identifier 'autoCharts' has already been declared`, so the UI cannot be built.
2. **Config layer never appeared.** The app still calls `load_dotenv`/`os.getenv` directly inside handlers (`backend/pdf_server.py:27-33`, `backend/pdf_server.py:76-103`, `backend/llm/gigachat_helper.py:16-35`). There is no `Config.validate()` and no required-variable checks, leaving CRITICAL-1 unresolved.
3. **Secrets remain in the repo.** `backend/.env:2-12` still carries live Yandex/OpenAI/GigaChat keys. The planned move to clean `.env.example` plus purging the committed secrets never happened.
4. **CSV streaming is ineffective.** `_csv_get_page` (`backend/pdf_server.py:160-184`) always re-reads the file with `pd.read_csv(..., skiprows=...)`, so every page load parses the entire CSV. The `chunksize` branch never runs, meaning 50k+ rows are still loaded into memory in one go.
5. **LLM still receives the whole table.** `/api/analyze` only accepts `table_data` and ignores dataset IDs (`backend/pdf_server.py:435-464`), while the frontend keeps re-sending the accumulated rows on every `handleLoadMore` (`frontend/src/App.tsx:222-244`). HIGH-2 (`dataset_hash+model` cache and deltas) is missing, so latency and cost remain quadratic.
6. **Temp files can overwrite each other.** `upload_file` writes uploads to `os.path.join(tempfile.gettempdir(), secure_filename(file.filename))` (`backend/pdf_server.py:325-327`). Two users uploading `data.csv` will trample each other and `_datasets` will point to the wrong data.
7. **Virtualized table breaks markup.** `VirtualizedTable` inserts a `react-window` `<div>` directly inside `<TableBody>` (`frontend/src/components/VirtualizedTable.tsx:8-33`), yielding `<tbody><div>…</div></tbody>`. MUI/ARIA semantics break and scrolling glitches appear.

#### Additional notes
- Temp datasets stored in `_datasets` (`backend/pdf_server.py:325-333`) are never cleaned up, so the OS temp folder will grow without bound.
- `frontend/src/components/ModelSelector.tsx:9-47` and `frontend/src/App.tsx:120-156` still spam `console.log` even though logging was supposed to sit behind a DEBUG flag.

#### Tests / checks
- `npm run build` — **FAILED**: `Identifier 'autoCharts' has already been declared` (see `AnalysisResult.tsx:85`).
- `.venv\Scripts\python.exe -m pytest` — **FAILED**: `No module named pytest`. `backend/requirements.txt` still does not list pytest, so the promised backend tests cannot run.
