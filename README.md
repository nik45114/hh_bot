# 🤖 HH Job Bot

Telegram-бот для автоматизации откликов на вакансии с HeadHunter.ru

## 📋 Возможности

- 🔍 **Автоматический поиск вакансий** по ключевым словам
- 🤖 **AI-генерация сопроводительных писем** с помощью OpenAI GPT
- 📊 **Статистика и контроль** процесса через Telegram
- ⚙️ **Гибкая настройка** параметров поиска
- 🔄 **Автообновление** из GitHub репозитория
- 🎮 **Удобное управление** через кнопки в Telegram

## 🚀 Быстрый старт

### 1. Клонирование репозитория

```bash
git clone https://github.com/nik45114/hh_bot.git
cd hh_bot
```

### 2. Установка зависимостей

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 3. Настройка окружения

Создай файл `.env` на основе `.env.example`:

```bash
cp .env.example .env
```

Заполни `.env` своими данными:

```env
# Telegram Bot Token (получи у @BotFather)
TELEGRAM_BOT_TOKEN=your_bot_token

# OpenAI API Key
OPENAI_API_KEY=your_openai_key

# Твой Telegram User ID (получи у @userinfobot)
ALLOWED_USER_ID=your_user_id

# Настройки поиска
SEARCH_KEYWORDS=Python developer, Backend developer
SEARCH_INTERVAL_MINUTES=60
MAX_APPLICATIONS_PER_DAY=20
```

### 4. Заполни данные резюме

Отредактируй файл `resume_data.py` и укажи свои данные:
- Имя и позиция
- Опыт работы
- Навыки
- Образование
- Мотивация

### 5. Запуск бота

```bash
python bot.py
```

## 📱 Использование

1. Найди своего бота в Telegram и нажми `/start`
2. Используй кнопки для управления:
   - ▶️ **Запустить поиск** - начать автоматический поиск вакансий
   - ⏸ **Остановить поиск** - остановить процесс
   - 📊 **Статистика** - посмотреть статистику откликов
   - ⚙️ **Настройки** - просмотр текущих настроек
   - 🔄 **Обновить из GitHub** - обновить код бота
   - ℹ️ **Помощь** - справочная информация

## ⚙️ Настройка

### Параметры в .env

- `SEARCH_KEYWORDS` - ключевые слова для поиска (через запятую)
- `SEARCH_INTERVAL_MINUTES` - интервал между проверками (в минутах)
- `MAX_APPLICATIONS_PER_DAY` - максимум откликов в день

### Данные резюме

Файл `resume_data.py` содержит:
- Личные данные
- Опыт работы
- Навыки и достижения
- Шаблон для генерации писем

## 🔐 OAuth авторизация на HeadHunter

⚠️ **Важно:** Для автоматических откликов нужна OAuth авторизация.

Официальная документация API HeadHunter:
- https://github.com/hhru/api
- https://dev.hh.ru/

Для получения токена:
1. Зарегистрируй приложение на https://dev.hh.ru/
2. Получи `client_id` и `client_secret`
3. Реализуй OAuth 2.0 flow для получения `access_token`

## 🛠 Автообновление через SSH

### Настройка автозапуска

Создай systemd service:

```bash
sudo nano /etc/systemd/system/hh_bot.service
```

```ini
[Unit]
Description=HH Job Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/hh_bot
Environment="PATH=/path/to/hh_bot/venv/bin"
ExecStart=/path/to/hh_bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Включи и запусти service:

```bash
sudo systemctl enable hh_bot
sudo systemctl start hh_bot
sudo systemctl status hh_bot
```

### Просмотр логов

```bash
sudo journalctl -u hh_bot -f
# или
tail -f bot.log
```

## 📂 Структура проекта

```
hh_bot/
├── bot.py                      # Основной файл бота
├── hh_client.py                # Клиент для работы с HH API
├── cover_letter_generator.py   # Генератор сопроводительных писем
├── resume_data.py              # Данные резюме
├── config.py                   # Конфигурация
├── requirements.txt            # Зависимости
├── .env                        # Переменные окружения (не в git)
├── .env.example                # Шаблон переменных
├── .gitignore                  # Игнорируемые файлы
└── README.md                   # Документация
```

## 🔄 Обновление из GitHub

Через Telegram:
1. Нажми кнопку "🔄 Обновить из GitHub"
2. Бот выполнит `git pull`
3. Перезапусти бота для применения изменений

Через SSH:
```bash
cd /path/to/hh_bot
git pull origin main
sudo systemctl restart hh_bot
```

## 📊 Логирование

Бот ведет логи в:
- `bot.log` - общий лог работы
- `applications.log` - лог откликов
- stdout/stderr - для systemd

## ⚠️ Ограничения

1. **OAuth авторизация**: Для автоматических откликов нужен access token от HH
2. **Rate limiting**: HH API имеет ограничения на количество запросов
3. **OpenAI costs**: Генерация писем потребляет токены OpenAI API

## 🆘 Устранение неполадок

### Бот не отвечает
- Проверь, что токен бота правильный
- Убедись, что бот запущен: `sudo systemctl status hh_bot`
- Проверь логи: `tail -f bot.log`

### Не генерируются сопроводительные письма
- Проверь наличие OpenAI API ключа в `.env`
- Проверь баланс OpenAI аккаунта

### Не находятся вакансии
- Проверь ключевые слова в настройках
- Убедись, что HH API доступен

## 📝 TODO

- [ ] Реализация полной OAuth авторизации для HH
- [ ] Фильтрация вакансий по зарплате и навыкам
- [ ] Уведомления о новых откликах
- [ ] Веб-интерфейс для управления
- [ ] Поддержка нескольких резюме
- [ ] Интеграция с другими job-сайтами

## 🤝 Вклад в проект

Если хочешь улучшить бота:
1. Fork репозитория
2. Создай ветку для своих изменений
3. Отправь Pull Request

## 📄 Лицензия

MIT License

## ⚠️ Дисклеймер

Этот бот создан в образовательных целях. Используй его ответственно и в соответствии с правилами HeadHunter.ru.

---

**Автор**: [@nik45114](https://github.com/nik45114)

**GitHub**: https://github.com/nik45114/hh_bot
