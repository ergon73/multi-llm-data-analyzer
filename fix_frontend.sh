#!/bin/bash

echo "🔄 Исправляем проблемы с React..."

# Переходим в папку frontend
cd /c/Users/ergon73/CursorProjects/VCb03/frontend

echo "📦 Удаляем node_modules..."
rm -rf node_modules

echo "🧹 Очищаем npm cache..."
npm cache clean --force

echo "📦 Переустанавливаем зависимости..."
npm install

echo "✅ Готово! Теперь можно запускать:"
echo "npm start"

echo ""
echo "🚀 Автоматически запускаем фронтенд..."
npm start
