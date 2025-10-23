# UX Flow Documentation

## User Interaction Flows

### Flow 1: Initial Setup and First Search

```
User: /start
Bot: 🤖 HH Job Bot - Main Menu
     [🔍 Поиск вакансий]
     [⚙️ Настроить критерии]
     [✍️ Промпт сопровода]
     [🤖 Авто-отклик: ❌ Выкл]
     [📊 Статистика]
     [ℹ️ Помощь]

User: Clicks "⚙️ Настроить критерии"
Bot: ⚙️ Настройки критериев поиска
     
     💻 Сфера: IT
     🌍 Город: Москва
     🏠 Только удалёнка: ❌
     📝 Ключевые слова: не заданы
     💰 Зарплата от: 0 руб.
     👔 Уровень: не задан
     
     [💼/💻 Изменить сферу]
     [🌍 Изменить город]
     [🏠 Только удалёнка вкл/выкл]
     [📝 Ключевые слова]
     [💰 Минимальная зарплата]
     [👔 Уровень/роль]
     [🔙 Назад]

User: Clicks "💼/💻 Изменить сферу"
Bot: Выберите сферу деятельности:
     [💻 IT]
     [💼 Управление]
     [🔧 Другое]
     [🔙 Назад]

User: Clicks "💼 Управление"
Bot: ⚙️ Настройки критериев поиска (updated)
     💼 Сфера: Management
     ...

User: Clicks "🏠 Только удалёнка вкл/выкл"
Bot: ✅ Только удалённая работа: включена
     (Updates menu with checkmark)

User: Clicks "📝 Ключевые слова"
Bot: Введите ключевые слова через запятую.
     
     Например: Python, Django, API
     или: Руководитель, Менеджер проектов
     
     Для отмены отправьте /cancel

User: Types "руководитель, проджект менеджер, product owner"
Bot: ✅ Ключевые слова обновлены: руководитель, проджект менеджер, product owner

User: Clicks "🔙 Назад" (returns to main menu)
User: Clicks "🔍 Поиск вакансий"
Bot: 🔍 Поиск вакансий
     
     Текущие критерии:
     • Сфера: Management
     • Город: Москва
     • Удалёнка: Да
     • Ключевые слова: руководитель, проджект менеджер
     • Зарплата от: 0 руб.
     
     [🔍 Найти вакансии сейчас]
     [🔙 Назад]

User: Clicks "🔍 Найти вакансии сейчас"
Bot: 🔍 Ищу вакансии... Пожалуйста, подождите.

Bot: 🎯 Найдено 5 новых вакансий!
     Начинаю показ...

Bot: 📋 Вакансия 1 из 5
     
     📋 Project Manager
     
     🏢 Компания: Tech Solutions Ltd
     💰 150,000 - 200,000 RUB
     🔗 https://hh.ru/vacancy/12345
     
     [✅ Откликнуться]
     [❌ Пропустить]
     [🔗 Открыть на сайте]

User: Clicks "✅ Откликнуться"
Bot: (Updates message)
     📋 Вакансия 1 из 5
     ...
     ⏳ Подготавливаю отклик...

Bot: (Updates message again)
     📋 Вакансия 1 из 5
     ...
     ✅ Отклик: Отклик успешно отправлен!

Bot: (Shows next vacancy)
     📋 Вакансия 2 из 5
     ...
```

### Flow 2: Prompt Customization

```
User: /prompt
Bot: ✍️ Управление промптом
     
     📝 Используется стандартный промпт
     
     Текущий промпт:
     На основе следующих данных о кандидате создай профессиональное...
     (shows first 200 chars)
     
     Промпт используется для генерации сопроводительных писем с помощью AI.
     
     [✏️ Изменить промпт]
     [🔄 Сбросить по умолчанию]
     [🔙 Назад]

User: Clicks "✏️ Изменить промпт"
Bot: Отправьте новый текст промпта для генерации сопроводительных писем.
     
     Можете использовать плейсхолдеры:
     • {vacancy_title} - название вакансии
     • {company_name} - название компании
     • {user_name} - ваше имя
     • {skills} - ваши навыки
     
     Для отмены отправьте /cancel

User: Sends multi-line custom prompt text
Bot: ✅ Промпт обновлён!
     
     Первые 200 символов: [preview]

User: /prompt (to check)
Bot: ✍️ Управление промптом
     
     ✅ Используется пользовательский промпт
     ...
```

### Flow 3: Auto-Apply Mode

```
User: /apply_on
Bot: ✅ Авто-отклик включён

User: /search
Bot: 🔍 Ищу вакансии... Пожалуйста, подождите.
Bot: 🎯 Найдено 5 новых вакансий!
     Начинаю показ...

Bot: 📋 Вакансия 1 из 5
     
     📋 Product Manager (Remote)
     🏢 Компания: Startup Inc
     💰 От 180,000 RUB
     🔗 https://hh.ru/vacancy/67890
     
     ✅ Авто-отклик: Отклик успешно отправлен!

Bot: 📋 Вакансия 2 из 5
     ...
     ✅ Авто-отклик: Отклик успешно отправлен!

Bot: 📋 Вакансия 3 из 5
     ...
     ❌ Авто-отклик: Превышен лимит запросов. Попробуйте позже.

(Continues through all vacancies)
```

