import os

from cryptography.fernet import Fernet

from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("ENCRYPTION_KEY").encode()


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

        # Возвращаем зашифрованный пароль в формате строки
        return encrypted_password.decode()
    except Exception as e:
        raise ValueError(f"Failed to encrypt password: {e}")