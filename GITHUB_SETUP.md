# 📦 Инструкция по загрузке проекта в GitHub

## Шаг 1: Создай репозиторий на GitHub (если еще не создан)

1. Зайди на https://github.com
2. Нажми "New repository" (зеленая кнопка)
3. Назови репозиторий: `hh_bot`
4. Сделай его **Private** (для безопасности)
5. НЕ добавляй README, .gitignore или лицензию (они уже есть)
6. Нажми "Create repository"

## Шаг 2: Загрузи код в GitHub

### Вариант А: Через SSH (рекомендуется)

```bash
cd /home/claude/hh_bot

# Добавь GitHub репозиторий
git remote add origin git@github.com:nik45114/hh_bot.git

# Переименуй ветку в main (если нужно)
git branch -M main

# Загрузи код
git push -u origin main
```

### Вариант Б: Через HTTPS

```bash
cd /home/claude/hh_bot

# Добавь GitHub репозиторий
git remote add origin https://github.com/nik45114/hh_bot.git

# Переименуй ветку в main (если нужно)
git branch -M main

# Загрузи код (потребуется ввести логин и токен)
git push -u origin main
```

**Если GitHub запрашивает пароль:**
- Пароль больше не работает!
- Используй Personal Access Token
- Получи токен: GitHub → Settings → Developer settings → Personal access tokens → Generate new token
- Права: `repo` (полный доступ к репозиториям)

## Шаг 3: Проверь загрузку

Открой https://github.com/nik45114/hh_bot и убедись, что все файлы на месте.

## ⚠️ ВАЖНО: Безопасность!

Файл `.env` с реальными токенами **НЕ загружен** в GitHub (он в .gitignore)!

Но ты случайно оставил токены в публичном чате. Обязательно смени их:

### 1. Telegram Bot Token
```bash
# В Telegram найди @BotFather
# Отправь команду:
/revoke

# Затем отправь:
/newtoken

# Скопируй новый токен в .env
```

### 2. OpenAI API Key
1. Зайди на https://platform.openai.com/api-keys
2. Удали старый ключ
3. Создай новый
4. Обнови в .env

## 🔄 Обновление кода

После изменений:

```bash
cd ~/hh_bot

# Добавь изменения
git add .

# Сделай коммит
git commit -m "Описание изменений"

# Загрузи в GitHub
git push origin main
```

## 📥 Клонирование на другой сервер

На новом сервере:

```bash
# Клонируй репозиторий
git clone https://github.com/nik45114/hh_bot.git
cd hh_bot

# Создай .env файл (скопируй из .env.example)
cp .env.example .env
nano .env  # Заполни токены

# Запусти установку
./start.sh
```

## 🎯 Готово!

Теперь твой бот:
- ✅ Хранится в GitHub
- ✅ Можно обновлять через git pull
- ✅ Можно управлять через Telegram
- ✅ Может автообновляться по кнопке

Следующие шаги:
1. Смени все токены на новые
2. Настрой автозапуск через systemd
3. Заполни resume_data.py своими данными
4. Протестируй бота в Telegram
