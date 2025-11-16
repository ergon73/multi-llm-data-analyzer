@echo off
echo Проверка окружения и запуск сервера...

cd /d "C:\Users\ergon73\CursorProjects\VCb03"

echo.
echo 1. Проверяем виртуальное окружение...
if exist .venv\Scripts\activate.bat (
    echo ✅ Виртуальное окружение найдено
) else (
    echo ❌ Виртуальное окружение не найдено
    echo Создаем виртуальное окружение...
    python -m venv .venv
    if errorlevel 1 (
        echo ❌ Ошибка создания виртуального окружения
        pause
        exit /b 1
    )
    echo ✅ Виртуальное окружение создано
)

echo.
echo 2. Активируем виртуальное окружение...
call .venv\Scripts\activate.bat

echo.
echo 3. Устанавливаем зависимости...
pip install -r backend\requirements.txt

echo.
echo 4. Проверяем Flask...
python -c "import flask; print('Flask версия:', flask.__version__)"

echo.
echo 5. Запускаем сервер...
cd backend
python pdf_server.py

pause
