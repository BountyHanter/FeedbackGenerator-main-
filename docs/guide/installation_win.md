# Установка Docker и Docker Compose на Windows

## 1️⃣ Установка Docker

Docker предоставляет удобный способ работы с контейнерами. На Windows используется **Docker Desktop**.

!!! info "Что такое Docker?"
    Docker – это инструмент для создания, развертывания и управления контейнерами. Он позволяет запускать приложения в изолированной среде.

### 🔹 **Шаг 1. Скачивание и установка**
1. Перейдите на официальный сайт [Docker Desktop](https://www.docker.com/products/docker-desktop/){target=_blank}.
2. Выберите версию для **Windows** и скачайте установочный файл.
3. Запустите установку и следуйте инструкциям мастера установки.

!!! warning "Требования к системе"
    - Windows 10/11 (64-bit) с поддержкой WSL 2 или Hyper-V
    - Включенная виртуализация в BIOS
    - 4 ГБ ОЗУ или больше

### 🔹 **Шаг 2. Проверка установки**
После установки откройте терминал **PowerShell** и выполните команду:

```bash title="PowerShell"
docker --version
```

!!! tip "Важно"
    Если команда не работает, убедитесь, что Docker Desktop запущен.

## 2️⃣ Установка Docker Compose

Docker Compose позволяет управлять многоконтейнерными приложениями с помощью одного файла **docker-compose.yml**.

### 🔹 **Шаг 1. Проверка наличия Docker Compose**
Если у вас установлен **Docker Desktop**, то Docker Compose уже включён. Проверьте это командой:

```bash title="PowerShell"
docker compose version
```

Если команда сработала, **ничего дополнительно устанавливать не нужно**.

!!! success "Docker Compose уже установлен!"
    Если у вас Docker Desktop, то Docker Compose уже встроен, и его не нужно устанавливать отдельно.

### 🔹 **Шаг 2. Установка Docker Compose вручную** (если у вас только CLI)
Если вы используете только **Docker CLI** без Docker Desktop, выполните следующие шаги:

1. Перейдите на [страницу релизов](https://github.com/docker/compose/releases){target=_blank} и скачайте последнюю версию для **Windows x86_64**.
2. Переместите скачанный файл в `C:\Program Files\Docker\`.
3. Добавьте путь к `docker-compose.exe` в **переменные среды Windows** (`PATH`).
4. Проверьте установку командой:

```bash title="PowerShell"
docker-compose --version
```

!!! warning "Обратите внимание!"
    - `docker-compose` (с дефисом) – старая версия.
    - `docker compose` (без дефиса) – новая версия.
    Используйте `docker compose`, если у вас Docker Desktop.

## 3️⃣ Итог
После установки Docker и Docker Compose вы готовы к работе с контейнерами на Windows. 🚀

!!! example "Пример использования Docker Compose"
    Создайте файл `docker-compose.yml` и запустите контейнер:
    
    ```yaml title="docker-compose.yml"
    version: '3'
    services:
      web:
        image: nginx
        ports:
          - "80:80"
    ```
    
    Запустите команду:
    ```bash title="PowerShell"
    docker compose up -d
    ```
    Теперь ваш контейнер с Nginx работает!