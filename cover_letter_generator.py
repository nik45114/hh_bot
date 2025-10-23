from openai import OpenAI
import logging
from typing import Optional
from resume_data import RESUME_DATA, COVER_LETTER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class CoverLetterGenerator:
    """Генератор сопроводительных писем с использованием OpenAI"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        
    def generate_cover_letter(self,
                            job_title: str,
                            company_name: str,
                            job_description: str) -> Optional[str]:
        """
        Генерация сопроводительного письма
        
        Args:
            job_title: Название вакансии
            company_name: Название компании
            job_description: Описание вакансии
            
        Returns:
            Сопроводительное письмо или None в случае ошибки
        """
        try:
            # Формируем промпт
            prompt = COVER_LETTER_PROMPT_TEMPLATE.format(
                job_title=job_title,
                company_name=company_name,
                name=RESUME_DATA['name'],
                position=RESUME_DATA['position'],
                summary=RESUME_DATA['summary'],
                skills=', '.join(RESUME_DATA['skills']),
                job_description=job_description[:1000]  # Ограничиваем длину
            )
            
            # Генерируем письмо
            response = self.client.chat.completions.create(
                model="gpt-4",  # Или "gpt-3.5-turbo" для более быстрой генерации
                messages=[
                    {
                        "role": "system",
                        "content": "Ты профессиональный HR-консультант, который помогает создавать эффективные сопроводительные письма для IT-специалистов."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            cover_letter = response.choices[0].message.content.strip()
            logger.info(f"Сгенерировано сопроводительное письмо для {job_title} в {company_name}")
            
            return cover_letter
            
        except Exception as e:
            logger.error(f"Ошибка при генерации сопроводительного письма: {e}")
            return None
    
    def generate_simple_cover_letter(self, 
                                    job_title: str,
                                    company_name: str) -> str:
        """
        Генерация простого сопроводительного письма без AI
        (запасной вариант если OpenAI недоступен)
        """
        skills = ', '.join(RESUME_DATA['skills'][:5])
        
        letter = f"""Здравствуйте!

Меня заинтересовала вакансия {job_title} в компании {company_name}.

{RESUME_DATA['summary'].strip()}

Мои ключевые навыки: {skills}.

Буду рад обсудить детали и ответить на ваши вопросы.

Спасибо за внимание к моей кандидатуре!"""
        
        return letter
