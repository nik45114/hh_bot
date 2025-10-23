import requests
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import config

logger = logging.getLogger(__name__)


class HeadHunterClient:
    """Клиент для работы с API HeadHunter"""
    
    BASE_URL = "https://api.hh.ru"
    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE = 2  # seconds
    
    def __init__(self, email: str = None, password: str = None, access_token: str = None, 
                 refresh_token: str = None, user_agent: str = None):
        self.session = requests.Session()
        
        # Use provided user_agent or from config
        self.user_agent = user_agent or config.HH_USER_AGENT
        
        # Set default headers for all requests
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'HH-User-Agent': self.user_agent
        })
        
        self.email = email
        self.password = password
        self.access_token = access_token
        self.refresh_token = refresh_token or config.HH_REFRESH_TOKEN
        
        if self.access_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.access_token}'
            })
    
    def _request_with_retry(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """Make HTTP request with exponential backoff retry"""
        last_exception = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.session.request(method, url, **kwargs)
                
                # Log request details
                request_id = response.headers.get('X-Request-ID', 'N/A')
                logger.info(f"HH API {method} {url} -> {response.status_code} (X-Request-ID: {request_id})")
                
                # Handle rate limiting (429)
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', self.RETRY_BACKOFF_BASE ** (attempt + 1)))
                    logger.warning(f"Rate limited (429). X-Request-ID: {request_id}. Waiting {retry_after}s before retry {attempt + 1}/{self.MAX_RETRIES}")
                    time.sleep(retry_after)
                    continue
                
                # Handle server errors (5xx) with retry
                if response.status_code >= 500:
                    if attempt < self.MAX_RETRIES - 1:
                        wait_time = self.RETRY_BACKOFF_BASE ** (attempt + 1)
                        logger.warning(f"Server error {response.status_code}. X-Request-ID: {request_id}. Retrying in {wait_time}s ({attempt + 1}/{self.MAX_RETRIES})")
                        time.sleep(wait_time)
                        continue
                
                return response
                
            except requests.exceptions.Timeout as e:
                last_exception = e
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = self.RETRY_BACKOFF_BASE ** (attempt + 1)
                    logger.warning(f"Timeout. Retrying in {wait_time}s ({attempt + 1}/{self.MAX_RETRIES})")
                    time.sleep(wait_time)
                    continue
            
            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = self.RETRY_BACKOFF_BASE ** (attempt + 1)
                    logger.warning(f"Request error: {e}. Retrying in {wait_time}s ({attempt + 1}/{self.MAX_RETRIES})")
                    time.sleep(wait_time)
                    continue
        
        # All retries exhausted
        if last_exception:
            raise last_exception
        
        return None
    
    def refresh_access_token(self) -> bool:
        """
        Refresh access token using refresh token
        
        Returns:
            True if token was refreshed successfully, False otherwise
        """
        if not self.refresh_token:
            logger.warning("No refresh token available")
            return False
        
        if not config.HH_OAUTH_CLIENT_ID or not config.HH_OAUTH_CLIENT_SECRET:
            logger.warning("OAuth client credentials not configured")
            return False
        
        try:
            logger.info("Attempting to refresh access token")
            response = requests.post(
                'https://hh.ru/oauth/token',
                data={
                    'grant_type': 'refresh_token',
                    'refresh_token': self.refresh_token,
                    'client_id': config.HH_OAUTH_CLIENT_ID,
                    'client_secret': config.HH_OAUTH_CLIENT_SECRET
                },
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                
                # Update session headers
                self.session.headers.update({
                    'Authorization': f'Bearer {self.access_token}'
                })
                
                logger.info("Access token refreshed successfully")
                return True
            else:
                logger.error(f"Failed to refresh token: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return False
        
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
            
            response = self._request_with_retry(
                'GET',
                f"{self.BASE_URL}/vacancies",
                params=params,
                timeout=10
            )
            
            if response and response.status_code == 200:
                data = response.json()
                vacancies = data.get('items', [])
                logger.info(f"Найдено {len(vacancies)} вакансий по запросу '{text}'")
                return vacancies
            else:
                logger.error(f"Failed to search vacancies: {response.status_code if response else 'No response'}")
                return []
            
        except requests.exceptions.Timeout:
            logger.error("Timeout при поиске вакансий после всех попыток")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при поиске вакансий после всех попыток: {e}")
            return []
        except Exception as e:
            logger.error(f"Неожиданная ошибка при поиске вакансий: {e}")
            return []
    
    def get_vacancy_details(self, vacancy_id: str) -> Optional[Dict]:
        """Получить детальную информацию о вакансии"""
        try:
            response = self._request_with_retry(
                'GET',
                f"{self.BASE_URL}/vacancies/{vacancy_id}",
                timeout=10
            )
            
            if response and response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get vacancy {vacancy_id}: {response.status_code if response else 'No response'}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout при получении вакансии {vacancy_id} после всех попыток")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении вакансии {vacancy_id} после всех попыток: {e}")
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
            Dict с ключами 'success' (bool), 'message' (str), и опционально 'negotiation_url' (str)
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
            
            # Prepare form data (application/x-www-form-urlencoded)
            form_data = {
                'vacancy_id': vacancy_id,
                'resume_id': resume_id,
                'message': cover_letter
            }
            
            logger.info(f"Applying to vacancy {vacancy_id} with form-urlencoded data")
            
            response = self._request_with_retry(
                'POST',
                f"{self.BASE_URL}/negotiations",
                data=form_data,  # Use data= for form-urlencoded, not json=
                timeout=10
            )
            
            if not response:
                return {
                    'success': False,
                    'message': 'Не удалось отправить отклик после нескольких попыток'
                }
            
            request_id = response.headers.get('X-Request-ID', 'N/A')
            
            # Handle 201 Created - success
            if response.status_code == 201:
                negotiation_url = response.headers.get('Location', '')
                logger.info(f"Успешный отклик на вакансию {vacancy_id} (X-Request-ID: {request_id})")
                return {
                    'success': True,
                    'message': 'Отклик успешно отправлен!',
                    'negotiation_url': negotiation_url
                }
            
            # Handle 200 OK - also success
            elif response.status_code == 200:
                logger.info(f"Успешный отклик на вакансию {vacancy_id} (X-Request-ID: {request_id})")
                return {
                    'success': True,
                    'message': 'Отклик успешно отправлен!'
                }
            
            # Handle 409 Conflict - already applied (считаем успехом)
            elif response.status_code == 409:
                logger.info(f"Уже откликались на вакансию {vacancy_id} (X-Request-ID: {request_id})")
                return {
                    'success': True,
                    'message': 'Вы уже откликались на эту вакансию ранее.'
                }
            
            # Handle 401 Unauthorized - try to refresh token
            elif response.status_code == 401:
                logger.warning(f"Unauthorized (401) for vacancy {vacancy_id} (X-Request-ID: {request_id}). Attempting token refresh.")
                
                # Try to refresh token
                if self.refresh_access_token():
                    # Retry once with new token
                    logger.info(f"Retrying application to vacancy {vacancy_id} with refreshed token")
                    response = self._request_with_retry(
                        'POST',
                        f"{self.BASE_URL}/negotiations",
                        data=form_data,
                        timeout=10
                    )
                    
                    if response and response.status_code in [200, 201]:
                        negotiation_url = response.headers.get('Location', '')
                        logger.info(f"Успешный отклик после обновления токена (X-Request-ID: {response.headers.get('X-Request-ID', 'N/A')})")
                        return {
                            'success': True,
                            'message': 'Отклик успешно отправлен!',
                            'negotiation_url': negotiation_url
                        }
                    elif response and response.status_code == 409:
                        return {
                            'success': True,
                            'message': 'Вы уже откликались на эту вакансию ранее.'
                        }
                
                # Token refresh failed or retry failed
                return {
                    'success': False,
                    'message': 'Токен доступа истёк. Пожалуйста, обновите HH_ACCESS_TOKEN в настройках.'
                }
            
            # Handle 403 Forbidden - no permission
            elif response.status_code == 403:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('description', 'Недостаточно прав')
                logger.error(f"Ошибка отклика 403 (X-Request-ID: {request_id}): {error_msg}")
                return {
                    'success': False,
                    'message': f'Ошибка доступа: {error_msg}'
                }
            
            # Handle 400 Bad Request
            elif response.status_code == 400:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('description', 'Неверный запрос')
                
                # Check for bad_arguments details
                if 'bad_arguments' in error_data:
                    bad_args = error_data['bad_arguments']
                    if bad_args:
                        args_info = ', '.join([f"{arg.get('name')}: {arg.get('description')}" for arg in bad_args])
                        error_msg = f"{error_msg}: {args_info}"
                
                logger.error(f"Ошибка отклика 400 (X-Request-ID: {request_id}): {error_msg}")
                return {
                    'success': False,
                    'message': f'Ошибка при отклике: {error_msg}'
                }
            
            # Handle 429 Rate Limit (should have been retried, but just in case)
            elif response.status_code == 429:
                logger.warning(f"Достигнут лимит запросов к API (X-Request-ID: {request_id})")
                return {
                    'success': False,
                    'message': 'Превышен лимит запросов. Попробуйте позже.'
                }
            
            # Handle any other status code
            else:
                logger.error(f"Ошибка отклика: {response.status_code} (X-Request-ID: {request_id}) - {response.text[:200]}")
                return {
                    'success': False,
                    'message': f'Ошибка при отклике (код {response.status_code})'
                }
                
        except requests.exceptions.Timeout:
            logger.error("Timeout при отклике на вакансию после всех попыток")
            return {
                'success': False,
                'message': 'Превышено время ожидания. Попробуйте позже.'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при отклике на вакансию {vacancy_id} после всех попыток: {e}")
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
            
            response = self._request_with_retry(
                'GET',
                f"{self.BASE_URL}/resumes/mine",
                timeout=10
            )
            
            if response and response.status_code == 200:
                return response.json().get('items', [])
            else:
                logger.error(f"Failed to get resumes: {response.status_code if response else 'No response'}")
                return []
            
        except requests.exceptions.Timeout:
            logger.error("Timeout при получении резюме после всех попыток")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении резюме после всех попыток: {e}")
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
