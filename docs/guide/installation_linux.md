# Установка и настройка

## Установка Docker

### Загрузите и установите Docker

```bash title="bash"
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io
```


---

!!! tip "Важно"
    Убедитесь, что Docker установлен, выполнив команду:
    ```bash title="bash"
    docker --version
    ```

---

#### Настройте доступ без `sudo` (только для Linux)
Если вы хотите запускать Docker без `sudo`, выполните:

```bash title="bash"
sudo groupadd docker
sudo usermod -aG docker $USER
```

Затем **перезагрузите систему** или выполните:

```bash title="bash"
newgrp docker
```

---
    
## Установка Docker Compose
    
1. Скачайте последнюю версию Docker Compose:
    ``` bash title="bash"
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose # (1)
    ``` 
   
    1. "download/v2.20.2" - желательно посмотрите в интернете актуальную версию и замените цифры на неё или спросите у ChatGPT 

2. Проверьте установку:
    
   ```bash title="bash"
   docker-compose --version
   ```
    
## Подготовка системы

### Освобождение пора для Redis

Redis по умолчанию использует порт `6379`. Убедитесь, что этот порт не занят другим процессом. Для проверки выполните:

```bash title="bash"
sudo lsof -i :6379
```

Если порт занят, остановите процесс, используя команду:

```bash title="bash"
sudo kill -9 <PID>
```

Где `<PID>` — идентификатор процесса, который занимает порт. Если Redis уже работает на этом порту, убедитесь, что конфигурация в проекте не конфликтует с запущенным экземпляром.

### Настройка `.env` файла

В корневой директории нужно создать `.env` файл и в него вставить необхоидмые данные
```dotenv
ENCRYPTION_KEY=<KEY>

# Порты
MAIN_SERVICE_PORT=
DGIS_MICROSERVICE_PORT=
FRONTEND_PORT=

# Django Суперюзер
DJANGO_SUPERUSER_USERNAME=
DJANGO_SUPERUSER_PASSWORD=
DJANGO_SUPERUSER_EMAIL=

# Django настройки
SECRET_KEY=<KEY>
DEBUG=<Boolean>
```
Здесь вам необходимо вписать порты  
`MAIN_SERVICE_PORT` - Порт основного микросервиса на Django (FeedbackGenerator) (main)    
`DGIS_MICROSERVICE_PORT` - Порт микросервиса который взаимодействует с API 2GIS   
`FRONTEND_PORT` - Порт фронтенд сервиса который будет взаимодействовать с основным микросервисом    

Так же можете изменить данные для суперюзера. Ключи я вышлю в ТГ

## Запуск проекта

### Команда для запуска всех сервисов

Чтобы запустить проект, выполните команду:

```bash
docker-compose up --build
```

Эта команда:
1. Соберёт Docker-образы для всех сервисов.
2. Запустит контейнеры **feedback_generator**, **service_2gis**, **celery_worker** и **redis**.

После успешного запуска вы должны увидеть логи всех сервисов в терминале, например:

```bash
Successfully tagged projfeedbckdocker_service_2gis:latest
Starting projfeedbckdocker_redis_1 ... done
Recreating feedback_generator      ... done
Starting projfeedbckdocker_celery_worker_1 ... done
Attaching to feedback_generator, projfeedbckdocker_redis_1, service_2gis, projfeedbckdocker_celery_worker_1
...
```


## Проверка работоспособности

После запуска проекта выполните следующие шаги для проверки, что все сервисы работают корректно:

### Проверка основных сервисов

1. Убедитесь, что **feedback_generator** запущен и доступен на указанном порту (например, 8000):

    ```bash
    curl http://localhost:8000
    ```
   Ожидается ответ от сервиса (например, JSON или статус 200).

2. Убедитесь, что микросервис **service_2gis** доступен на своём порту (например, 8080):
    ```bash
    curl http://localhost:8080
    ```

   Ожидается ответ (например, JSON или статус 200).

### Проверка Redis

Убедитесь, что Redis работает. Выполните команду:

```bash
docker exec -it projfeedbckdocker_redis_1 redis-cli ping
```

Ожидаемый ответ:

```bash
PONG
```

### Проверка Celery

Убедитесь, что Celery Worker подключён к Redis. В логах Celery (**projfeedbckdocker_celery_worker_1**) вы должны увидеть строку:

```bash
Connected to redis://redis:6379/0
```

### Проверка базы данных

Убедитесь, что миграции применены, и таблицы созданы. Подключитесь к SQLite из контейнера:

```bash
docker exec -it projfeedbckdocker_service_2gis sqlite3 /app/db/db.sqlite3
```

Проверьте таблицы командой:

```bash
.tables
```

Вы должны увидеть список таблиц, включая **user_stats**, **reviews** и другие.

Если все шаги пройдены успешно, проект готов к использованию.
