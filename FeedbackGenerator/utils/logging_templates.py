import logging

logger = logging.getLogger(__name__)


def log_request_not_allowed(request, action: str, method: str):
    """
    Логирует предупреждения, связанные с неразрешённым запросом.

    :param request: Объект HTTP-запроса.
    :param action: Действие, которое пытался выполнить пользователь.
    :param method: Причина, по которой запрос не разрешён.
    """
    logger.warning(
        "Метод не разрешён для действия",
        extra={
            "path": request.path,
            "method": request.method,
            "user_id": request.user.id,
            "username": request.user.username,
            "action": action,
            "reason": f"{method} запрос для действия не поддерживается",
        },
        stacklevel=2,
    )


def log_request_missing_items(request, missing_items: list, item_type: str, status: str):
    """
    Логирует предупреждения, связанные с отсутствующими элементами (полями или параметрами).

    :param request: Объект HTTP-запроса.
    :param missing_items: Список отсутствующих элементов (например, полей или параметров).
    :param item_type: Тип элементов (например, "поля" или "параметры").
    :param status: Статус, описывающий тип предупреждения.
    """
    logger.warning(
        'Не переданы необходимые элементы',
        extra={
            "missing_items": missing_items,
            "item_type": item_type,
            "path": request.path,
            "method": request.method,
            "status": status,
        },
        stacklevel=2,
    )


def log_successful_response(service_name, service_url, params, response_data):
    """
    Логирует успешный ответ от внешнего сервиса.

    :param service_name: Имя сервиса.
    :param service_url: URL, к которому был сделан запрос.
    :param params: Параметры запроса.
    :param response_data: Данные успешного ответа.
    """
    logger.info(
        f"Успешный ответ от микросервиса {service_name}",
        extra={
            "service_url": service_url,
            "params": params,
            "response_keys": list(response_data.keys()),  # Логируем только ключи ответа
        },
        stacklevel=2,
    )


def log_request_to_service(service_name, service_url, method, headers=None, params=None, payload=None):
    """
    Логирует информацию о запросе к внешнему сервису.

    :param service_name: Имя сервиса.
    :param service_url: URL, к которому выполняется запрос.
    :param method: HTTP-метод запроса (GET, POST и т.д.).
    :param headers: Заголовки запроса (если есть).
    :param params: Параметры запроса (если есть).
    :param payload: Тело запроса (если есть).
    """
    logger.info(
        f"Выполняется {method} запрос к микросервису {service_name}",
        extra={
            "service_url": service_url,
            "method": method,
            "headers": headers,
            "params": params,
            "payload": payload,
        },
        stacklevel=2,
    )


def log_response(*, request, request_name, **kwargs):
    """
    Логирует информацию о запросах и ответах, связанных с 2GIS.

    :param request: HTTP-запрос (для получения пути, метода и пользователя).
    :param request_name: Название запроса.
    :param kwargs: Дополнительные данные для логирования (результаты, ошибки и т.д.).
    """
    logger.info(
        f"HTTP запрос: {request_name}",
        extra={
            "path": request.path,
            "method": request.method,
            "user_id": request.user.id,
            "username": request.user.username,
            **kwargs  # Добавляем дополнительные данные
        },
        stacklevel=2,
    )


def log_error_response(*, service_name, service_url=None, method=None, headers=None, params=None, payload=None,
                       response=None, exception=None, request=None, exc_info=False, **kwargs):
    """
    Логирует ошибочный ответ.

    :param service_name: Имя сервиса.
    :param service_url: URL, к которому был сделан запрос.
    :param method: HTTP-метод запроса.
    :param headers: Заголовки запроса.
    :param params: Параметры запроса.
    :param payload: Тело запроса.
    :param response: Ответ от сервиса.
    :param exception: Исключение.
    :param exc_info: Если True, логируется информация об исключении (трассировка).
    :param request: Django HTTP-запрос (если используется для внутреннего вызова).
    """
    log_data = {
        "service_name": service_name,
        "service_url": service_url,
        "method": method,
        "headers": headers,
        "params": params,
        "payload": payload,
    }
    if response:
        log_data.update({
            "status_code": response.status_code,
            "response_data": response.json() if response.content else None,
        })
    if exception:
        log_data.update({"error": str(exception)})
    if request:
        log_data.update({
            "path": request.path,
            "method": request.method,
            "user_id": request.user.id,
            "username": request.user.username,
        })

    log_data.update(kwargs)

    logger.warning(f"Ошибка при вызове: {service_name}", extra=log_data, exc_info=exc_info, stacklevel=2, )


def log_unexpected_error(*, request, service_name, service_url, exception, exc_info=False, **kwargs):
    logger.exception(
        f"Неожиданная ошибка при вызове {service_name}",
        extra={
            "path": request.path,
            "method": request.method,
            "service_url": service_url,
            "error": exception,
            **kwargs
        },
        exc_info=exc_info,
        stacklevel=2,
    )
