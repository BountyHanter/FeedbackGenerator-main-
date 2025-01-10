import logging
import os

from cryptography.fernet import Fernet

from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("ENCRYPTION_KEY").encode()
logger = logging.getLogger(__name__)


def encrypt_password(password: str) -> str:
    """
    Шифрует пароль с использованием указанного ключа.

    :param password: Пароль в виде строки.
    :return: Зашифрованный пароль в виде строки.
    """
    try:
        # Преобразуем ключ в формат bytes
        cipher = Fernet(KEY)

        # Шифруем пароль
        encrypted_password = cipher.encrypt(password.encode())
        logging.debug('Пароль успешно зашифрован')

        # Возвращаем зашифрованный пароль в формате строки
        return encrypted_password.decode()
    except Exception as e:
        logging.error(f'Ошибка при шифровании пароля пароля {e}')
        raise ValueError(f"Failed to encrypt password: {e}")
