import os
import logging
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

# Настройка логирования
logger = logging.getLogger(__name__)

def get_giga_response(user_prompt: str, model: str = "GigaChat:latest") -> str:
    """
    Отправляет запрос к GigaChat и возвращает ответ.
    В случае ошибки возвращает сообщение об ошибке.
    """
    # В тестовом режиме возвращаем заглушку
    if os.getenv("TEST_MODE", "false").lower() == "true":
        return "Тестовый режим: Здесь будет ответ от GigaChat. Для реальной работы укажите GIGACHAT_CREDENTIALS в .env"

    try:
        credentials = os.getenv("GIGACHAT_CREDENTIALS")
        cert_path = os.getenv("GIGACHAT_CERT_PATH", "russian_trusted_root_ca.cer")

        if not credentials:
            logger.error("Не найдены учетные данные GigaChat в переменных окружения")
            return "Не удалось получить ответ от GigaChat: отсутствуют учетные данные"

        # Проверяем наличие сертификата
        if not os.path.exists(cert_path):
            logger.warning(f"Сертификат {cert_path} не найден")
            return "Не удалось получить ответ от GigaChat: отсутствует сертификат"
        
        # Создаем клиент GigaChat
        giga = GigaChat(
            credentials=credentials,
            ca_bundle_file=cert_path,
            verify_ssl_certs=True
        )
        
        # Создаем структуру сообщения для API
        messages = [
            Messages(
                role=MessagesRole.SYSTEM,
                content="Ты — полезный ассистент-аналитик данных."
            ),
            Messages(
                role=MessagesRole.USER,
                content=user_prompt
            )
        ]
        
        # Отправляем запрос
        response = giga.chat(Chat(messages=messages))
        
        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"Ошибка при работе с GigaChat: {str(e)}")
        return "Не удалось получить ответ от GigaChat. Попробуйте позже."