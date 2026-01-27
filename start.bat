@echo off
chcp 65001 >nul
title Discord Bot - Семья GTA 5 RP

echo.
echo ════════════════════════════════════════════
echo    🚀 Запуск Discord бота для семьи
echo ════════════════════════════════════════════
echo.

REM Проверка наличия Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не установлен!
    echo 📥 Скачайте Python с https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Проверка наличия .env файла
if not exist .env (
    echo ⚠️ Файл .env не найден!
    echo 📝 Создайте файл .env на основе .env.example
    echo.
    pause
    exit /b 1
)

REM Установка зависимостей при первом запуске
if "%1"=="--install" (
    echo 📦 Установка зависимостей...
    pip install -r requirements.txt
    echo.
)

REM Запуск бота
echo ✅ Запуск бота...
echo.
python bot.py

REM Если бот завершился с ошибкой
if errorlevel 1 (
    echo.
    echo ❌ Бот завершился с ошибкой!
    pause
)
