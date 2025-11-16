import os
import logging
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
from backend.config import Config

# Настройка логирования
logger = logging.getLogger(__name__)

def get_giga_response(user_prompt: str, model: str = "GigaChat:latest") -> str:
    """
    Отправляет запрос к GigaChat и возвращает ответ.
    В случае ошибки возвращает сообщение об ошибке.
    """
    # В тестовом режиме возвращаем заглушку
    if Config.TEST_MODE:
        return "Тестовый режим: Здесь будет ответ от GigaChat. Для реальной работы укажите GIGACHAT_CREDENTIALS в .env"

    try:
        credentials = Config.GIGACHAT_CREDENTIALS
        verify_ssl = Config.GIGACHAT_VERIFY_SSL_CERTS

        if not credentials:
            logger.error("Не найдены учетные данные GigaChat в переменных окружения")
            return "Не удалось получить ответ от GigaChat: отсутствуют учетные данные"

        # Формируем параметры для GigaChat
        giga_kwargs = {
            "credentials": credentials,
            "verify_ssl_certs": verify_ssl
        }

        # Проверяем наличие сертификата только если проверка SSL включена
        if verify_ssl:
            cert_path = Config.GIGACHAT_CERT_PATH or "russian_trusted_root_ca.cer"
            if not os.path.exists(cert_path):
                logger.warning(f"Сертификат {cert_path} не найден")
                return "Не удалось получить ответ от GigaChat: отсутствует сертификат"
            giga_kwargs["ca_bundle_file"] = cert_path
        else:
            logger.warning("SSL-валидация для GigaChat отключена (GIGACHAT_VERIFY_SSL_CERTS=false). Это небезопасно!")
        
        # Создаем клиент GigaChat
        giga = GigaChat(**giga_kwargs)
        
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