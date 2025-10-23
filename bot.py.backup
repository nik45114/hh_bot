import asyncio
import json
import logging
import os
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

import config
from hh_client import HeadHunterClient, format_vacancy_info
from cover_letter_generator import CoverLetterGenerator

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


class JobBot:
    """Telegram бот для автоматизации откликов на hh.ru"""
    
    def __init__(self):
        self.hh_client = HeadHunterClient(config.HH_EMAIL, config.HH_PASSWORD)
        self.cover_letter_gen = CoverLetterGenerator(config.OPENAI_API_KEY)
        
        self.is_running = False
        self.applications_count = 0
        self.applications_today = 0
        self.last_reset_date = datetime.now().date()
        
        self.state = self.load_state()
        
    def load_state(self) -> Dict:
        """Загрузка состояния бота из файла"""
        try:
            if os.path.exists(config.STATE_FILE):
                with open(config.STATE_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки состояния: {e}")
        
        return {
            'is_running': False,
            'applications_count': 0,
            'processed_vacancies': [],
            'settings': {
                'keywords': config.SEARCH_KEYWORDS,
                'interval': config.SEARCH_INTERVAL_MINUTES,
                'max_per_day': config.MAX_APPLICATIONS_PER_DAY
            }
        }
    
    def save_state(self):
        """Сохранение состояния бота"""
        try:
            state = {
                'is_running': self.is_running,
                'applications_count': self.applications_count,
                'processed_vacancies': self.state.get('processed_vacancies', []),
                'settings': self.state.get('settings', {})
            }
            with open(config.STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка сохранения состояния: {e}")
    
    def reset_daily_counter(self):
        """Сброс ежедневного счетчика откликов"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            self.applications_today = 0
            self.last_reset_date = today
            logger.info("Сброшен ежедневный счетчик откликов")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user_id = str(update.effective_user.id)
        
        if config.ALLOWED_USER_ID and user_id != config.ALLOWED_USER_ID:
            await update.message.reply_text("❌ У вас нет доступа к этому боту.")
            return
        
        keyboard = [
            [InlineKeyboardButton("▶️ Запустить поиск", callback_data='start_search')],
            [InlineKeyboardButton("⏸ Остановить поиск", callback_data='stop_search')],
            [InlineKeyboardButton("📊 Статистика", callback_data='stats')],
            [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')],
            [InlineKeyboardButton("🔄 Обновить из GitHub", callback_data='update_repo')],
            [InlineKeyboardButton("ℹ️ Помощь", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = """
🤖 <b>HH Job Bot</b>

Привет! Я бот для автоматизации откликов на вакансии с hh.ru.

<b>Мои возможности:</b>
• Автоматический поиск вакансий по ключевым словам
• Генерация сопроводительных писем с помощью AI
• Автоматические отклики на подходящие вакансии
• Статистика и контроль процесса

Выбери действие в меню ниже 👇
"""
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(query.from_user.id)
        if config.ALLOWED_USER_ID and user_id != config.ALLOWED_USER_ID:
            await query.edit_message_text("❌ У вас нет доступа к этому боту.")
            return
        
        action = query.data
        
        if action == 'start_search':
            await self.start_search(query)
        elif action == 'stop_search':
            await self.stop_search(query)
        elif action == 'stats':
            await self.show_stats(query)
        elif action == 'settings':
            await self.show_settings(query)
        elif action == 'update_repo':
            await self.update_from_github(query)
        elif action == 'help':
            await self.show_help(query)
        elif action == 'back_to_menu':
            await self.show_main_menu(query)
    
    async def start_search(self, query):
        """Запуск автоматического поиска"""
        if self.is_running:
            await query.edit_message_text(
                "ℹ️ Поиск уже запущен!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')
                ]])
            )
            return
        
        self.is_running = True
        self.save_state()
        
        # Запускаем фоновую задачу поиска
        asyncio.create_task(self.search_and_apply_loop(query.message.chat_id))
        
        await query.edit_message_text(
            "✅ Поиск вакансий запущен!\n\n"
            f"🔍 Ключевые слова: {', '.join(self.state['settings']['keywords'])}\n"
            f"⏱ Интервал: {self.state['settings']['interval']} мин\n"
            f"📊 Лимит в день: {self.state['settings']['max_per_day']}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')
            ]])
        )
    
    async def stop_search(self, query):
        """Остановка автоматического поиска"""
        if not self.is_running:
            await query.edit_message_text(
                "ℹ️ Поиск не запущен!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')
                ]])
            )
            return
        
        self.is_running = False
        self.save_state()
        
        await query.edit_message_text(
            "⏸ Поиск остановлен.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')
            ]])
        )
    
    async def show_stats(self, query):
        """Показать статистику"""
        self.reset_daily_counter()
        
        stats_text = f"""
📊 <b>Статистика</b>

📝 Откликов сегодня: {self.applications_today}/{self.state['settings']['max_per_day']}
📈 Всего откликов: {self.applications_count}
🔍 Обработано вакансий: {len(self.state.get('processed_vacancies', []))}

Status: {'🟢 Активен' if self.is_running else '🔴 Остановлен'}
"""
        
        await query.edit_message_text(
            stats_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')
            ]])
        )
    
    async def show_settings(self, query):
        """Показать настройки"""
        settings = self.state['settings']
        
        settings_text = f"""
⚙️ <b>Настройки</b>

🔍 Ключевые слова:
{', '.join(settings['keywords'])}

⏱ Интервал проверки: {settings['interval']} мин
📊 Максимум откликов в день: {settings['max_per_day']}

Для изменения настроек отредактируй файл .env и перезапусти бота.
"""
        
        await query.edit_message_text(
            settings_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')
            ]])
        )
    
    async def update_from_github(self, query):
        """Обновление кода из GitHub"""
        await query.edit_message_text("🔄 Обновление из GitHub...")
        
        try:
            # Выполняем git pull
            result = subprocess.run(
                ['git', 'pull', 'origin', 'main'],
                cwd='/home/claude/hh_bot',
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                await query.edit_message_text(
                    f"✅ Обновление выполнено успешно!\n\n"
                    f"<code>{result.stdout}</code>\n\n"
                    "⚠️ Рекомендуется перезапустить бота для применения изменений.",
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')
                    ]])
                )
            else:
                await query.edit_message_text(
                    f"❌ Ошибка обновления:\n\n<code>{result.stderr}</code>",
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')
                    ]])
                )
        
        except Exception as e:
            await query.edit_message_text(
                f"❌ Ошибка: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')
                ]])
            )
    
    async def show_help(self, query):
        """Показать справку"""
        help_text = """
ℹ️ <b>Справка</b>

<b>Команды:</b>
/start - Главное меню
/stop - Остановить бота

<b>Как работает бот:</b>
1. Ищет вакансии по заданным ключевым словам
2. Фильтрует подходящие вакансии
3. Генерирует сопроводительное письмо с помощью AI
4. Отправляет отклик на вакансию

<b>Настройка:</b>
• Отредактируй файл .env для изменения настроек
• Заполни resume_data.py своими данными
• Перезапусти бота после изменений

<b>⚠️ Важно:</b>
Для автоматических откликов нужна OAuth авторизация на hh.ru.
Подробнее: https://github.com/hhru/api
"""
        
        await query.edit_message_text(
            help_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')
            ]])
        )
    
    async def show_main_menu(self, query):
        """Показать главное меню"""
        keyboard = [
            [InlineKeyboardButton("▶️ Запустить поиск", callback_data='start_search')],
            [InlineKeyboardButton("⏸ Остановить поиск", callback_data='stop_search')],
            [InlineKeyboardButton("📊 Статистика", callback_data='stats')],
            [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')],
            [InlineKeyboardButton("🔄 Обновить из GitHub", callback_data='update_repo')],
            [InlineKeyboardButton("ℹ️ Помощь", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🤖 <b>Главное меню</b>\n\nВыбери действие:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    
    async def search_and_apply_loop(self, chat_id):
        """Основной цикл поиска и откликов"""
        application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        
        while self.is_running:
            try:
                self.reset_daily_counter()
                
                # Проверяем лимит откликов
                if self.applications_today >= self.state['settings']['max_per_day']:
                    logger.info("Достигнут дневной лимит откликов")
                    await application.bot.send_message(
                        chat_id=chat_id,
                        text=f"⏸ Достигнут дневной лимит откликов ({self.state['settings']['max_per_day']})"
                    )
                    await asyncio.sleep(3600)  # Ждем час
                    continue
                
                # Ищем вакансии по каждому ключевому слову
                for keyword in self.state['settings']['keywords']:
                    if not self.is_running:
                        break
                    
                    logger.info(f"Поиск вакансий по запросу: {keyword}")
                    vacancies = self.hh_client.search_vacancies(keyword, per_page=10)
                    
                    for vacancy in vacancies:
                        if not self.is_running:
                            break
                        
                        vacancy_id = vacancy.get('id')
                        
                        # Пропускаем уже обработанные вакансии
                        if vacancy_id in self.state.get('processed_vacancies', []):
                            continue
                        
                        # Получаем детали вакансии
                        details = self.hh_client.get_vacancy_details(vacancy_id)
                        if not details:
                            continue
                        
                        # Отправляем информацию о вакансии
                        vacancy_text = format_vacancy_info(vacancy)
                        await application.bot.send_message(
                            chat_id=chat_id,
                            text=f"🔍 Найдена вакансия:\n{vacancy_text}",
                            parse_mode='HTML'
                        )
                        
                        # Генерируем сопроводительное письмо
                        cover_letter = self.cover_letter_gen.generate_cover_letter(
                            job_title=details.get('name', ''),
                            company_name=details.get('employer', {}).get('name', ''),
                            job_description=details.get('description', '')
                        )
                        
                        if cover_letter:
                            await application.bot.send_message(
                                chat_id=chat_id,
                                text=f"📝 Сопроводительное письмо:\n\n{cover_letter[:500]}..."
                            )
                        
                        # Здесь должен быть код отклика на вакансию
                        # Для этого нужна OAuth авторизация на hh.ru
                        
                        # Добавляем в обработанные
                        if 'processed_vacancies' not in self.state:
                            self.state['processed_vacancies'] = []
                        self.state['processed_vacancies'].append(vacancy_id)
                        self.save_state()
                        
                        # Небольшая задержка между обработкой вакансий
                        await asyncio.sleep(30)
                
                # Ждем до следующей итерации
                logger.info(f"Ожидание {self.state['settings']['interval']} минут до следующего поиска")
                await asyncio.sleep(self.state['settings']['interval'] * 60)
                
            except Exception as e:
                logger.error(f"Ошибка в цикле поиска: {e}")
                await asyncio.sleep(300)  # Ждем 5 минут при ошибке


def main():
    """Запуск бота"""
    # Проверка наличия токенов
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("Не указан TELEGRAM_BOT_TOKEN в .env файле!")
        return
    
    if not config.OPENAI_API_KEY:
        logger.warning("Не указан OPENAI_API_KEY - генерация писем будет недоступна")
    
    # Создаем экземпляр бота
    job_bot = JobBot()
    
    # Создаем приложение Telegram
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", job_bot.start_command))
    application.add_handler(CallbackQueryHandler(job_bot.button_callback))
    
    # Запускаем бота
    logger.info("Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
