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
    
    def __init__(self, email: str = None, password: str = None, access_token: str = None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HH-Job-Bot/1.0 (your@email.com)',
            'Content-Type': 'application/json'
        })
        self.email = email
        self.password = password
        self.access_token = access_token
        
        if self.access_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.access_token}'
            })
        
    def search_vacancies(self, 
                        text: str = None,
                        area: int = 1,  # 1 = Москва, 2 = Санкт-Петербург, 113 = Россия
                        per_page: int = 20,
                        period: int = 1,
                        schedule: str = None,  # remote, fullDay, shift, flexible, flyInFlyOut
                        experience: str = None,  # noExperience, between1And3, between3And6, moreThan6
                        employment: str = None,  # full, part, project, volunteer, probation
                        salary: int = None,
                        only_with_salary: bool = False) -> List[Dict]:
        """
        Поиск вакансий с расширенными фильтрами
        
        Args:
            text: Поисковый запрос
            area: ID региона (1 - Москва, 113 - Россия)
            per_page: Количество вакансий на странице
            period: За сколько дней искать (1-30)
            schedule: График работы (remote для удалённой)
            experience: Требуемый опыт
            employment: Тип занятости
            salary: Минимальная зарплата
            only_with_salary: Только с указанной зарплатой
            
        Returns:
            Список вакансий
        """
        try:
            params = {
                'per_page': per_page,
                'period': period,
                'order_by': 'publication_time',  # Сначала новые
            }
            
            if text:
                params['text'] = text
            if area:
                params['area'] = area
            if schedule:
                params['schedule'] = schedule
            if experience:
                params['experience'] = experience
            if employment:
                params['employment'] = employment
            if salary:
                params['salary'] = salary
            if only_with_salary:
                params['only_with_salary'] = 'true'
            
            response = self.session.get(
                f"{self.BASE_URL}/vacancies",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            vacancies = data.get('items', [])
            
            logger.info(f"Найдено {len(vacancies)} вакансий по запросу '{text}'")
            return vacancies
            
        except requests.exceptions.Timeout:
            logger.error("Timeout при поиске вакансий")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при поиске вакансий: {e}")
            return []
        except Exception as e:
            logger.error(f"Неожиданная ошибка при поиске вакансий: {e}")
            return []
    
    def get_vacancy_details(self, vacancy_id: str) -> Optional[Dict]:
        """Получить детальную информацию о вакансии"""
        try:
            response = self.session.get(
                f"{self.BASE_URL}/vacancies/{vacancy_id}",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"Timeout при получении вакансии {vacancy_id}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении вакансии {vacancy_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при получении вакансии {vacancy_id}: {e}")
            return None
    
    def apply_to_vacancy(self, 
                        vacancy_id: str, 
                        resume_id: str, 
                        cover_letter: str) -> Dict:
        """
        Откликнуться на вакансию
        
        Требует OAuth токен с правами на отклики.
        
        Args:
            vacancy_id: ID вакансии
            resume_id: ID резюме
            cover_letter: Сопроводительное письмо
            
        Returns:
            Dict с ключами 'success' (bool) и 'message' (str)
        """
        try:
            if not self.access_token:
                logger.warning("Нет токена авторизации. Нужна OAuth авторизация на hh.ru")
                return {
                    'success': False,
                    'message': 'Не настроен токен доступа HH.ru. Используйте /help для инструкций по настройке.'
                }
            
            if not resume_id:
                return {
                    'success': False,
                    'message': 'Не указан ID резюме. Используйте /help для инструкций по настройке.'
                }
            
            data = {
                'vacancy_id': vacancy_id,
                'resume_id': resume_id,
                'message': cover_letter
            }
            
            response = self.session.post(
                f"{self.BASE_URL}/negotiations",
                json=data,
                timeout=10
            )
            
            if response.status_code == 201:
                logger.info(f"Успешный отклик на вакансию {vacancy_id}")
                return {
                    'success': True,
                    'message': 'Отклик успешно отправлен!'
                }
            elif response.status_code == 400:
                error_data = response.json()
                error_msg = error_data.get('description', 'Неизвестная ошибка')
                logger.error(f"Ошибка отклика 400: {error_msg}")
                return {
                    'success': False,
                    'message': f'Ошибка при отклике: {error_msg}'
                }
            elif response.status_code == 403:
                logger.error("Недостаточно прав для отклика")
                return {
                    'success': False,
                    'message': 'Недостаточно прав. Проверьте токен доступа.'
                }
            elif response.status_code == 429:
                logger.warning("Достигнут лимит запросов к API")
                return {
                    'success': False,
                    'message': 'Превышен лимит запросов. Попробуйте позже.'
                }
            else:
                logger.error(f"Ошибка отклика: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'message': f'Ошибка при отклике (код {response.status_code})'
                }
                
        except requests.exceptions.Timeout:
            logger.error("Timeout при отклике на вакансию")
            return {
                'success': False,
                'message': 'Превышено время ожидания. Попробуйте позже.'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при отклике на вакансию {vacancy_id}: {e}")
            return {
                'success': False,
                'message': f'Ошибка соединения: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отклике на вакансию {vacancy_id}: {e}")
            return {
                'success': False,
                'message': f'Неожиданная ошибка: {str(e)}'
            }
    
    def get_my_resumes(self) -> List[Dict]:
        """Получить список резюме пользователя"""
        try:
            if not self.access_token:
                logger.warning("Нет токена авторизации")
                return []
            
            response = self.session.get(
                f"{self.BASE_URL}/resumes/mine",
                timeout=10
            )
            response.raise_for_status()
            
            return response.json().get('items', [])
            
        except requests.exceptions.Timeout:
            logger.error("Timeout при получении резюме")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении резюме: {e}")
            return []
        except Exception as e:
            logger.error(f"Неожиданная ошибка при получении резюме: {e}")
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
