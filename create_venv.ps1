# Создание виртуального окружения
Write-Host "Создание виртуального окружения..." -ForegroundColor Green
python -m venv venv

# Активация виртуального окружения
Write-Host "Активация виртуального окружения..." -ForegroundColor Green
.\venv\Scripts\Activate.ps1

# Обновление pip
Write-Host "Обновление pip..." -ForegroundColor Green
python -m pip install --upgrade pip

# Установка зависимостей
Write-Host "Установка зависимостей из requirements.txt..." -ForegroundColor Green
pip install -r backend\requirements.txt

Write-Host "Виртуальное окружение создано и настроено!" -ForegroundColor Green
Write-Host "Для активации окружения используйте команду: .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
Write-Host "Для деактивации окружения используйте команду: deactivate" -ForegroundColor Yellow 