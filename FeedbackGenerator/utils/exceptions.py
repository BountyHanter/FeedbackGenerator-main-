from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    # Вызов стандартного обработчика исключений DRF
    response = exception_handler(exc, context)

    if response is not None:
        # Возвращаем JSON-ответ, если DRF обработал исключение
        return Response(
            {
                "error": response.data.get("detail", "Произошла ошибка"),
                "status_code": response.status_code,
            },
            status=response.status_code,
        )

    # Если исключение не обработано, например, 404
    return Response(
        {"error": "Ресурс не найден", "status_code": 404},
        status=status.HTTP_404_NOT_FOUND,
    )
