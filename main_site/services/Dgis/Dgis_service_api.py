import logging
import os
import time

import httpx
from dotenv import load_dotenv

from FeedbackGenerator.utils.mask_data import mask_sensitive_data

load_dotenv()
DGIS_ADDRESS = os.getenv("DGIS_SERVICE_ADDRESS")
logger = logging.getLogger(__name__)


async def link_profile_to_2gis(*, data: dict):
    """
    Ожидаемая структура данных (data):
    {
        "main_user_id": int,        # ID профиля (целое число)
        "username": str,            # Имя пользователя (строка)
        "hashed_password": str      # Хешированный пароль (строка)
    }
    """
    masked_data = mask_sensitive_data(data, ['hashed_password'])
    url = f'{DGIS_ADDRESS}/api/create_or_update_user'
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            start_time = time.monotonic()
            response = await client.post(url, json=data)
            elapsed_time = time.monotonic() - start_time
        except httpx.RequestError as exc:
            elapsed_time = time.monotonic() - start_time
            logger.error('Ошибка при вызове микросервиса 2GIS: сетевая ошибка',
                         extra={'url': url,
                                'method': 'POST',
                                'data': masked_data,
                                'error': str(exc),
                                'elapsed_time': elapsed_time})
            raise
        logger.info('Запрос на микросервис 2GIS',
                    extra={'url': url,
                           'method': 'POST',
                           'data': masked_data,
                           'elapsed_time': elapsed_time,
                           })
        if response.status_code == 201:
            logger.info('Ответ от микросервиса 2GIS',
                        extra={'url': url,
                               'status_code': response.status_code,
                               'elapsed_time': elapsed_time,
                               })
            return response.json()  # Возвращаем результат
        else:
            logger.error('Ошибка при вызове микросервиса 2GIS: некорректный ответ',
                         extra={'url': url,
                                'data': masked_data,
                                'status_code': response.status_code,
                                'headers': response.headers,
                                'error': response.text,
                                'elapsed_time': elapsed_time,
                                })
            raise Exception(f"Error response: {response.status_code}, {response.text}")
