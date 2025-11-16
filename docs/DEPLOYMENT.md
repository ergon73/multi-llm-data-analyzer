# Деплой

## Локально (dev)
1) Backend
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows
pip install -r backend/requirements.txt
copy env.example .env
python backend/pdf_server.py
```
2) Frontend
```
cd frontend
npm install
npm start
```

## Production (вариант)
- Собрать фронтенд: `cd frontend && npm run build`
- Сервис backend (systemd / PM2 / Docker)
- Отдача статики (Nginx) и прокси на Flask `:5000`
- Настроить переменные окружения (без .env в проде)

## Переменные окружения
См. `env.example`


