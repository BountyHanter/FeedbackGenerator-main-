import logging
import os

import httpx
from asgiref.sync import async_to_sync
from dotenv import load_dotenv
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from FeedbackGenerator.utils.logging_templates import log_request_not_allowed, log_request_missing_items, \
    log_request_to_service, log_response, log_error_response, log_successful_response, log_unexpected_error

load_dotenv()

FLAMP_SERVER_URL = os.getenv("FLAMP_SERVICE_ADDRESS")

logger = logging.getLogger(__name__)


class APIFlampProfiles(APIView):
    """
    Синхронный вариант вью, но сами запросы к внешнему сервису выполняются асинхронно
    и оборачиваются в async_to_sync, чтобы мы могли дождаться их результата.
    В данном вью пристутствуют GET эндпоинты - получение отзывов(reviews), получение статистики(stats),
    и POST эндпоинт - запрос сбора статистики (trigger_stats)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, action=None):
        """
        Синхронный метод GET, который внутри вызывает нужные методы для получения отзывов или статистики
        (fetch_reviews / fetch_stats)
        """
        if action == 'reviews':
            return self.fetch_reviews(request)
        elif action == 'stats':
            return self.fetch_stats(request)
        else:
            log_request_not_allowed(request, action, 'GET')

            return Response(
                {'error': 'Метод не разрешён'},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )

    def post(self, request, action=None):
        """
        Метод POST который внутри только инициирует сбор статистики используя метод - trigger_stats_collection
        """
        if action == 'trigger_stats':
            return self.trigger_stats_collection(request)
        else:
            log_request_not_allowed(request, action, 'POST')

            return Response(
                {'error': 'Метод не разрешён'},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
    # ---------------------------
    # Синхронные методы для GET
    # ---------------------------

    def fetch_reviews(self, request):
        """
        Получение списка отзывов для филиала Flamp.

        Этот метод обрабатывает GET-запросы для получения отзывов от внешнего микросервиса Flamp.
        Проверяются обязательные параметры, формируются запросы к микросервису и фильтруются данные ответа.

        :param request: Объект HTTP-запроса, содержащий параметры:
            - filial_id (int): ID филиала 2GIS (обязательный).
            - limit (int): Лимит количества отзывов (необязательный, по умолчанию 20).
            - offset_date (str): Дата смещения для пагинации (необязательный).
            - rating (int): Рейтинг отзывов для фильтрации (необязательный).
            - without_answer (bool): Флаг, показывающий, выводить ли только отзывы без ответа (необязательный).
            - is_favorite (bool): Флаг, показывающий, выводить ли только избранные отзывы (необязательный).

        :return: Объект Response с JSON-ответом:
            - reviews_count (int): Кол-во отзывов которое вернул микросервис.
            - reviews (list): Список отфильтрованных отзывов с полями:
                - id (int): ID отзыва.
                - filial_id (int): ID филиала в Flamp
                - rating (int): Рейтинг отзыва.
                - text (str): Текст отзыва.
                - created_at (str): Дата создания отзыва.
                - user_name (str): Имя пользователя, оставившего отзыв (будет Null так как доступен по отдельному запросу).
                - comments_count (int): Количество комментариев к отзыву.
                - likes_count (int): Количество лайков у отзыва.
                - photos (list): Список фотографий (То же что и с именем).
                - is_favorite (bool): Флаг избранного отзыва.

        :raises ValueError: Если ответ от микросервиса имеет неожиданный формат.
        :raises RequestError: Если произошла ошибка сети при запросе к микросервису.
        :raises Exception: Если возникли неожиданные ошибки.
        """

        required_params = ['filial_id']
        missing_params = [param for param in required_params if not request.GET.get(param)]

        if missing_params:
            log_request_missing_items(request, missing_params, 'params', 'missing_params')
            return Response(
                {'error': f"Отсутствуют обязательные параметры: {', '.join(missing_params)}"},
                status=400
            )

        filial_id = request.GET.get('filial_id')
        limit = request.GET.get('limit')
        offset_date = request.GET.get('offset_date')
        rating = request.GET.get('ratings')
        without_answer = request.GET.get('without_answer')
        is_favorite = request.GET.get('is_favorite')

        logger.debug("Данные в запросе",
                     extra={
                         "limit": limit,
                         "offset_date": offset_date,
                         "rating": rating,
                         "without_answer": without_answer,
                         "is_favorite": is_favorite,
                     }
                     )

        service_url = f"{FLAMP_SERVER_URL}/api/reviews/{filial_id}"

        params = {
            "filial_id": filial_id,
        }
        if limit:
            params["limit"] = limit
        if offset_date:
            params["offset_date"] = offset_date
        if rating:
            params["rating"] = rating
        if without_answer:
            params["without_answer"] = True
        if is_favorite:
            params["is_favorite"] = True

        log_request_to_service("Flamp", service_url, 'GET', params=params)

        try:
            response_data = async_to_sync(self._async_get)(service_url)

            # Если _async_get вернул DRF Response (ошибка)
            if isinstance(response_data, Response):
                log_error_response(
                    service_name='Микросервис Flamp', service_url=service_url, method="GET",
                    params={"filial_id": filial_id}, response=response_data,
                )
                return response_data

            # Если ответ - это JSON-словарь
            if isinstance(response_data, dict):
                log_successful_response("Flamp", service_url, None, response_data)

                # Проверяем, если в ответе явно указано, что отзывов нет
                if response_data.get("message") == "Нет отзывов" or not response_data.get("data"):
                    log_response(request=request, request_name="Отзывы Flamp с микросервиса",
                                 result=None, status="Нет отзывов",
                                 )
                    return Response({"status": "Нет отзывов"}, status=200)

                # Если данные есть, обрабатываем их
                reviews = response_data.get("data", [])

                result = {
                    "reviews_count": len(reviews),
                    "reviews": reviews,  # Можно передавать их как есть, если нужно
                }

                log_response(request=request, request_name="Отзывы Flamp с микросервиса",
                             result=result,
                             status="Данные собраны",
                             )

                return Response({"status": "Данные собраны", "result": result}, status=200)

        except httpx.RequestError as exc:
            log_error_response(
                service_name='Микросервис Flamp', service_url=service_url, method='GET',
                params={"filial_id": filial_id}, exception=exc
            )
            return Response({"error": "Ошибка при подключении к сервису"}, status=500)

        except Exception as e:
            log_unexpected_error(
                request=request,
                service_name='Микросервис Flamp',
                service_url=service_url,
                method="GET",
                params={"filial_id": filial_id},
                exception=str(e)
            )
            return Response({"error": "Внутренняя ошибка сервера"}, status=500)

    def fetch_stats(self, request):































    # --------------------------------------------------
    # Вспомогательные асинхронные методы для запросов
    # --------------------------------------------------
    async def _async_get(self, url, params=None):
        """
        Асинхронный GET-запрос, возвращает либо словарь (response.json()),
        либо DRF Response (при ошибке).
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()

                logger.info(
                    "Успешный GET-запрос к микросервису",
                    extra={
                        "url": url,
                        "method": "GET",
                        "params": params,
                        "status_code": response.status_code,
                    }
                )
                return response.json()
        except httpx.TimeoutException as exc:
            logger.error(
                "Тайм-аут при запросе к микросервису",
                extra={
                    "url": url,
                    "method": "GET" if "GET" in str(exc) else "POST",
                    "params": params if "GET" in str(exc) else None,
                    "error": str(exc),
                }
            )
            return Response({"error": "Тайм-аут подключения к микросервису Flamp"}, status=504)

        except httpx.RequestError as exc:
            logger.error(
                "Сетевая ошибка при GET-запросе к микросервису",
                extra={
                    "url": url,
                    "method": "GET",
                    "params": params,
                    "error": str(exc),
                }
            )
            return Response({"error": "Ошибка подключения к микросервису Flamp"}, status=500)
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Ошибка статуса HTTP при GET-запросе к микросервису",
                extra={
                    "url": url,
                    "method": "GET",
                    "params": params,
                    "status_code": exc.response.status_code,
                    "response_text": exc.response.text,
                }
            )
            return Response({"error": f"Ошибка микросервиса Flamp: {exc.response.status_code}"},
                            status=exc.response.status_code)

    async def _async_post(self, url, payload):
        """
        Асинхронный POST-запрос, возвращает сам объект response (чтобы мы взяли .status_code и т.п.),
        либо DRF Response (при ошибке).
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload)

                logger.info(
                    "Успешный POST-запрос к микросервису",
                    extra={
                        "url": url,
                        "method": "POST",
                        "payload": payload,
                        "status_code": response.status_code,
                    }
                )
                return response

        except httpx.TimeoutException as exc:
            logger.error(
                "Тайм-аут при запросе к микросервису",
                extra={
                    "url": url,
                    "method": "GET" if "GET" in str(exc) else "POST",
                    "payload": payload if "POST" in str(exc) else None,
                    "error": str(exc),
                }
            )
            return Response({"error": "Тайм-аут подключения к микросервису Flamp"}, status=504)

        except httpx.RequestError as exc:
            logger.error(
                "Сетевая ошибка при POST-запросе к микросервису",
                extra={
                    "url": url,
                    "method": "POST",
                    "payload": payload,
                    "error": str(exc),
                }
            )
            return Response({"error": "Ошибка подключения к микросервису Flamp"}, status=500)
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Ошибка статуса HTTP при POST-запросе к микросервису",
                extra={

                    "url": url,
                    "method": "POST",
                    "payload": payload,
                    "status_code": exc.response.status_code,
                    "response_text": exc.response.text,
                }
            )
            return Response({"error": f"Ошибка микросервиса Flamp: {exc.response.status_code}"},
                            status=exc.response.status_code)
