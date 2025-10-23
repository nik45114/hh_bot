import asyncio
import json
import logging
import os
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler
)

import config
from hh_client import HeadHunterClient, format_vacancy_info
from cover_letter_generator import CoverLetterGenerator
from storage.database import Database
from prompts import get_default_prompt
from resume_data import RESUME_DATA

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Conversation states
WAITING_FOR_KEYWORDS = 1
WAITING_FOR_CITY = 2
WAITING_FOR_SALARY = 3
WAITING_FOR_PROMPT = 4

# Vacancy action prefix
VACANCY_PREFIX = "vac_"

# Areas mapping (популярные города)
POPULAR_AREAS = {
    'Москва': 1,
    'Санкт-Петербург': 2,
    'Россия': 113,
    'Екатеринбург': 3,
    'Новосибирск': 4,
    'Казань': 88,
    'Нижний Новгород': 66
}

# Role levels for Management
ROLE_LEVELS = [
    'Руководитель',
    'Project Manager',
    'Program Manager', 
    'Product Manager',
    'Team Lead',
    'Директор',
    'Head of',
    'CTO/CIO'
]


class JobBot:
    """Telegram бот для автоматизации откликов на hh.ru"""
    
    def __init__(self):
        self.hh_client = HeadHunterClient(
            config.HH_EMAIL, 
            config.HH_PASSWORD,
            config.HH_ACCESS_TOKEN
        )
        self.cover_letter_gen = CoverLetterGenerator(config.OPENAI_API_KEY) if config.OPENAI_API_KEY else None
        self.db = Database(config.DATABASE_FILE)
        
        # Active search tasks per user
        self.active_searches = {}
        
        # Temporary storage for current vacancies per user
        self.current_vacancies = {}
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user_id = update.effective_user.id
        username = update.effective_user.username
        
        if config.ALLOWED_USER_ID and str(user_id) != config.ALLOWED_USER_ID:
            await update.message.reply_text("❌ У вас нет доступа к этому боту.")
            return
        
        self.db.get_or_create_user(user_id, username)
        await self.show_main_menu(update.message)
    
    async def show_main_menu(self, message, edit=False):
        """Показать главное меню"""
        chat_id = message.chat_id if hasattr(message, 'chat_id') else message.chat.id
        prefs = self.db.get_preferences(chat_id)
        auto_apply_status = "✅ Вкл" if prefs.get('auto_apply') else "❌ Выкл"
        
        keyboard = [
            [InlineKeyboardButton("🔍 Поиск вакансий", callback_data='main_search')],
            [InlineKeyboardButton("⚙️ Настроить критерии", callback_data='main_criteria')],
            [InlineKeyboardButton("✍️ Промпт сопровода", callback_data='main_prompt')],
            [InlineKeyboardButton(f"🤖 Авто-отклик: {auto_apply_status}", callback_data='main_autoapply')],
            [InlineKeyboardButton("📊 Статистика", callback_data='main_stats')],
            [InlineKeyboardButton("ℹ️ Помощь", callback_data='main_help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = """
🤖 <b>HH Job Bot - Автоматизация поиска вакансий</b>

<b>Возможности:</b>
✅ Поиск вакансий по критериям (IT/Управление, удалёнка)
✅ Генерация сопроводительных писем с AI  
✅ Автоматические отклики на вакансии
✅ Гибкая настройка критериев поиска
✅ Управление промтами для сопровода

Выберите действие в меню ниже 👇
"""
        
        if edit:
            await message.edit_text(welcome_text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            await message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if config.ALLOWED_USER_ID and str(user_id) != config.ALLOWED_USER_ID:
            await query.edit_message_text("❌ У вас нет доступа к этому боту.")
            return
        
        action = query.data
        
        # Main menu actions
        if action == 'main_search':
            await self.handle_search_menu(query)
        elif action == 'main_criteria':
            await self.handle_criteria_menu(query)
        elif action == 'main_prompt':
            await self.handle_prompt_menu(query)
        elif action == 'main_autoapply':
            await self.toggle_auto_apply(query)
        elif action == 'main_stats':
            await self.show_stats(query)
        elif action == 'main_help':
            await self.show_help(query)
        elif action == 'back_to_menu':
            await self.show_main_menu(query.message, edit=True)
        
        # Criteria actions
        elif action.startswith('criteria_'):
            await self.handle_criteria_action(query, action, context)
        
        # Search actions
        elif action.startswith('search_'):
            await self.handle_search_action(query, action)
        
        # Prompt actions
        elif action.startswith('prompt_'):
            await self.handle_prompt_action(query, action, context)
        
        # Vacancy actions
        elif action.startswith(VACANCY_PREFIX):
            await self.handle_vacancy_action(query, action, context)
    
    # === CRITERIA MANAGEMENT ===
    
    async def handle_criteria_menu(self, query):
        """Меню настройки критериев поиска"""
        prefs = self.db.get_preferences(query.message.chat_id)
        
        domain_emoji = "💼" if prefs.get('role_domain') == 'Management' else "💻"
        remote_emoji = "✅" if prefs.get('remote_only') else "❌"
        
        criteria_text = f"""
⚙️ <b>Настройки критериев поиска</b>

{domain_emoji} <b>Сфера:</b> {prefs.get('role_domain', 'IT')}
🌍 <b>Город:</b> {prefs.get('city', 'Москва')}
🏠 <b>Только удалёнка:</b> {remote_emoji}
📝 <b>Ключевые слова:</b> {', '.join(prefs.get('keywords', [])) or 'не заданы'}
💰 <b>Зарплата от:</b> {prefs.get('salary_min', 0)} руб.
👔 <b>Уровень:</b> {prefs.get('role_level') or 'не задан'}
"""
        
        keyboard = [
            [InlineKeyboardButton("💼/💻 Изменить сферу", callback_data='criteria_domain')],
            [InlineKeyboardButton("🌍 Изменить город", callback_data='criteria_city')],
            [InlineKeyboardButton("🏠 Только удалёнка вкл/выкл", callback_data='criteria_remote')],
            [InlineKeyboardButton("📝 Ключевые слова", callback_data='criteria_keywords')],
            [InlineKeyboardButton("💰 Минимальная зарплата", callback_data='criteria_salary')],
            [InlineKeyboardButton("👔 Уровень/роль", callback_data='criteria_level')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(criteria_text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def handle_criteria_action(self, query, action, context):
        """Обработка действий с критериями"""
        chat_id = query.message.chat_id
        
        if action == 'criteria_domain':
            keyboard = [
                [InlineKeyboardButton("💻 IT", callback_data='set_domain_IT')],
                [InlineKeyboardButton("💼 Управление", callback_data='set_domain_Management')],
                [InlineKeyboardButton("🔧 Другое", callback_data='set_domain_Other')],
                [InlineKeyboardButton("🔙 Назад", callback_data='main_criteria')]
            ]
            await query.edit_message_text(
                "Выберите сферу деятельности:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif action.startswith('set_domain_'):
            domain = action.replace('set_domain_', '')
            self.db.update_preferences(chat_id, role_domain=domain)
            await query.answer(f"Сфера изменена на: {domain}")
            await self.handle_criteria_menu(query)
        
        elif action == 'criteria_remote':
            prefs = self.db.get_preferences(chat_id)
            new_value = not prefs.get('remote_only', False)
            self.db.update_preferences(chat_id, remote_only=new_value, schedule='remote' if new_value else 'fullDay')
            status = "включена" if new_value else "выключена"
            await query.answer(f"Только удалённая работа: {status}")
            await self.handle_criteria_menu(query)
        
        elif action == 'criteria_city':
            keyboard = []
            for city, area_id in POPULAR_AREAS.items():
                keyboard.append([InlineKeyboardButton(city, callback_data=f'set_city_{area_id}_{city}')])
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='main_criteria')])
            
            await query.edit_message_text(
                "Выберите город:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif action.startswith('set_city_'):
            parts = action.replace('set_city_', '').split('_', 1)
            area_id = int(parts[0])
            city = parts[1]
            self.db.update_preferences(chat_id, city=city, area_id=area_id)
            await query.answer(f"Город изменён на: {city}")
            await self.handle_criteria_menu(query)
        
        elif action == 'criteria_level':
            keyboard = []
            for level in ROLE_LEVELS:
                keyboard.append([InlineKeyboardButton(level, callback_data=f'set_level_{level}')])
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='main_criteria')])
            
            await query.edit_message_text(
                "Выберите уровень/роль:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif action.startswith('set_level_'):
            level = action.replace('set_level_', '')
            self.db.update_preferences(chat_id, role_level=level)
            await query.answer(f"Уровень изменён на: {level}")
            await self.handle_criteria_menu(query)
        
        elif action == 'criteria_keywords':
            await query.edit_message_text(
                "Введите ключевые слова через запятую.\n\n"
                "Например: Python, Django, API\n"
                "или: Руководитель, Менеджер проектов\n\n"
                "Для отмены отправьте /cancel"
            )
            context.user_data['waiting_for'] = 'keywords'
            
        elif action == 'criteria_salary':
            await query.edit_message_text(
                "Введите минимальную желаемую зарплату (в рублях).\n\n"
                "Например: 150000\n\n"
                "Для отмены отправьте /cancel"
            )
            context.user_data['waiting_for'] = 'salary'
    
    # === PROMPT MANAGEMENT ===
    
    async def handle_prompt_menu(self, query):
        """Меню управления промптами"""
        prefs = self.db.get_preferences(query.message.chat_id)
        custom_prompt = prefs.get('prompt')
        default_prompt = get_default_prompt(prefs.get('role_domain', 'IT'))
        
        if custom_prompt:
            prompt_preview = custom_prompt[:200] + "..." if len(custom_prompt) > 200 else custom_prompt
            status = "✅ Используется пользовательский промпт"
        else:
            prompt_preview = default_prompt[:200] + "..." if len(default_prompt) > 200 else default_prompt
            status = "📝 Используется стандартный промпт"
        
        text = f"""
✍️ <b>Управление промптом</b>

{status}

<b>Текущий промпт:</b>
<code>{prompt_preview}</code>

Промпт используется для генерации сопроводительных писем с помощью AI.
"""
        
        keyboard = [
            [InlineKeyboardButton("✏️ Изменить промпт", callback_data='prompt_edit')],
            [InlineKeyboardButton("🔄 Сбросить по умолчанию", callback_data='prompt_reset')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    
    async def handle_prompt_action(self, query, action, context):
        """Обработка действий с промптами"""
        if action == 'prompt_reset':
            self.db.update_preferences(query.message.chat_id, prompt=None)
            await query.answer("Промпт сброшен к значению по умолчанию")
            await self.handle_prompt_menu(query)
        elif action == 'prompt_edit':
            await query.edit_message_text(
                "Отправьте новый текст промпта для генерации сопроводительных писем.\n\n"
                "Можете использовать плейсхолдеры:\n"
                "• {vacancy_title} - название вакансии\n"
                "• {company_name} - название компании\n"
                "• {user_name} - ваше имя\n"
                "• {skills} - ваши навыки\n\n"
                "Для отмены отправьте /cancel"
            )
            context.user_data['waiting_for'] = 'prompt'
    
    # === SEARCH AND VACANCY HANDLING ===
    
    async def handle_search_menu(self, query):
        """Меню поиска вакансий"""
        prefs = self.db.get_preferences(query.message.chat_id)
        
        search_text = f"""
🔍 <b>Поиск вакансий</b>

<b>Текущие критерии:</b>
• Сфера: {prefs.get('role_domain', 'IT')}
• Город: {prefs.get('city', 'Москва')}
• Удалёнка: {'Да' if prefs.get('remote_only') else 'Любой формат'}
• Ключевые слова: {', '.join(prefs.get('keywords', [])) or 'не заданы'}
• Зарплата от: {prefs.get('salary_min', 0)} руб.

Выберите действие:
"""
        
        keyboard = [
            [InlineKeyboardButton("🔍 Найти вакансии сейчас", callback_data='search_now')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')]
        ]
        
        await query.edit_message_text(search_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    
    async def handle_search_action(self, query, action):
        """Обработка действий поиска"""
        if action == 'search_now':
            await query.edit_message_text("🔍 Ищу вакансии... Пожалуйста, подождите.")
            await self.perform_search(query.message.chat_id, query.message)
    
    async def perform_search(self, chat_id: int, message):
        """Выполнить поиск вакансий"""
        try:
            prefs = self.db.get_preferences(chat_id)
            
            # Build search parameters
            keywords = prefs.get('keywords', [])
            search_text = ' '.join(keywords) if keywords else prefs.get('role_level', '')
            
            if not search_text and prefs.get('role_domain') == 'Management':
                search_text = 'руководитель менеджер'
            elif not search_text:
                search_text = 'python developer'
            
            # Search vacancies
            vacancies = self.hh_client.search_vacancies(
                text=search_text,
                area=prefs.get('area_id', 1),
                schedule=prefs.get('schedule', 'remote') if prefs.get('remote_only') else None,
                experience=prefs.get('experience', 'between3And6'),
                employment=prefs.get('employment', 'full'),
                salary=prefs.get('salary_min', 0) if prefs.get('salary_min') > 0 else None,
                per_page=10
            )
            
            if not vacancies:
                await message.reply_text(
                    "😔 Вакансии не найдены по заданным критериям.\n\n"
                    "Попробуйте изменить критерии поиска в настройках."
                )
                return
            
            # Filter already processed
            new_vacancies = [v for v in vacancies if not self.db.is_vacancy_processed(chat_id, v['id'])]
            
            if not new_vacancies:
                await message.reply_text(
                    f"✅ Найдено {len(vacancies)} вакансий, но все уже были обработаны ранее."
                )
                return
            
            # Store vacancies for this user
            self.current_vacancies[chat_id] = new_vacancies
            
            await message.reply_text(
                f"🎯 Найдено {len(new_vacancies)} новых вакансий!\n"
                f"Начинаю показ..."
            )
            
            # Show vacancies one by one
            for i, vacancy in enumerate(new_vacancies, 1):
                await self.show_vacancy_card(chat_id, vacancy, i, len(new_vacancies), message)
                await asyncio.sleep(1)  # Small delay between messages
            
        except Exception as e:
            logger.error(f"Ошибка при поиске вакансий: {e}")
            await message.reply_text(
                f"❌ Произошла ошибка при поиске вакансий: {str(e)}"
            )
    
    async def show_vacancy_card(self, chat_id: int, vacancy: Dict, position: int, total: int, message):
        """Показать карточку вакансии с кнопками действий"""
        vacancy_text = format_vacancy_info(vacancy)
        header = f"📋 Вакансия {position} из {total}\n\n"
        
        # Check auto-apply setting
        prefs = self.db.get_preferences(chat_id)
        auto_apply = prefs.get('auto_apply', False)
        
        if auto_apply:
            # Auto-apply mode - apply automatically
            result = await self.apply_to_vacancy(chat_id, vacancy)
            status_icon = "✅" if result.get('success') else "❌"
            await message.reply_text(
                f"{header}{vacancy_text}\n\n"
                f"{status_icon} <b>Авто-отклик:</b> {result.get('message')}",
                parse_mode='HTML'
            )
        else:
            # Manual mode - show buttons
            vacancy_id = vacancy['id']
            keyboard = [
                [InlineKeyboardButton("✅ Откликнуться", callback_data=f"{VACANCY_PREFIX}apply_{vacancy_id}")],
                [InlineKeyboardButton("❌ Пропустить", callback_data=f"{VACANCY_PREFIX}skip_{vacancy_id}")],
                [InlineKeyboardButton("🔗 Открыть на сайте", url=vacancy.get('alternate_url', ''))]
            ]
            
            await message.reply_text(
                f"{header}{vacancy_text}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
    
    async def handle_vacancy_action(self, query, action, context):
        """Обработка действий с вакансией"""
        chat_id = query.message.chat_id
        vacancy_id = action.split('_')[-1]
        
        if action.startswith(f"{VACANCY_PREFIX}apply_"):
            # Find vacancy in current vacancies
            vacancies = self.current_vacancies.get(chat_id, [])
            vacancy = next((v for v in vacancies if v['id'] == vacancy_id), None)
            
            if not vacancy:
                await query.answer("Вакансия не найдена")
                return
            
            await query.edit_message_text(f"{query.message.text}\n\n⏳ Подготавливаю отклик...")
            
            result = await self.apply_to_vacancy(chat_id, vacancy)
            
            status_icon = "✅" if result.get('success') else "❌"
            await query.edit_message_text(
                f"{query.message.text}\n\n"
                f"{status_icon} <b>Отклик:</b> {result.get('message')}",
                parse_mode='HTML'
            )
            
        elif action.startswith(f"{VACANCY_PREFIX}skip_"):
            self.db.mark_vacancy_processed(chat_id, vacancy_id)
            await query.edit_message_text(
                f"{query.message.text}\n\n"
                f"⏭ Вакансия пропущена",
                parse_mode='HTML'
            )
    
    async def apply_to_vacancy(self, chat_id: int, vacancy: Dict) -> Dict:
        """Откликнуться на вакансию"""
        try:
            vacancy_id = vacancy['id']
            prefs = self.db.get_preferences(chat_id)
            
            # Check if HH token and resume are configured
            if not config.HH_ACCESS_TOKEN:
                return {
                    'success': False,
                    'message': 'Не настроен токен доступа HH.ru. См. /help для инструкций.'
                }
            
            if not config.HH_RESUME_ID:
                return {
                    'success': False,
                    'message': 'Не указан ID резюме. См. /help для инструкций.'
                }
            
            # Get vacancy details
            details = self.hh_client.get_vacancy_details(vacancy_id)
            if not details:
                return {
                    'success': False,
                    'message': 'Не удалось получить детали вакансии'
                }
            
            # Generate cover letter
            if self.cover_letter_gen:
                cover_letter = self.cover_letter_gen.generate_cover_letter(
                    job_title=details.get('name', ''),
                    company_name=details.get('employer', {}).get('name', ''),
                    job_description=details.get('description', ''),
                    custom_prompt=prefs.get('prompt'),
                    role_domain=prefs.get('role_domain', 'IT'),
                    schedule=details.get('schedule', {}).get('id'),
                    location=details.get('area', {}).get('name')
                )
            else:
                cover_letter = f"Здравствуйте! Меня заинтересовала вакансия {details.get('name', '')}. {RESUME_DATA['summary']}"
            
            if not cover_letter:
                cover_letter = f"Здравствуйте! Заинтересован в вакансии {details.get('name', '')}."
            
            # Apply to vacancy
            result = self.hh_client.apply_to_vacancy(
                vacancy_id=vacancy_id,
                resume_id=config.HH_RESUME_ID,
                cover_letter=cover_letter
            )
            
            # Log application
            status = 'success' if result.get('success') else 'failed'
            self.db.log_application(
                chat_id=chat_id,
                vacancy_id=vacancy_id,
                vacancy_title=details.get('name', ''),
                company_name=details.get('employer', {}).get('name', ''),
                cover_letter=cover_letter,
                status=status,
                error_message=None if result.get('success') else result.get('message')
            )
            
            # Mark as processed
            self.db.mark_vacancy_processed(chat_id, vacancy_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при отклике на вакансию: {e}")
            return {
                'success': False,
                'message': f'Произошла ошибка: {str(e)}'
            }
    
    # === STATS AND INFO ===
    
    async def show_stats(self, query):
        """Показать статистику"""
        chat_id = query.message.chat_id
        
        # Get today's applications
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = self.db.get_applications_count(chat_id, since=today)
        total_count = self.db.get_applications_count(chat_id)
        
        # Get recent applications
        recent = self.db.get_recent_applications(chat_id, limit=5)
        
        stats_text = f"""
📊 <b>Статистика</b>

📝 Откликов сегодня: {today_count}
📈 Всего откликов: {total_count}

<b>Последние отклики:</b>
"""
        
        if recent:
            for app in recent:
                status_icon = "✅" if app['status'] == 'success' else "❌"
                date = app['applied_at'][:10] if app['applied_at'] else "дата неизвестна"
                stats_text += f"\n{status_icon} {app['vacancy_title']} - {date}"
        else:
            stats_text += "\nПока нет откликов"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')]]
        
        await query.edit_message_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    
    async def toggle_auto_apply(self, query):
        """Переключить режим авто-отклика"""
        chat_id = query.message.chat_id
        prefs = self.db.get_preferences(chat_id)
        
        new_value = not prefs.get('auto_apply', False)
        self.db.update_preferences(chat_id, auto_apply=new_value)
        
        status = "включён" if new_value else "выключен"
        await query.answer(f"Авто-отклик {status}")
        await self.show_main_menu(query.message, edit=True)
    
    async def show_help(self, query):
        """Показать справку"""
        help_text = """
ℹ️ <b>Справка</b>

<b>Команды бота:</b>
/start - Главное меню
/criteria - Настроить критерии поиска
/search - Запустить поиск вакансий
/prompt - Управление промптом
/apply_on - Включить авто-отклик
/apply_off - Выключить авто-отклик
/stats - Статистика откликов
/help - Эта справка

<b>Как работает бот:</b>
1️⃣ Настройте критерии поиска (сфера, город, удалёнка, зарплата)
2️⃣ При необходимости настройте промпт для сопроводительных писем
3️⃣ Запустите поиск вакансий
4️⃣ Бот найдёт вакансии и предложит откликнуться
5️⃣ В режиме авто-отклика бот откликается автоматически

<b>⚙️ Настройка HH.ru API:</b>

Для автоматических откликов нужны:
• HH_ACCESS_TOKEN - OAuth токен доступа
• HH_RESUME_ID - ID вашего резюме

<b>Как получить токен:</b>
1. Зарегистрируйте приложение на https://dev.hh.ru/admin
2. Получите Client ID и Client Secret
3. Пройдите OAuth авторизацию
4. Получите access_token

<b>Как узнать ID резюме:</b>
Через API запрос GET https://api.hh.ru/resumes/mine
с заголовком Authorization: Bearer YOUR_TOKEN

Подробнее: https://github.com/hhru/api

<b>Переменные окружения (.env):</b>
• TELEGRAM_BOT_TOKEN - токен Telegram бота
• OPENAI_API_KEY - ключ OpenAI для генерации писем
• HH_ACCESS_TOKEN - токен доступа к HH API
• HH_RESUME_ID - ID резюме

Пример: см. файл .env.example
"""
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')]]
        
        await query.edit_message_text(
            help_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    
    # === ADDITIONAL COMMANDS ===
    
    async def criteria_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /criteria"""
        query = Update(update_id=0, callback_query=update.callback_query)
        query.callback_query = type('obj', (object,), {
            'message': update.message,
            'from_user': update.effective_user,
            'answer': lambda: asyncio.sleep(0),
            'edit_message_text': update.message.edit_text if hasattr(update.message, 'edit_text') else update.message.reply_text
        })()
        await self.handle_criteria_menu(query.callback_query)
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /search"""
        chat_id = update.effective_user.id
        await update.message.reply_text("🔍 Начинаю поиск вакансий...")
        await self.perform_search(chat_id, update.message)
    
    async def prompt_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /prompt"""
        query = Update(update_id=0, callback_query=update.callback_query)
        query.callback_query = type('obj', (object,), {
            'message': update.message,
            'from_user': update.effective_user,
            'answer': lambda: asyncio.sleep(0),
            'edit_message_text': update.message.edit_text if hasattr(update.message, 'edit_text') else update.message.reply_text
        })()
        await self.handle_prompt_menu(query.callback_query)
    
    async def apply_on_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /apply_on"""
        self.db.update_preferences(update.effective_user.id, auto_apply=True)
        await update.message.reply_text("✅ Авто-отклик включён")
    
    async def apply_off_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /apply_off"""
        self.db.update_preferences(update.effective_user.id, auto_apply=False)
        await update.message.reply_text("❌ Авто-отклик выключен")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats"""
        query = Update(update_id=0, callback_query=update.callback_query)
        query.callback_query = type('obj', (object,), {
            'message': update.message,
            'from_user': update.effective_user,
            'answer': lambda: asyncio.sleep(0),
            'edit_message_text': update.message.edit_text if hasattr(update.message, 'edit_text') else update.message.reply_text
        })()
        await self.show_stats(query.callback_query)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        query = Update(update_id=0, callback_query=update.callback_query)
        query.callback_query = type('obj', (object,), {
            'message': update.message,
            'from_user': update.effective_user,
            'answer': lambda: asyncio.sleep(0),
            'edit_message_text': update.message.edit_text if hasattr(update.message, 'edit_text') else update.message.reply_text
        })()
        await self.show_help(query.callback_query)
    
    # === TEXT MESSAGE HANDLERS ===
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений (для ввода данных)"""
        chat_id = update.effective_user.id
        text = update.message.text
        
        waiting_for = context.user_data.get('waiting_for')
        
        if waiting_for == 'keywords':
            keywords = [kw.strip() for kw in text.split(',')]
            self.db.update_preferences(chat_id, keywords=keywords)
            await update.message.reply_text(
                f"✅ Ключевые слова обновлены: {', '.join(keywords)}"
            )
            context.user_data.pop('waiting_for', None)
            
        elif waiting_for == 'salary':
            try:
                salary = int(text)
                self.db.update_preferences(chat_id, salary_min=salary)
                await update.message.reply_text(
                    f"✅ Минимальная зарплата установлена: {salary:,} руб."
                )
            except ValueError:
                await update.message.reply_text(
                    "❌ Некорректное значение. Введите число."
                )
            context.user_data.pop('waiting_for', None)
            
        elif waiting_for == 'prompt':
            self.db.update_preferences(chat_id, prompt=text)
            await update.message.reply_text(
                "✅ Промпт обновлён!\n\n"
                f"Первые 200 символов: {text[:200]}..."
            )
            context.user_data.pop('waiting_for', None)
    
    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /cancel"""
        context.user_data.pop('waiting_for', None)
        await update.message.reply_text("❌ Операция отменена")


def main():
    """Запуск бота"""
    # Проверка наличия токенов
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("Не указан TELEGRAM_BOT_TOKEN в .env файле!")
        return
    
    if not config.OPENAI_API_KEY:
        logger.warning("Не указан OPENAI_API_KEY - генерация писем будет недоступна")
    
    if not config.HH_ACCESS_TOKEN:
        logger.warning("Не указан HH_ACCESS_TOKEN - отклики будут недоступны")
    
    if not config.HH_RESUME_ID:
        logger.warning("Не указан HH_RESUME_ID - отклики будут недоступны")
    
    # Создаем экземпляр бота
    job_bot = JobBot()
    
    # Создаем приложение Telegram
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", job_bot.start_command))
    application.add_handler(CommandHandler("criteria", job_bot.criteria_command))
    application.add_handler(CommandHandler("search", job_bot.search_command))
    application.add_handler(CommandHandler("prompt", job_bot.prompt_command))
    application.add_handler(CommandHandler("apply_on", job_bot.apply_on_command))
    application.add_handler(CommandHandler("apply_off", job_bot.apply_off_command))
    application.add_handler(CommandHandler("stats", job_bot.stats_command))
    application.add_handler(CommandHandler("help", job_bot.help_command))
    application.add_handler(CommandHandler("cancel", job_bot.cancel_command))
    
    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(job_bot.button_callback))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, job_bot.handle_text_message))
    
    # Запускаем бота
    logger.info("Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
