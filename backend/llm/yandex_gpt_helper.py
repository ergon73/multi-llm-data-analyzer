import logging
import requests
from typing import Optional
import json
from backend.config import Config

logger = logging.getLogger(__name__)

# Этот модуль инкапсулирует работу с YandexGPT.

def get_yandex_response(user_prompt: str, model: str = "yandexgpt-lite", retries=3) -> str:
    """
    Отправляет запрос к YandexGPT и возвращает ответ.
    Предусмотрены повторные попытки в случае ошибки.
    """
    # В тестовом режиме возвращаем заглушку
    if Config.TEST_MODE:
        return "Тестовый режим: Здесь будет ответ от YandexGPT. Для реальной работы укажите YANDEX_FOLDER_ID и YANDEX_API_KEY в .env"

    folder_id = Config.YANDEX_FOLDER_ID
    iam_token = Config.YANDEX_API_KEY
    
    logger.debug(f"Используется YANDEX_FOLDER_ID: {folder_id}")
    
    if not folder_id or not iam_token:
        logger.error("Не найдены учетные данные Yandex в переменных окружения")
        return "Ошибка конфигурации YandexGPT. Обратитесь к администратору."
    
    headers = {
        "Authorization": f"Bearer {iam_token}",
        "x-folder-id": folder_id
    }
    
    data = {
        "modelUri": f"gpt://{folder_id}/{model}",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": "2000"
        },
        "messages": [
            {"role": "system", "text": "Ты — полезный ассистент-аналитик данных."},
            {"role": "user", "text": user_prompt}
        ]
    }
    
    logger.debug(f"Подготовлен запрос к YandexGPT:")
    logger.debug(f"Headers: {json.dumps({k: v[:10] + '...' if k == 'Authorization' else v for k, v in headers.items()})}")
    logger.debug(f"Data: {json.dumps(data)}")
    
    for attempt in range(retries):
        try:
            logger.debug(f"Попытка {attempt + 1} отправки запроса к YandexGPT")
            response = requests.post(
                "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
                headers=headers,
                json=data
            )
            
            if response.status_code != 200:
                error_msg = f"Ошибка API YandexGPT: {response.status_code} - {response.text}"
                logger.error(error_msg)
                if "folder ID" in response.text:
                    error_response = response.json()
                    logger.error(f"Детали ошибки: {json.dumps(error_response)}")
                    if 'error' in error_response and 'message' in error_response['error']:
                        return f"Ошибка конфигурации YandexGPT: {error_response['error']['message']}"
                    return f"Ошибка конфигурации YandexGPT: неверный ID каталога. Текущий ID: {folder_id}"
                continue
                
            result = response.json()
            logger.debug("Успешно получен ответ от YandexGPT")
            return result['result']['alternatives'][0]['message']['text']
            
        except Exception as e:
            logger.error(f"Ошибка при работе с YandexGPT (попытка {attempt + 1}): {str(e)}")
            if attempt + 1 == retries:
                return "Не удалось получить ответ от YandexGPT. Попробуйте снова."
    
    return "Не удалось получить ответ от YandexGPT после всех попыток."