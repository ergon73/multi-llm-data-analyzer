@echo off
echo Запуск бэкенда...

cd /d "C:\Users\ergon73\CursorProjects\VCb03"

echo Активируем виртуальное окружение...
call .venv\Scripts\activate.bat

echo Переходим в папку backend...
cd backend

echo Запускаем сервер...
python pdf_server.py

pause
