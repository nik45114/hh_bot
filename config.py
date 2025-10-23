import os
from dotenv import load_dotenv

load_dotenv()

# Telegram settings
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ALLOWED_USER_ID = os.getenv('ALLOWED_USER_ID')

# OpenAI settings
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# HeadHunter credentials
HH_EMAIL = os.getenv('HH_EMAIL')
HH_PASSWORD = os.getenv('HH_PASSWORD')

# GitHub settings
GITHUB_REPO = os.getenv('GITHUB_REPO', 'https://github.com/nik45114/hh_bot.git')

# Search settings
SEARCH_KEYWORDS = os.getenv('SEARCH_KEYWORDS', 'Python developer').split(',')
SEARCH_KEYWORDS = [kw.strip() for kw in SEARCH_KEYWORDS]
SEARCH_INTERVAL_MINUTES = int(os.getenv('SEARCH_INTERVAL_MINUTES', '60'))
MAX_APPLICATIONS_PER_DAY = int(os.getenv('MAX_APPLICATIONS_PER_DAY', '20'))

# Bot state file
STATE_FILE = 'bot_state.json'
APPLICATIONS_LOG = 'applications.log'
