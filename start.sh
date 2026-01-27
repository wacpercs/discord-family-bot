#!/bin/bash

# Скрипт для запуска Discord бота

echo "🚀 Запуск Discord бота для семьи..."

# Проверка наличия Python
if ! command -v python3 &> /dev/null
then
    echo "❌ Python 3 не установлен!"
    exit 1
fi

# Проверка наличия pip
if ! command -v pip3 &> /dev/null
then
    echo "❌ pip3 не установлен!"
    exit 1
fi

# Проверка наличия .env файла
if [ ! -f .env ]; then
    echo "⚠️ Файл .env не найден!"
    echo "📝 Создайте файл .env на основе .env.example"
    exit 1
fi

# Установка зависимостей (если требуется)
if [ "$1" == "--install" ]; then
    echo "📦 Установка зависимостей..."
    pip3 install -r requirements.txt
fi

# Запуск бота
echo "✅ Запуск бота..."
python3 bot.py
