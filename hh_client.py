import requests
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class HeadHunterClient:
    """Клиент для работы с API HeadHunter"""
    
    BASE_URL = "https://api.hh.ru"
    
    def __init__(self, email: str = None, password: str = None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HH-Job-Bot/1.0 (your@email.com)',
            'Content-Type': 'application/json'
        })
        self.email = email
        self.password = password
        self.access_token = None
        
    def search_vacancies(self, 
                        text: str, 
                        area: int = 1,  # 1 = Москва, 2 = Санкт-Петербург
                        per_page: int = 20,
                        period: int = 1) -> List[Dict]:
        """
        Поиск вакансий
        
        Args:
            text: Поисковый запрос
            area: ID региона (1 - Москва)
            per_page: Количество вакансий на странице
            period: За сколько дней искать (1-30)
            
        Returns:
            Список вакансий
        """
        try:
            params = {
                'text': text,
                'area': area,
                'per_page': per_page,
                'period': period,
                'order_by': 'publication_time',  # Сначала новые
            }
            
            response = self.session.get(
                f"{self.BASE_URL}/vacancies",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            vacancies = data.get('items', [])
            
            logger.info(f"Найдено {len(vacancies)} вакансий по запросу '{text}'")
            return vacancies
            
        except Exception as e:
            logger.error(f"Ошибка при поиске вакансий: {e}")
            return []
    
    def get_vacancy_details(self, vacancy_id: str) -> Optional[Dict]:
        """Получить детальную информацию о вакансии"""
        try:
            response = self.session.get(f"{self.BASE_URL}/vacancies/{vacancy_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Ошибка при получении вакансии {vacancy_id}: {e}")
            return None
    
    def apply_to_vacancy(self, 
                        vacancy_id: str, 
                        resume_id: str, 
                        cover_letter: str) -> bool:
        """
        Откликнуться на вакансию
        
        ВАЖНО: Для автоматических откликов нужен OAuth токен с правами на отклики.
        Это требует авторизации через OAuth 2.0 на hh.ru
        
        Args:
            vacancy_id: ID вакансии
            resume_id: ID резюме
            cover_letter: Сопроводительное письмо
            
        Returns:
            True если отклик успешен
        """
        try:
            if not self.access_token:
                logger.warning("Нет токена авторизации. Нужна OAuth авторизация на hh.ru")
                return False
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'vacancy_id': vacancy_id,
                'resume_id': resume_id,
                'message': cover_letter
            }
            
            response = self.session.post(
                f"{self.BASE_URL}/negotiations",
                headers=headers,
                json=data
            )
            
            if response.status_code == 201:
                logger.info(f"Успешный отклик на вакансию {vacancy_id}")
                return True
            else:
                logger.error(f"Ошибка отклика: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при отклике на вакансию {vacancy_id}: {e}")
            return False
    
    def get_my_resumes(self) -> List[Dict]:
        """Получить список резюме пользователя"""
        try:
            if not self.access_token:
                logger.warning("Нет токена авторизации")
                return []
            
            headers = {'Authorization': f'Bearer {self.access_token}'}
            response = self.session.get(
                f"{self.BASE_URL}/resumes/mine",
                headers=headers
            )
            response.raise_for_status()
            
            return response.json().get('items', [])
            
        except Exception as e:
            logger.error(f"Ошибка при получении резюме: {e}")
            return []
    
    def filter_suitable_vacancies(self, 
                                  vacancies: List[Dict],
                                  min_salary: int = None,
                                  required_skills: List[str] = None) -> List[Dict]:
        """
        Фильтрация подходящих вакансий
        
        Args:
            vacancies: Список вакансий
            min_salary: Минимальная зарплата
            required_skills: Обязательные навыки
            
        Returns:
            Отфильтрованный список
        """
        filtered = []
        
        for vacancy in vacancies:
            # Фильтр по зарплате
            if min_salary:
                salary = vacancy.get('salary')
                if salary and salary.get('from'):
                    if salary['from'] < min_salary:
                        continue
            
            # Можно добавить фильтры по навыкам, опыту и т.д.
            filtered.append(vacancy)
        
        return filtered


def format_vacancy_info(vacancy: Dict) -> str:
    """Форматирование информации о вакансии для отображения"""
    name = vacancy.get('name', 'Без названия')
    employer = vacancy.get('employer', {}).get('name', 'Неизвестная компания')
    
    salary_info = "Зарплата не указана"
    if vacancy.get('salary'):
        salary = vacancy['salary']
        if salary.get('from') and salary.get('to'):
            salary_info = f"{salary['from']:,} - {salary['to']:,} {salary.get('currency', 'RUB')}"
        elif salary.get('from'):
            salary_info = f"От {salary['from']:,} {salary.get('currency', 'RUB')}"
        elif salary.get('to'):
            salary_info = f"До {salary['to']:,} {salary.get('currency', 'RUB')}"
    
    url = vacancy.get('alternate_url', '')
    
    text = f"""
📋 <b>{name}</b>

🏢 Компания: {employer}
💰 {salary_info}
🔗 Ссылка: {url}
"""
    return text.strip()