### Flow 4: Statistics Review

```
User: /stats
Bot: 📊 Статистика
     
     📝 Откликов сегодня: 5
     📈 Всего откликов: 23
     
     Последние отклики:
     
     ✅ Product Manager - 2025-10-23
     ✅ Team Lead - 2025-10-23
     ✅ Project Manager - 2025-10-23
     ❌ Senior Manager - 2025-10-22
     ✅ Head of Product - 2025-10-22
     
     [🔙 Назад]
```

### Flow 5: Help and Setup

```
User: /help
Bot: ℹ️ Справка
     
     Команды бота:
     /start - Главное меню
     /criteria - Настроить критерии поиска
     /search - Запустить поиск вакансий
     /prompt - Управление промптом
     /apply_on - Включить авто-отклик
     /apply_off - Выключить авто-отклик
     /stats - Статистика откликов
     /help - Эта справка
     
     Как работает бот:
     1️⃣ Настройте критерии поиска...
     2️⃣ При необходимости настройте промпт...
     ...
     
     ⚙️ Настройка HH.ru API:
     
     Для автоматических откликов нужны:
     • HH_ACCESS_TOKEN - OAuth токен доступа
     • HH_RESUME_ID - ID вашего резюме
     
     Как получить токен:
     1. Зарегистрируйте приложение на https://dev.hh.ru/admin
     2. Получите Client ID и Client Secret
     ...
     
     [🔙 Назад]
```

### Flow 6: Error Handling Examples

#### No Token Configured
```
User: Tries to apply to vacancy
Bot: ❌ Отклик: Не настроен токен доступа HH.ru. См. /help для инструкций.
```

#### API Rate Limit
```
User: Searches for vacancies
Bot: (After several applications)
     ❌ Авто-отклик: Превышен лимит запросов. Попробуйте позже.
```

#### Invalid Salary Input
```
User: Types "сто тысяч" when asked for salary
Bot: ❌ Некорректное значение. Введите число.
```

#### Network Error
```
User: Searches for vacancies
Bot: 🔍 Ищу вакансии... Пожалуйста, подождите.
Bot: 😔 Вакансии не найдены по заданным критериям.
     
     Попробуйте изменить критерии поиска в настройках.
```

## Button States and Transitions

### Main Menu
- **Поиск вакансий** → Search Menu
- **Настроить критерии** → Criteria Menu
- **Промпт сопровода** → Prompt Menu
- **Авто-отклик** → Toggle state, refresh menu
- **Статистика** → Stats View
- **Помощь** → Help View

### Criteria Menu
- **Изменить сферу** → Domain Selection → Back to Criteria
- **Изменить город** → City Selection → Back to Criteria
- **Только удалёнка** → Toggle → Refresh Criteria Menu
- **Ключевые слова** → Text Input State → Confirmation → Criteria Menu
- **Минимальная зарплата** → Text Input State → Confirmation → Criteria Menu
- **Уровень/роль** → Level Selection → Back to Criteria
- **Назад** → Main Menu

### Search Flow
- **Найти вакансии сейчас** → Loading → Results Display
  - If auto_apply=False: Show cards with buttons
  - If auto_apply=True: Apply automatically, show results

### Vacancy Card (Manual Mode)
- **Откликнуться** → Loading → Success/Error Message
- **Пропустить** → Mark as processed, show "Пропущена"
- **Открыть на сайте** → Open HH.ru URL in browser

### Prompt Menu
- **Изменить промпт** → Text Input State → Confirmation → Prompt Menu
- **Сбросить по умолчанию** → Reset → Refresh Prompt Menu
- **Назад** → Main Menu

## Input States

The bot maintains user context for text input:

1. **WAITING_FOR_KEYWORDS**: User typing keywords
   - Accepts: Comma-separated text
   - Cancel: /cancel command
   - Result: Updates preferences, returns to menu

2. **WAITING_FOR_SALARY**: User typing salary
   - Accepts: Numeric value
   - Validation: Must be integer
   - Cancel: /cancel command
   - Result: Updates preferences, confirmation message

3. **WAITING_FOR_PROMPT**: User typing custom prompt
   - Accepts: Multi-line text
   - Cancel: /cancel command
   - Result: Saves prompt, shows preview

## Visual Indicators

- ✅ - Success, Enabled, Completed
- ❌ - Error, Disabled, Skipped
- 🔍 - Search in progress
- ⏳ - Loading/Processing
- 📊 - Statistics
- 💻 - IT Domain
- 💼 - Management Domain
- 🏠 - Remote work
- 🌍 - Location/City
- 💰 - Salary
- 📝 - Keywords/Text
- 👔 - Role/Level
- ℹ️ - Information/Help

## Accessibility Features

- Clear button labels in Russian
- Progress feedback for long operations
- Error messages with actionable suggestions
- Cancel option for all input flows
- Back button on every sub-menu
- Confirmation messages for all updates
- Preview of long text (first 200 chars)
- Numbered vacancy cards (1 of 5)
