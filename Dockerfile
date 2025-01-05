FROM python:3.10-slim

WORKDIR /app

# Установить системные зависимости
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    default-libmysqlclient-dev \
    sqlite3 \
    redis-tools \
    && apt-get clean

# Устанавливаем зависимости
COPY req.txt .
RUN pip install --no-cache-dir -r req.txt

# Копируем проект и entrypoint
COPY . .
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Не обязательно указывать EXPOSE с переменной окружения,
# можно просто задокументировать EXPOSE 8000
EXPOSE 8000

# Важно: ENTRYPOINT + CMD
ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

