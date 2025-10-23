# 🚀 Быстрая установка на сервере через SSH

## Шаг 1: Подключись к серверу

```bash
ssh user@your-server.com
```

## Шаг 2: Установи зависимости

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Python и Git
sudo apt install python3 python3-pip python3-venv git -y
```

## Шаг 3: Клонируй репозиторий

```bash
cd ~
git clone https://github.com/nik45114/hh_bot.git
cd hh_bot
```

## Шаг 4: Настрой .env файл

```bash
# Скопируй пример
cp .env.example .env

# Отредактируй файл (используй nano или vim)
nano .env
```

**Важные параметры:**
- `TELEGRAM_BOT_TOKEN` - получи у @BotFather в Telegram
- `OPENAI_API_KEY` - получи на platform.openai.com
- `ALLOWED_USER_ID` - твой Telegram ID (получи у @userinfobot)

## Шаг 5: Заполни данные резюме

```bash
nano resume_data.py
```

Укажи свои:
- Имя и позицию
- Опыт работы
- Навыки
- Образование

## Шаг 6: Запусти установку

### Вариант А: Разовый запуск (для тестирования)

```bash
./start.sh
```

### Вариант Б: Установка как службы (рекомендуется)

```bash
# Сначала проверь работу бота
./start.sh

# Если всё работает, установи как службу
./install_service.sh
```

## Шаг 7: Проверь работу

### Если используешь service:

```bash
# Статус
sudo systemctl status hh_bot

# Логи в реальном времени
sudo journalctl -u hh_bot -f

# или
tail -f ~/hh_bot/bot.log
```

### Если запустил через start.sh:

Бот работает в текущей сессии. Логи будут в консоли.

## 🔄 Управление через Telegram

1. Найди своего бота в Telegram (имя которое дал @BotFather)
2. Отправь `/start`
3. Используй кнопки для управления:
   - ▶️ Запустить поиск
   - ⏸ Остановить поиск
   - 📊 Статистика
   - 🔄 Обновить из GitHub
   - И другие...

## 🔄 Обновление бота

### Через Telegram:
Нажми кнопку "🔄 Обновить из GitHub" в боте

### Через SSH:

```bash
cd ~/hh_bot
git pull origin main

# Если используешь service:
sudo systemctl restart hh_bot

# Если запускал через start.sh:
# Останови бота (Ctrl+C) и запусти заново
./start.sh
```

## 📋 Полезные команды

### Управление службой:
```bash
sudo systemctl status hh_bot    # Статус
sudo systemctl start hh_bot     # Запустить
sudo systemctl stop hh_bot      # Остановить
sudo systemctl restart hh_bot   # Перезапустить
sudo systemctl disable hh_bot   # Отключить автозапуск
sudo systemctl enable hh_bot    # Включить автозапуск
```

### Логи:
```bash
# Логи systemd
sudo journalctl -u hh_bot -f

# Логи файла
tail -f ~/hh_bot/bot.log

# Последние 100 строк
tail -n 100 ~/hh_bot/bot.log
```

### Очистка:
```bash
# Очистить логи
> ~/hh_bot/bot.log

# Очистить состояние бота
rm ~/hh_bot/bot_state.json
```

## 🆘 Решение проблем

### Бот не запускается:
```bash
# Проверь логи
sudo journalctl -u hh_bot -n 50

# Проверь .env файл
cat ~/hh_bot/.env

# Проверь зависимости
cd ~/hh_bot
source venv/bin/activate
pip install -r requirements.txt
```

### Бот не отвечает в Telegram:
- Проверь токен бота в .env
- Убедись что бот запущен: `sudo systemctl status hh_bot`
- Проверь, что указал ALLOWED_USER_ID в .env

### Порты заняты:
Бот работает через Telegram API, порты не нужны!

## ⚠️ Важно!

1. **Смени API ключи после настройки!**
   - Регенерируй Telegram токен у @BotFather
   - Создай новый OpenAI API ключ

2. **OAuth для HeadHunter**
   Для автоматических откликов нужна OAuth авторизация на hh.ru
   Документация: https://github.com/hhru/api

3. **Безопасность**
   - Никому не давай доступ к .env файлу
   - Не публикуй токены в открытом доступе

## 🎯 Что дальше?

1. Протестируй бота через `/start` в Telegram
2. Настрой параметры поиска в .env
3. Запусти поиск через кнопку "▶️ Запустить поиск"
4. Следи за статистикой через бота

Удачи в поиске работы! 🚀
