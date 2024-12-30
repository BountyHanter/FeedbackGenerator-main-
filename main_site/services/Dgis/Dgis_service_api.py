import os

import httpx
from dotenv import load_dotenv

load_dotenv()
DGIS_ADDRESS = os.getenv("DGIS_SERVICE_ADDRESS")

# Запрос отзывов


async def link_profile_to_2gis(*, data: dict):
    """
    Ожидаемая структура данных (data):
    {
        "main_user_id": int,        # ID профиля (целое число)
        "username": str,            # Имя пользователя (строка)
        "hashed_password": str      # Хешированный пароль (строка)
    }
    """
    url = f'{DGIS_ADDRESS}/api/create_or_update_user'
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json=data)
        print(response.json())

        if response.status_code == 201:
            return response.json()  # Возвращаем результат
        else:
            raise Exception(f"Error response: {response.status_code}, {response.text}")
