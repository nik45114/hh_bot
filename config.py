import os
from dotenv import load_dotenv

load_dotenv()

# Telegram settings
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ALLOWED_USER_ID = os.getenv('ALLOWED_USER_ID')

# OpenAI settings
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# HeadHunter credentials (legacy - для старых методов)
HH_EMAIL = os.getenv('HH_EMAIL')
HH_PASSWORD = os.getenv('HH_PASSWORD')

# HeadHunter OAuth settings
HH_OAUTH_CLIENT_ID = os.getenv('HH_OAUTH_CLIENT_ID')
HH_OAUTH_CLIENT_SECRET = os.getenv('HH_OAUTH_CLIENT_SECRET')
HH_ACCESS_TOKEN = os.getenv('HH_ACCESS_TOKEN')
HH_REFRESH_TOKEN = os.getenv('HH_REFRESH_TOKEN')
HH_RESUME_ID = os.getenv('HH_RESUME_ID')  # ID резюме для откликов

# GitHub settings
GITHUB_REPO = os.getenv('GITHUB_REPO', 'https://github.com/nik45114/hh_bot.git')

# Search settings
SEARCH_KEYWORDS = os.getenv('SEARCH_KEYWORDS', 'менеджер,руководитель').split(',')
SEARCH_KEYWORDS = [kw.strip() for kw in SEARCH_KEYWORDS]
SEARCH_INTERVAL_MINUTES = int(os.getenv('SEARCH_INTERVAL_MINUTES', '60'))
MAX_APPLICATIONS_PER_DAY = int(os.getenv('MAX_APPLICATIONS_PER_DAY', '20'))

# Default search filters
DEFAULT_AREA = int(os.getenv('DEFAULT_AREA', '1'))  # 1 = Москва, 113 = Россия
DEFAULT_SCHEDULE = os.getenv('DEFAULT_SCHEDULE', 'remote')  # remote, fullDay, flexible
DEFAULT_EXPERIENCE = os.getenv('DEFAULT_EXPERIENCE', 'between3And6')  # noExperience, between1And3, between3And6, moreThan6
DEFAULT_EMPLOYMENT = os.getenv('DEFAULT_EMPLOYMENT', 'full')  # full, part, project
MIN_SALARY = int(os.getenv('MIN_SALARY', '0'))

# Bot state file
STATE_FILE = 'bot_state.json'
APPLICATIONS_LOG = 'applications.log'