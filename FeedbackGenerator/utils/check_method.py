from rest_framework.response import Response
from rest_framework import status


def check_method(request, allowed_methods):
    """
    Проверяет, разрешён ли HTTP-метод для данного действия.
    Если метод не разрешён, возвращает Response с кодом 405.
    """
    if request.method not in allowed_methods:
        return Response(
            {"error": f"Метод {request.method} не разрешён. Разрешённые методы: {', '.join(allowed_methods)}."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    return None
