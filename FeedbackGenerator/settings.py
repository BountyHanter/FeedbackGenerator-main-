"""
Django settings for FeedbackGenerator project.

Generated by 'django-admin startproject' using Django 5.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""
import logging
import os
from datetime import datetime
from pathlib import Path

from django.contrib import staticfiles
from dotenv import load_dotenv
from pythonjsonlogger.json import JsonFormatter

from FeedbackGenerator.utils.mask_data import MaskingFilter

load_dotenv()


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    "corsheaders",
    "rest_framework",
    'drf_spectacular',
    "main_site.apps.MainSiteConfig"
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

MIDDLEWARE.insert(0, 'corsheaders.middleware.CorsMiddleware')

ROOT_URLCONF = 'FeedbackGenerator.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'EXCEPTION_HANDLER': 'FeedbackGenerator.utils.exceptions.custom_exception_handler',

}

WSGI_APPLICATION = 'FeedbackGenerator.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'ru'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/2gis_accounts/'
LOGOUT_REDIRECT_URL = '/login/'

# Время жизни сессии в секундах (7 дней = 604800 секунд)
SESSION_COOKIE_AGE = 604800

# Автоматически обновлять время сессии при каждом запросе (по желанию)
SESSION_SAVE_EVERY_REQUEST = True

FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5 MB, например

ASGI_APPLICATION = 'finApplications.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}

CORS_ALLOWED_ORIGINS = [
    os.getenv("ALLOWED_ORIGIN"),  # Адрес фронта
]

CORS_ALLOW_CREDENTIALS = True  # Для передачи cookies/токенов аутентификации

CSRF_TRUSTED_ORIGINS = [
    os.getenv("ALLOWED_ORIGIN"),  # Адрес фронта
]
CSRF_COOKIE_HTTPONLY = False  # Чтобы фронт мог читать токен из cookie


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,  # Не отключать существующие логгеры
    'formatters': {
        'json': {
            '()': JsonFormatter,
            'fmt': (
                '%(asctime)s %(name)s %(levelname)s %(message)s '
                '%(filename)s %(lineno)d %(funcName)s %(module)s'
            ),
            'json_ensure_ascii': False,
        },
        'console': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(data)s',
        },
    },
    'filters': {
        'mask_sensitive': {
            '()': MaskingFilter,
            'fields_to_mask': ['hashed_password'],
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
            'level': 'DEBUG' if DEBUG else 'WARNING',  # Уровень зависит от DEBUG
        },
        'file': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filters': ['mask_sensitive'],  # Маскируем данные
            'formatter': 'json',
            'level': 'DEBUG',
            'filename': os.path.join(BASE_DIR, 'logs', f'app_{datetime.now().strftime("%Y-%m-%d")}.log'),
            'when': 'W0',
            'interval': 1,
            'backupCount': 4,
            'encoding': 'utf-8',
            'utc': False,
        },
    },
    'loggers': {
        '': {  # Корневой логгер
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'main_site': {  # Логгер для вашего приложения
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
