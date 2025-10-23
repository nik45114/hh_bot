#!/bin/bash

echo "🚀 Установка HH Job Bot"
echo "======================="

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден. Установи Python 3.8+"
    exit 1
fi

echo "✅ Python найден: $(python3 --version)"

# Создание виртуального окружения
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
else
    echo "✅ Виртуальное окружение уже существует"
fi

# Активация виртуального окружения
echo "🔧 Активация виртуального окружения..."
source venv/bin/activate

# Установка зависимостей
echo "📥 Установка зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt

# Проверка .env файла
if [ ! -f ".env" ]; then
    echo "⚠️  Файл .env не найден!"
    echo "Копирую .env.example в .env..."
    cp .env.example .env
    echo "❗ ВАЖНО: Отредактируй файл .env и укажи свои данные!"
    echo "   - TELEGRAM_BOT_TOKEN (получи у @BotFather)"
    echo "   - OPENAI_API_KEY (получи на platform.openai.com)"
    echo "   - ALLOWED_USER_ID (получи у @userinfobot)"
    echo ""
    read -p "Нажми Enter после настройки .env файла..."
fi

# Проверка resume_data.py
echo "📝 Не забудь заполнить resume_data.py своими данными!"
echo ""

# Запуск бота
echo "🤖 Запуск бота..."
python bot.py
