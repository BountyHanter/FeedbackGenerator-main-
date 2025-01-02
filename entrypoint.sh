#!/bin/sh

# Выполняем миграции
echo "Applying database migrations..."
python manage.py migrate --no-input

# Проверяем и создаём суперпользователя, если его нет
echo "Checking for superuser..."
python manage.py shell <<EOF
from django.contrib.auth import get_user_model;
import os;

User = get_user_model();
username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin');
email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@example.com');
password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'admin');

try:
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username=username, email=email, password=password)
        print(f"Superuser '{username}' created successfully.")
    else:
        print(f"Superuser '{username}' already exists.")
except Exception as e:
    print(f"Error creating superuser: {e}")
EOF

# Запускаем сервер
echo "Starting server..."
exec "$@"

