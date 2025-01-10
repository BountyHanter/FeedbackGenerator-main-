import logging

from rest_framework.response import Response
from rest_framework import status

from FeedbackGenerator.utils.logging_templates import log_request_not_allowed

logger = logging.getLogger(__name__)


def check_method(request, allowed_methods):
    """
    Проверяет, разрешён ли HTTP-метод для данного действия.
    Если метод не разрешён, возвращает Response с кодом 405.
    """
    if request.method not in allowed_methods:
        log_request_not_allowed(request, 'method_not_allowed')
        return Response(
            {"error": f"Метод {request.method} не разрешён. Разрешённые методы: {', '.join(allowed_methods)}."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    return None
