import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

# Этот модуль инкапсулирует работу с OpenAI API.

def get_openai_response(user_prompt: str, model: str = "gpt-4", retries=3) -> str:
    """
    Отправляет запрос к OpenAI и возвращает ответ.
    """
    # В тестовом режиме возвращаем заглушку
    if os.getenv("TEST_MODE", "false").lower() == "true":
        return "Тестовый режим: Здесь будет ответ от OpenAI. Для реальной работы укажите OPENAI_API_KEY в .env"

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("Не найден API ключ OpenAI в переменных окружения")
        return "Ошибка конфигурации OpenAI. Обратитесь к администратору."
    
    client = OpenAI(api_key=api_key)
    
    system_prompt = "Ты — полезный ассистент-аналитик данных."
    
    for attempt in range(retries):
        try:
            logger.debug(f"Попытка {attempt + 1} отправки запроса к OpenAI")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            logger.debug("Успешно получен ответ от OpenAI")
            content = response.choices[0].message.content
            if content is None:
                return "Получен пустой ответ от OpenAI. Попробуйте снова."
            return content
            
        except Exception as e:
            logger.error(f"Ошибка при работе с OpenAI (попытка {attempt + 1}): {str(e)}")
            if attempt + 1 == retries:
                return "Не удалось получить ответ от OpenAI. Попробуйте снова."
    
    return "Не удалось получить ответ от OpenAI после всех попыток."