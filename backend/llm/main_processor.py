# Этот файл будет центральной точкой для вызова любой LLM
from backend.config import Config
from . import yandex_gpt_helper, gigachat_helper, openai_helper

def get_analysis(provider: str, model: str, table_data: str) -> str:
    """
    Выбирает нужную модель и получает от нее аналитический отчет.

    :param provider: Провайдер ("yandex", "giga", "openai")
    :param model: Конкретная модель (например, "gpt-4o", "yandexgpt-lite")
    :param table_data: Строковое представление данных для анализа
    :return: Текстовый отчет от LLM
    """
    # Проверяем тестовый режим
    if Config.TEST_MODE:
        return f"""Тестовый режим активен. Анализ данных:
        
Провайдер: {provider}
Модель: {model}
Размер данных: {len(table_data)} символов

В тестовом режиме возвращается шаблонный ответ без реального анализа.
Для полноценной работы необходимо:
1. Установить TEST_MODE=false в .env
2. Добавить соответствующие API ключи для выбранной модели"""

    # Системный промпт для реального режима
    system_prompt = "Ты — опытный аналитик данных. Твоя задача — кратко проанализировать предоставленные табличные данные, найти в них основные тенденции, аномалии и сделать выводы. Будь краток и точен."
    
    user_prompt = f"{system_prompt}\n\nВот первые строки таблицы для анализа:\n\n{table_data}"

    if provider == "yandex":
        return yandex_gpt_helper.get_yandex_response(user_prompt, model)
    elif provider == "giga":
        return gigachat_helper.get_giga_response(user_prompt, model)
    elif provider == "openai":
        return openai_helper.get_openai_response(user_prompt, model)
    else:
        return f'Ошибка: неизвестный провайдер "{provider}". Доступные провайдеры: yandex, giga, openai.'
