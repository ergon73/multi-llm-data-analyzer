@echo off
echo 🔄 Исправляем проблемы с React...

cd /d "C:\Users\ergon73\CursorProjects\VCb03\frontend"

echo 📦 Удаляем node_modules...
if exist node_modules (
    rmdir /s /q node_modules
    echo ✅ node_modules удален
) else (
    echo ℹ️ node_modules не найден
)

echo 🧹 Очищаем npm cache...
npm cache clean --force

echo 📦 Переустанавливаем зависимости...
npm install

echo ✅ Готово! Теперь можно запускать:
echo npm start

pause
