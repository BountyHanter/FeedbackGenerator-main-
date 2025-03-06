import logging
import os
import time

import httpx
from dotenv import load_dotenv
from typing import Dict

from FeedbackGenerator.utils.mask_data import mask_sensitive_data

load_dotenv()
FLAMP_ADDRESS = os.getenv("FLAMP_SERVICE_ADDRESS")
logger = logging.getLogger(__name__)


async def link_profile_to_flamp(*, data: dict):
    """
    Ожидаемая структура данных (data):
    {
        "main_user_id": int,        # ID профиля (целое число) → отправляем как owner_id
        "username": str,            # Имя пользователя (строка)
        "hashed_password": str      # Хешированный пароль (строка)
    }
    """
    # Меняем main_user_id → owner_id
    owner_id = data.pop("main_user_id")
    data["owner_id"] = owner_id  # Теперь в data есть owner_id

    masked_data = mask_sensitive_data(data, ["hashed_password"])

    # Формируем данные для PATCH (убираем owner_id, потому что он там не нужен)
    update_data: Dict[str, str] = {}
    if "username" in data:
        update_data["username"] = data["username"]
    if "hashed_password" in data:
        update_data["hashed_password"] = data["hashed_password"]

    # Если нет данных для обновления → сразу идём на POST
    if not update_data:
        logger.info("Нет данных для обновления, сразу создаём пользователя")
        return await create_user(data, masked_data)

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            # 1. Пытаемся обновить пользователя (PATCH)
            update_url = f"{FLAMP_ADDRESS}/api/users/{owner_id}/update"
            start_time = time.monotonic()
            response = await client.patch(update_url, json=update_data)
            elapsed_time = time.monotonic() - start_time

            if response.status_code == 200:
                logger.info("Пользователь успешно обновлён")
                return response.json()

            elif response.status_code == 404:
                logger.warning("Пользователь не найден, создаём нового...")

            else:
                logger.error(f"Ошибка при обновлении пользователя: {response.status_code}, {response.text}")
                raise Exception(response.text)

            # 2. Если 404, создаем нового пользователя
            return await create_user(data, masked_data)

        except httpx.RequestError as exc:
            elapsed_time = time.monotonic() - start_time
            logger.error("Ошибка при запросе к Flamp",
                         extra={"url": update_url,
                                "method": "PATCH",
                                "data": masked_data,
                                "error": str(exc),
                                "elapsed_time": elapsed_time})
            raise


async def create_user(data: dict, masked_data: dict):
    """Создаёт пользователя в Flamp через POST-запрос"""
    create_url = f"{FLAMP_ADDRESS}/api/users/create"

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            start_time = time.monotonic()
            response = await client.post(create_url, json=data)
            elapsed_time = time.monotonic() - start_time

            if response.status_code == 201:
                logger.info("Пользователь успешно создан")
                return response.json()
            else:
                logger.error(f"Ошибка при создании пользователя: {response.status_code}, {response.text}")
                raise Exception(f"Error creating user: {response.status_code}, {response.text}")

        except httpx.RequestError as exc:
            logger.error("Ошибка при запросе к Flamp",
                         extra={"url": create_url,
                                "method": "POST",
                                "data": masked_data,
                                "error": str(exc),
                                "elapsed_time": elapsed_time})
            raise
