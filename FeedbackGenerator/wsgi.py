"""
WSGI config for FeedbackGenerator project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""
import logging
import os

from django.core.wsgi import get_wsgi_application

from FeedbackGenerator.settings import DEBUG, ALLOWED_HOSTS, DATABASES, STATIC_ROOT, SECRET_KEY, CORS_ALLOWED_ORIGINS, \
    CSRF_TRUSTED_ORIGINS

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FeedbackGenerator.settings')

application = get_wsgi_application()

# Получаем корневой логгер
logger = logging.getLogger(__name__)

if DEBUG:
    # Логируем начальную конфигурацию
    logger.debug(f"DEBUG: {DEBUG}")
    logger.debug(f"ALLOWED_HOSTS: {ALLOWED_HOSTS}")
    logger.debug(f"DATABASE ENGINE: {DATABASES['default']['ENGINE']}")
    logger.debug(f"DATABASE NAME: {DATABASES['default']['NAME']}")
    logger.debug(f"STATIC_ROOT: {STATIC_ROOT}")
    logger.debug(f"SECRET_KEY: {'Скрыто' if SECRET_KEY == 'default-secret-key' else 'Установлено'}")
    logger.debug(f"CORS_ALLOWED_ORIGINS: {CORS_ALLOWED_ORIGINS}")
    logger.debug(f"CSRF_TRUSTED_ORIGINS: {CSRF_TRUSTED_ORIGINS}")