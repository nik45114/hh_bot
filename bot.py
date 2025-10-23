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
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import git

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
            config.HH_ACCESS_TOKEN,
            config.HH_REFRESH_TOKEN,
            config.HH_USER_AGENT
        )
        self.cover_letter_gen = CoverLetterGenerator(config.OPENAI_API_KEY) if config.OPENAI_API_KEY else None
        self.db = Database(config.DATABASE_FILE)
        
        # Active search tasks per user
        self.active_searches = {}
        
        # Temporary storage for current vacancies per user
        self.current_vacancies = {}
        
        # Scheduler for 24/7 monitoring
        self.scheduler = AsyncIOScheduler()
        self.app = None  # Will be set when bot starts
        
        # Rate limiting
        self.last_hh_request = datetime.now() - timedelta(seconds=10)
    
    def set_application(self, app):
        """Set telegram application reference"""
        self.app = app
    
    def start_monitoring(self):
        """Start the monitoring scheduler"""
        if not self.scheduler.running:
            # Add job to check for new vacancies
            self.scheduler.add_job(
                self.check_all_users_vacancies,
                trigger=IntervalTrigger(seconds=config.HH_SEARCH_INTERVAL_SEC),
                id='vacancy_monitoring',
                replace_existing=True
            )
            self.scheduler.start()
            logger.info(f"Monitoring scheduler started with interval {config.HH_SEARCH_INTERVAL_SEC}s")
    
    async def check_all_users_vacancies(self):
        """Check for new vacancies for all users with monitoring enabled"""
        try:
            monitoring_users = self.db.get_all_monitoring_users()
            logger.info(f"Checking vacancies for {len(monitoring_users)} users with monitoring enabled")
            
            for chat_id in monitoring_users:
                try:
                    await self.check_user_vacancies(chat_id)
                    await asyncio.sleep(2)  # Small delay between users
                except Exception as e:
                    logger.error(f"Error checking vacancies for user {chat_id}: {e}")
        except Exception as e:
            logger.error(f"Error in check_all_users_vacancies: {e}")
    
    async def check_user_vacancies(self, chat_id: int):
        """Check for new vacancies for a specific user"""
        try:
            prefs = self.db.get_preferences(chat_id)
            
            # Build search parameters
            keywords = prefs.get('keywords', [])
            search_text = ' '.join(keywords) if keywords else prefs.get('role_level', '')
            
            if not search_text and prefs.get('role_domain') == 'Management':
                search_text = 'руководитель менеджер'
            elif not search_text:
                search_text = 'python developer'
            
            # Rate limiting
            await self._wait_for_rate_limit()
            
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
                return
            
            # Filter to only new vacancies
            new_vacancies = [v for v in vacancies if not self.db.is_vacancy_sent(chat_id, v['id'])]
            
            if not new_vacancies:
                return
            
            logger.info(f"Found {len(new_vacancies)} new vacancies for user {chat_id}")
            
            # Update last check time
            self.db.update_monitoring_state(chat_id, last_check=datetime.now())
            
            # Send vacancies to user
            for vacancy in new_vacancies:
                await self.send_monitored_vacancy(chat_id, vacancy)
                self.db.mark_vacancy_sent(chat_id, vacancy['id'])
                await asyncio.sleep(1)  # Delay between messages
                
        except Exception as e:
            logger.error(f"Error checking vacancies for user {chat_id}: {e}")
    
    async def send_monitored_vacancy(self, chat_id: int, vacancy: Dict):
        """Send a monitored vacancy to the user"""
        try:
            if not self.app:
                logger.error("App not initialized, cannot send message")
                return
            
            vacancy_text = format_vacancy_info(vacancy)
            prefs = self.db.get_preferences(chat_id)
            auto_apply = prefs.get('auto_apply', False)
            
            header = "🔔 <b>Новая вакансия найдена!</b>\n\n"
            
            if auto_apply:
                # Auto-apply mode
                result = await self.apply_to_vacancy(chat_id, vacancy)
                status_icon = "✅" if result.get('success') else "❌"
                message = (
                    f"{header}{vacancy_text}\n\n"
                    f"{status_icon} <b>Авто-отклик:</b> {result.get('message')}"
                )
                await self.app.bot.send_message(
                    chat_id=chat_id,
                    text=message,
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
                
                # Store vacancy for callback handling
                if chat_id not in self.current_vacancies:
                    self.current_vacancies[chat_id] = []
                self.current_vacancies[chat_id].append(vacancy)
                
                await self.app.bot.send_message(
                    chat_id=chat_id,
                    text=f"{header}{vacancy_text}",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
        except Exception as e:
            logger.error(f"Error sending monitored vacancy to {chat_id}: {e}")
    
    async def _wait_for_rate_limit(self):
        """Wait for rate limit if needed"""
        elapsed = (datetime.now() - self.last_hh_request).total_seconds()
        min_interval = 1.0 / config.HH_RATE_LIMIT_QPS
        
        if elapsed < min_interval:
            wait_time = min_interval - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        
        self.last_hh_request = datetime.now()
    
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
        monitoring_state = self.db.get_monitoring_state(chat_id)
        
        auto_apply_status = "✅ Вкл" if prefs.get('auto_apply') else "❌ Выкл"
        monitoring_status = "✅ Вкл" if monitoring_state.get('monitoring_enabled') else "❌ Выкл"
        
        keyboard = [
            [InlineKeyboardButton("🔍 Поиск вакансий", callback_data='main_search')],
            [InlineKeyboardButton("⚙️ Настроить критерии", callback_data='main_criteria')],
            [InlineKeyboardButton("✍️ Промпт сопровода", callback_data='main_prompt')],
            [InlineKeyboardButton(f"🤖 Авто-отклик: {auto_apply_status}", callback_data='main_autoapply')],
            [InlineKeyboardButton(f"📡 Мониторинг 24/7: {monitoring_status}", callback_data='main_monitoring')],
            [InlineKeyboardButton("📊 Статистика", callback_data='main_stats')],
            [InlineKeyboardButton("ℹ️ Помощь", callback_data='main_help')]
        ]
        
        # Add admin commands if user is admin
        user_id = chat_id
        if user_id in config.ADMIN_CHAT_IDS:
            keyboard.append([InlineKeyboardButton("⚙️ Админ", callback_data='main_admin')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = """
🤖 <b>HH Job Bot - Автоматизация поиска вакансий</b>

<b>Возможности:</b>
✅ Поиск вакансий по критериям (IT/Управление, удалёнка)
✅ Генерация сопроводительных писем с AI  
✅ Автоматические отклики на вакансии
✅ 24/7 мониторинг новых вакансий
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
        elif action == 'main_monitoring':
            await self.toggle_monitoring(query)
        elif action == 'main_stats':
            await self.show_stats(query)
        elif action == 'main_help':
            await self.show_help(query)
        elif action == 'main_admin':
            await self.show_admin_menu(query)
        elif action == 'back_to_menu':
            await self.show_main_menu(query.message, edit=True)
        
        # Criteria actions
        elif action.startswith('criteria_') or action.startswith('set_domain_') or action.startswith('set_level_') or action.startswith('set_city_'):
            await self.handle_criteria_action(query, action, context)
        
        # Search actions
        elif action.startswith('search_'):
            await self.handle_search_action(query, action)
        
        # Prompt actions
        elif action.startswith('prompt_'):
            await self.handle_prompt_action(query, action, context)
        
        # Admin actions
        elif action.startswith('admin_'):
            await self.handle_admin_action(query, action, context)
        
        # Vacancy actions
        elif action.startswith(VACANCY_PREFIX):
            await self.handle_vacancy_action(query, action, context)
    
    # === CRITERIA MANAGEMENT ===
    
    async def handle_criteria_menu(self, query):
        """Меню настройки критериев поиска"""
        prefs = self.db.get_preferences(query.message.chat_id)
        
        domain_emoji = "💼" if prefs.get('role_domain') == 'Management' else "💻"
        remote_emoji = "✅" if prefs.get('remote_only') else "❌"
        
        # Format roles display
        roles = prefs.get('roles', [])
        roles_display = ', '.join(roles) if roles else 'не заданы'
        
        criteria_text = f"""
⚙️ <b>Настройки критериев поиска</b>

{domain_emoji} <b>Сфера:</b> {prefs.get('role_domain', 'IT')}
🌍 <b>Город:</b> {prefs.get('city', 'Москва')}
🏠 <b>Только удалёнка:</b> {remote_emoji}
📝 <b>Ключевые слова:</b> {', '.join(prefs.get('keywords', [])) or 'не заданы'}
💰 <b>Зарплата от:</b> {prefs.get('salary_min', 0)} руб.
👔 <b>Роли:</b> {roles_display}
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
            prefs = self.db.get_preferences(chat_id)
            current_domain = prefs.get('role_domain', 'IT')
            
            keyboard = [
                [InlineKeyboardButton(
                    f"{'✅ ' if current_domain == 'IT' else '⬜️ '}💻 IT", 
                    callback_data='set_domain_IT'
                )],
                [InlineKeyboardButton(
                    f"{'✅ ' if current_domain == 'Management' else '⬜️ '}💼 Управление", 
                    callback_data='set_domain_Management'
                )],
                [InlineKeyboardButton(
                    f"{'✅ ' if current_domain == 'Other' else '⬜️ '}🔧 Другое", 
                    callback_data='set_domain_Other'
                )],
                [InlineKeyboardButton("🔙 Назад", callback_data='main_criteria')]
            ]
            await query.edit_message_text(
                "Выберите сферу деятельности:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            await query.answer()
        
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
            await query.answer()
        
        elif action.startswith('set_city_'):
            parts = action.replace('set_city_', '').split('_', 1)
            area_id = int(parts[0])
            city = parts[1]
            self.db.update_preferences(chat_id, city=city, area_id=area_id)
            await query.answer(f"Город изменён на: {city}")
            await self.handle_criteria_menu(query)
        
        elif action == 'criteria_level':
            prefs = self.db.get_preferences(chat_id)
            current_roles = prefs.get('roles', [])
            
            keyboard = []
            for level in ROLE_LEVELS:
                is_selected = level in current_roles
                checkbox = "✅" if is_selected else "⬜️"
                keyboard.append([InlineKeyboardButton(
                    f"{checkbox} {level}", 
                    callback_data=f'toggle_role_{level}'
                )])
            keyboard.append([InlineKeyboardButton("💾 Сохранить", callback_data='main_criteria')])
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='main_criteria')])
            
            await query.edit_message_text(
                "Выберите уровень/роль (можно выбрать несколько):",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            await query.answer()
        
        elif action.startswith('toggle_role_'):
            role = action.replace('toggle_role_', '')
            prefs = self.db.get_preferences(chat_id)
            current_roles = prefs.get('roles', [])
            
            # Toggle role selection
            if role in current_roles:
                current_roles.remove(role)
            else:
                current_roles.append(role)
            
            # Save to database
            self.db.update_preferences(chat_id, roles=current_roles)
            
            # Update display with new checkboxes
            keyboard = []
            for level in ROLE_LEVELS:
                is_selected = level in current_roles
                checkbox = "✅" if is_selected else "⬜️"
                keyboard.append([InlineKeyboardButton(
                    f"{checkbox} {level}", 
                    callback_data=f'toggle_role_{level}'
                )])
            keyboard.append([InlineKeyboardButton("💾 Сохранить", callback_data='main_criteria')])
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='main_criteria')])
            
            await query.edit_message_reply_markup(
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            await query.answer(f"{'Добавлено' if role in current_roles else 'Удалено'}: {role}")
        
        elif action == 'criteria_keywords':
            await query.edit_message_text(
                "Введите ключевые слова через запятую.\n\n"
                "Например: Python, Django, API\n"
                "или: Руководитель, Менеджер проектов\n\n"
                "Для отмены отправьте /cancel"
            )
            await query.answer()
            context.user_data['waiting_for'] = 'keywords'
            
        elif action == 'criteria_salary':
            await query.edit_message_text(
                "Введите минимальную желаемую зарплату (в рублях).\n\n"
                "Например: 150000\n\n"
                "Для отмены отправьте /cancel"
            )
            await query.answer()
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
    
    async def toggle_monitoring(self, query):
        """Переключить режим мониторинга 24/7"""
        chat_id = query.message.chat_id
        monitoring_state = self.db.get_monitoring_state(chat_id)
        
        new_value = not monitoring_state.get('monitoring_enabled', False)
        self.db.update_monitoring_state(chat_id, enabled=new_value)
        
        status = "включён" if new_value else "выключен"
        
        if new_value:
            message = f"✅ Мониторинг 24/7 {status}\n\nБот будет проверять новые вакансии каждые {config.HH_SEARCH_INTERVAL_SEC} секунд и автоматически присылать их вам."
        else:
            message = f"❌ Мониторинг 24/7 {status}"
        
        await query.answer(message)
        await self.show_main_menu(query.message, edit=True)
    
    async def show_admin_menu(self, query):
        """Показать меню администратора"""
        user_id = query.from_user.id
        if user_id not in config.ADMIN_CHAT_IDS:
            await query.answer("❌ Недостаточно прав")
            return
        
        admin_text = """
🔐 <b>Админ-панель</b>

<b>Доступные команды:</b>
• Обновление кода из Git
• Перезапуск сервиса (если разрешено)
• Просмотр статуса системы
"""
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить код", callback_data='admin_update_code')],
        ]
        
        if config.ALLOW_SYSTEMCTL:
            keyboard.append([InlineKeyboardButton("🔁 Перезапустить сервис", callback_data='admin_restart')])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')])
        
        await query.edit_message_text(
            admin_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    
    async def handle_admin_action(self, query, action, context):
        """Обработка админских действий"""
        user_id = query.from_user.id
        if user_id not in config.ADMIN_CHAT_IDS:
            await query.answer("❌ Недостаточно прав")
            return
        
        if action == 'admin_update_code':
            await query.edit_message_text("⏳ Обновляю код из репозитория...")
            result = await self.update_code_from_git()
            await query.edit_message_text(
                f"<b>Обновление кода:</b>\n\n{result}",
                parse_mode='HTML'
            )
        
        elif action == 'admin_restart':
            if not config.ALLOW_SYSTEMCTL:
                await query.answer("❌ Перезапуск сервиса отключён в конфигурации")
                return
            
            await query.edit_message_text("⏳ Перезапускаю сервис...")
            result = await self.restart_service()
            await query.edit_message_text(
                f"<b>Перезапуск сервиса:</b>\n\n{result}",
                parse_mode='HTML'
            )
    
    async def update_code_from_git(self) -> str:
        """Обновить код из Git репозитория"""
        try:
            repo_path = config.BOT_INSTALL_PATH
            
            if not os.path.exists(os.path.join(repo_path, '.git')):
                return f"❌ Директория {repo_path} не является Git репозиторием"
            
            repo = git.Repo(repo_path)
            
            # Fetch changes
            origin = repo.remotes.origin
            fetch_info = origin.fetch()
            
            # Check for conflicts
            if repo.is_dirty():
                return "⚠️ Обнаружены локальные изменения.\n\nВыполните git stash или commit вручную."
            
            # Pull changes
            current_commit = repo.head.commit.hexsha[:7]
            pull_info = origin.pull('main')
            new_commit = repo.head.commit.hexsha[:7]
            
            if current_commit == new_commit:
                return f"✅ Код уже актуален\n\nТекущий коммит: {current_commit}"
            
            return f"✅ Код успешно обновлён\n\nБыло: {current_commit}\nСтало: {new_commit}\n\nРекомендуется перезапустить сервис."
            
        except git.exc.GitCommandError as e:
            logger.error(f"Git error during update: {e}")
            return f"❌ Ошибка Git:\n\n{str(e)}"
        except Exception as e:
            logger.error(f"Error updating code: {e}")
            return f"❌ Ошибка обновления:\n\n{str(e)}"
    
    async def restart_service(self) -> str:
        """Перезапустить systemd сервис"""
        try:
            if not config.ALLOW_SYSTEMCTL:
                return "❌ Перезапуск сервиса отключён в конфигурации"
            
            # Run systemctl restart command
            result = subprocess.run(
                ['sudo', 'systemctl', 'restart', config.SERVICE_NAME],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Check status
                status_result = subprocess.run(
                    ['sudo', 'systemctl', 'status', config.SERVICE_NAME],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                return f"✅ Сервис {config.SERVICE_NAME} перезапущен\n\n<code>{status_result.stdout[:500]}</code>"
            else:
                return f"❌ Ошибка перезапуска:\n\n<code>{result.stderr[:500]}</code>"
                
        except subprocess.TimeoutExpired:
            return "⏳ Команда перезапуска выполняется слишком долго"
        except Exception as e:
            logger.error(f"Error restarting service: {e}")
            return f"❌ Ошибка:\n\n{str(e)}"
    
    async def show_help(self, query):
        """Показать справку"""
        chat_id = query.message.chat_id
        prefs = self.db.get_preferences(chat_id)
        monitoring_state = self.db.get_monitoring_state(chat_id)
        
        auto_apply_status = "✅ Включён" if prefs.get('auto_apply') else "❌ Выключен"
        monitoring_status = "✅ Включён" if monitoring_state.get('monitoring_enabled') else "❌ Выключен"
        
        help_text = f"""
ℹ️ <b>Справка</b>

<b>Текущий статус:</b>
• Авто-отклик: {auto_apply_status}
• Мониторинг 24/7: {monitoring_status}

<b>Команды бота:</b>
/start - Главное меню
/criteria - Настроить критерии поиска
/search - Запустить поиск вакансий
/prompt - Управление промптом
/apply_on - Включить авто-отклик
/apply_off - Выключить авто-отклик
/monitoring_on - Включить мониторинг 24/7
/monitoring_off - Выключить мониторинг 24/7
/stats - Статистика откликов
/help - Эта справка

<b>Админские команды (если вы админ):</b>
/update_code - Обновить код из Git
/restart - Перезапустить сервис (если разрешено)

<b>Как работает бот:</b>
1️⃣ Настройте критерии поиска (сфера, город, удалёнка, зарплата)
2️⃣ При необходимости настройте промпт для сопроводительных писем
3️⃣ Включите мониторинг 24/7 для автоматической проверки новых вакансий
4️⃣ Включите авто-отклик, если хотите откликаться автоматически
5️⃣ Или запустите поиск вручную командой /search

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
• HH_SEARCH_INTERVAL_SEC - интервал проверки (сек)
• ADMIN_CHAT_IDS - ID админов (через запятую)

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
        prefs = self.db.get_preferences(update.effective_user.id)
        
        domain_emoji = "💼" if prefs.get('role_domain') == 'Management' else "💻"
        remote_emoji = "✅" if prefs.get('remote_only') else "❌"
        
        # Format roles display
        roles = prefs.get('roles', [])
        roles_display = ', '.join(roles) if roles else 'не заданы'
        
        criteria_text = f"""
⚙️ <b>Настройки критериев поиска</b>

{domain_emoji} <b>Сфера:</b> {prefs.get('role_domain', 'IT')}
🌍 <b>Город:</b> {prefs.get('city', 'Москва')}
🏠 <b>Только удалёнка:</b> {remote_emoji}
📝 <b>Ключевые слова:</b> {', '.join(prefs.get('keywords', [])) or 'не заданы'}
💰 <b>Зарплата от:</b> {prefs.get('salary_min', 0)} руб.
👔 <b>Роли:</b> {roles_display}
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
        
        await update.message.reply_text(criteria_text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /search"""
        chat_id = update.effective_user.id
        await update.message.reply_text("🔍 Начинаю поиск вакансий...")
        await self.perform_search(chat_id, update.message)
    
    async def prompt_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /prompt"""
        prefs = self.db.get_preferences(update.effective_user.id)
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
        
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    
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
        chat_id = update.effective_user.id
        
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
        
        await update.message.reply_text(stats_text, parse_mode='HTML')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        chat_id = update.effective_user.id
        prefs = self.db.get_preferences(chat_id)
        monitoring_state = self.db.get_monitoring_state(chat_id)
        
        auto_apply_status = "✅ Включён" if prefs.get('auto_apply') else "❌ Выключен"
        monitoring_status = "✅ Включён" if monitoring_state.get('monitoring_enabled') else "❌ Выключен"
        
        help_text = f"""
ℹ️ <b>Справка</b>

<b>Текущий статус:</b>
• Авто-отклик: {auto_apply_status}
• Мониторинг 24/7: {monitoring_status}

<b>Команды бота:</b>
/start - Главное меню
/criteria - Настроить критерии поиска
/search - Запустить поиск вакансий
/prompt - Управление промптом
/apply_on - Включить авто-отклик
/apply_off - Выключить авто-отклик
/monitoring_on - Включить мониторинг 24/7
/monitoring_off - Выключить мониторинг 24/7
/stats - Статистика откликов
/help - Эта справка

<b>Админские команды (если вы админ):</b>
/update_code - Обновить код из Git
/restart - Перезапустить сервис (если разрешено)

<b>Как работает бот:</b>
1️⃣ Настройте критерии поиска (сфера, город, удалёнка, зарплата)
2️⃣ При необходимости настройте промпт для сопроводительных писем
3️⃣ Включите мониторинг 24/7 для автоматической проверки новых вакансий
4️⃣ Включите авто-отклик, если хотите откликаться автоматически
5️⃣ Или запустите поиск вручную командой /search

<b>⚙️ Настройка HH.ru API:</b>

Для автоматических откликов нужны:
• HH_ACCESS_TOKEN - OAuth токен доступа
• HH_RESUME_ID - ID вашего резюме
• HH_USER_AGENT - User-Agent для API запросов

<b>Как получить токен:</b>
1. Зарегистрируйте приложение на https://dev.hh.ru/admin
2. Получите Client ID и Client Secret
3. Пройдите OAuth авторизацию
4. Получите access_token и refresh_token

<b>Как узнать ID резюме:</b>
Через API запрос GET https://api.hh.ru/resumes/mine
с заголовком Authorization: Bearer YOUR_TOKEN

Подробнее: https://github.com/hhru/api

<b>Переменные окружения (.env):</b>
• TELEGRAM_BOT_TOKEN - токен Telegram бота
• OPENAI_API_KEY - ключ OpenAI для генерации писем
• HH_ACCESS_TOKEN - токен доступа к HH API
• HH_REFRESH_TOKEN - refresh токен для обновления
• HH_RESUME_ID - ID резюме
• HH_USER_AGENT - User-Agent (формат: app/user (email))
• HH_SEARCH_INTERVAL_SEC - интервал проверки (сек)
• ADMIN_CHAT_IDS - ID админов (через запятую)

Пример: см. файл .env.example
"""
        
        await update.message.reply_text(help_text, parse_mode='HTML')
    
    async def monitoring_on_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /monitoring_on"""
        chat_id = update.effective_user.id
        self.db.update_monitoring_state(chat_id, enabled=True)
        await update.message.reply_text(
            f"✅ Мониторинг 24/7 включён\n\n"
            f"Бот будет проверять новые вакансии каждые {config.HH_SEARCH_INTERVAL_SEC} секунд."
        )
    
    async def monitoring_off_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /monitoring_off"""
        chat_id = update.effective_user.id
        self.db.update_monitoring_state(chat_id, enabled=False)
        await update.message.reply_text("❌ Мониторинг 24/7 выключен")
    
    async def update_code_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /update_code"""
        user_id = update.effective_user.id
        if user_id not in config.ADMIN_CHAT_IDS:
            await update.message.reply_text("❌ Недостаточно прав для выполнения этой команды")
            return
        
        await update.message.reply_text("⏳ Обновляю код из репозитория...")
        result = await self.update_code_from_git()
        await update.message.reply_text(f"<b>Обновление кода:</b>\n\n{result}", parse_mode='HTML')
    
    async def restart_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /restart"""
        user_id = update.effective_user.id
        if user_id not in config.ADMIN_CHAT_IDS:
            await update.message.reply_text("❌ Недостаточно прав для выполнения этой команды")
            return
        
        if not config.ALLOW_SYSTEMCTL:
            await update.message.reply_text("❌ Перезапуск сервиса отключён в конфигурации")
            return
        
        await update.message.reply_text("⏳ Перезапускаю сервис...")
        result = await self.restart_service()
        await update.message.reply_text(f"<b>Перезапуск сервиса:</b>\n\n{result}", parse_mode='HTML')
    
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
    
    # Set application reference in job_bot
    job_bot.set_application(application)
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", job_bot.start_command))
    application.add_handler(CommandHandler("criteria", job_bot.criteria_command))
    application.add_handler(CommandHandler("search", job_bot.search_command))
    application.add_handler(CommandHandler("prompt", job_bot.prompt_command))
    application.add_handler(CommandHandler("apply_on", job_bot.apply_on_command))
    application.add_handler(CommandHandler("apply_off", job_bot.apply_off_command))
    application.add_handler(CommandHandler("monitoring_on", job_bot.monitoring_on_command))
    application.add_handler(CommandHandler("monitoring_off", job_bot.monitoring_off_command))
    application.add_handler(CommandHandler("stats", job_bot.stats_command))
    application.add_handler(CommandHandler("help", job_bot.help_command))
    application.add_handler(CommandHandler("cancel", job_bot.cancel_command))
    
    # Admin commands
    application.add_handler(CommandHandler("update_code", job_bot.update_code_command))
    application.add_handler(CommandHandler("restart", job_bot.restart_command))
    
    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(job_bot.button_callback))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, job_bot.handle_text_message))
    
    # Start monitoring scheduler
    job_bot.start_monitoring()
    
    # Запускаем бота
    logger.info("Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
