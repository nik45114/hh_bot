class HHClient:
    # Добавляем поддержку OAuth 2.0
    def __init__(self):
        self.access_token = None
        self.refresh_token = None

    def set_access_token(self, token):
        """Установить OAuth токен"""
        self.access_token = token

    def refresh_access_token(self):
        """Обновить токен доступа с помощью refresh token"""
        # Логика обновления токена...
        pass

    def search_vacancies(self, schedule=None, experience=None, employment=None,
                         salary=None, only_with_salary=False):
        """Искать вакансии с учетом дополнительных параметров"""
        # Логика поиска вакансий...
        pass

    def apply_to_vacancy(self, vacancy_id):
        """Подать заявку на вакансию с авторизацией OAuth"""
        # Логика подачи заявки...
        pass

    def format_vacancy_info(self, vacancy):
        """Форматировать информацию о вакансии"""
        # Логика форматирования...
        # Показать тип графика работы
        pass

    def handle_error(self, error):
        """Обработать ошибки и ведение журнала"""
        # Логика обработки ошибок...
        pass