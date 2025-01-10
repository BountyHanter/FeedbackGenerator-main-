import json
import logging
import os

import httpx
from asgiref.sync import async_to_sync
from dotenv import load_dotenv
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from FeedbackGenerator.utils.logging_templates import log_request_not_allowed, log_request_missing_items, \
    log_successful_response, log_request_to_service, log_response, log_error_response, log_unexpected_error
from main_site.models.Dgis_models import DgisFilial

load_dotenv()

DGIS_SERVER_URL = os.getenv("DGIS_SERVICE_ADDRESS")

logger = logging.getLogger(__name__)


class APIDGISProfiles(APIView):
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
        Получение списка отзывов для филиала 2GIS.

        Этот метод обрабатывает GET-запросы для получения отзывов от внешнего микросервиса 2GIS.
        Проверяются обязательные параметры, формируются запросы к микросервису и фильтруются данные ответа.

        :param request: Объект HTTP-запроса, содержащий параметры:
            - main_user_id (int): ID основного пользователя (обязательный).
            - filial_id (int): ID филиала 2GIS (обязательный).
            - limit (int): Лимит количества отзывов (необязательный, по умолчанию 20).
            - offset_date (str): Дата смещения для пагинации (необязательный).
            - rating (int): Рейтинг отзывов для фильтрации (необязательный).
            - without_answer (bool): Флаг, показывающий, выводить ли только отзывы без ответа (необязательный).
            - is_favorite (bool): Флаг, показывающий, выводить ли только избранные отзывы (необязательный).

        :return: Объект Response с JSON-ответом:
            - reviews (list): Список отфильтрованных отзывов с полями:
                - id (int): ID отзыва.
                - rating (int): Рейтинг отзыва.
                - text (str): Текст отзыва.
                - dateCreated (str): Дата создания отзыва.
                - name (str): Имя пользователя, оставившего отзыв.
                - commentsCount (int): Количество комментариев к отзыву.
                - likesCount (int): Количество лайков у отзыва.
                - photos (list): Список фотографий (если есть).
                - is_favorite (bool): Флаг избранного отзыва.
            - count (int): Общее количество отзывов.
            - filial_id (int): ID филиала.

        :raises ValueError: Если ответ от микросервиса имеет неожиданный формат.
        :raises RequestError: Если произошла ошибка сети при запросе к микросервису.
        :raises Exception: Если возникли неожиданные ошибки.
        """
        required_params = ['main_user_id', 'filial_id']
        missing_params = [param for param in required_params if not request.GET.get(param)]

        if missing_params:
            log_request_missing_items(request, missing_params, 'params', 'missing_params')
            return Response(
                {'error': f"Отсутствуют обязательные параметры: {', '.join(missing_params)}"},
                status=400
            )

        main_user_id = request.GET.get('main_user_id')
        filial_id = request.GET.get('filial_id')
        limit = request.GET.get('limit', 20)
        offset_date = request.GET.get('offset_date')
        rating = request.GET.get('rating')
        without_answer = request.GET.get('without_answer')
        is_favorite = request.GET.get('is_favorite')

        logger.debug("Данные в запросе",
                     extra={
                         "main_user_id": main_user_id,
                         "filial_id": filial_id,
                         "limit": limit,
                         "offset_date": offset_date,
                         "rating": rating,
                         "without_answer": without_answer,
                         "is_favorite": is_favorite,
                     }
                     )

        service_url = f"{DGIS_SERVER_URL}/api/get_reviews"

        params = {
            "main_user_id": main_user_id,
            "filial_id": filial_id,
            "limit": limit,
        }
        if offset_date:
            params["offset_date"] = offset_date
        if rating:
            params["rating"] = rating
        if without_answer:
            params["without_answer"] = True
        if is_favorite:
            params["is_favorite"] = True

        log_request_to_service("2GIS", service_url, 'GET', params=params)

        try:
            # Выполняем асинхронный запрос через async_to_sync
            response_data = async_to_sync(self._async_get)(service_url, params)

            # Если _async_get вернёт объект DRF-Response (ошибка)
            if isinstance(response_data, Response):
                log_error_response(
                    service_name='Микросервис 2GIS',
                    service_url=service_url,
                    method='GET',
                    params=params,
                    response=response_data
                )
                return response_data

            # Если ответ валидный (например, словарь)
            if isinstance(response_data, dict):
                log_successful_response("2GIS", service_url, params, response_data)

                reviews = response_data.get("reviews", [])
                filtered_reviews = []

                for review in reviews:
                    photos = review.get("photos")
                    if isinstance(photos, list) and all(isinstance(photo, str) for photo in photos):
                        filtered_photos = photos
                    elif isinstance(photos, list):
                        filtered_photos = [
                            photo.get("preview_urls", {}).get("url") for photo in photos if isinstance(photo, dict)
                        ]
                    else:
                        filtered_photos = None

                    filtered_review = {
                        "id": review.get("id"),
                        "rating": (review.get("rating", 0)),
                        "text": review.get("text", "Без текста"),
                        "dateCreated": review.get("created_at"),
                        "name": review.get("user_name"),
                        "commentsCount": review.get("comments_count", 0),
                        "likesCount": review.get("likes_count", 0),
                        "photos": filtered_photos,
                        "is_favorite": review.get('is_favorite'),
                    }
                    filtered_reviews.append(filtered_review)

                logger.debug(f"Отзывы",
                             extra={"filtred_reviews": filtered_reviews}
                             )

                log_response(request=request, request_name="Отзывы 2GIS с микросервиса",
                             review_count=len(filtered_reviews),
                             filial_id=filial_id
                             )

                return Response(
                    {
                        "reviews": filtered_reviews,
                        "count": len(filtered_reviews),
                        "filial_id": filial_id
                    },
                    status=200
                )

            # Если формат ответа неожиданный
            log_unexpected_error(
                request=request,
                service_name='Микросервис 2GIS',
                service_url=service_url,
                method='GET',
                params=params,
                response_type=type(response_data).__name__,
                response_data=response_data,
                exception=None
            )

            raise ValueError("Неожиданный формат ответа от микросервиса 2GIS")

        except httpx.RequestError as exc:
            # Обработка сетевых ошибок
            log_error_response(service_name="Микросервис 2GIS", service_url=service_url, method="GET",
                               params=params, exception=exc)
            raise

        except Exception as e:
            # Обработка неожиданных ошибок
            log_unexpected_error(
                request=request,
                service_name='Микросервис 2GIS',
                service_url=service_url,
                method="GET",
                params=params,
                exception=str(e)
            )
            raise

    def fetch_stats(self, request):
        """
        Получение статистики филиала 2GIS.

        Этот метод обрабатывает GET-запросы для получения статистики по указанному филиалу из внешнего микросервиса 2GIS.
        Проверяется наличие обязательных параметров, отправляется запрос к сервису и обрабатывается ответ.

        :param request: Объект HTTP-запроса, содержащий параметры:
            - filial_id (int): ID филиала 2GIS (обязательный).

        :return: Объект Response с JSON-ответом:
            - status (str): Статус ответа ("Данных нет", "В очереди", "В процессе", "Данные собраны").
            - result (dict, optional): Результаты статистики, если они собраны:
                - one_star_count (int): Количество оценок на 1 звезду.
                - one_star_percent (float): Процент оценок на 1 звезду.
                - two_stars_count (int): Количество оценок на 2 звезды.
                - two_stars_percent (float): Процент оценок на 2 звезды.
                - three_stars_count (int): Количество оценок на 3 звезды.
                - three_stars_percent (float): Процент оценок на 3 звезды.
                - four_stars_count (int): Количество оценок на 4 звезды.
                - four_stars_percent (float): Процент оценок на 4 звезды.
                - five_stars_count (int): Количество оценок на 5 звезд.
                - five_stars_percent (float): Процент оценок на 5 звезд.
                - rating (float): Средний рейтинг.
                - count_reviews (int): Общее количество отзывов.

        :raises RequestError: Если произошла ошибка сети при запросе к микросервису.
        :raises ValueError: Если ответ от микросервиса имеет неожиданный формат.
        :raises Exception: Если возникли неожиданные ошибки.

        Примечания:
            - Если параметр filial_id отсутствует, возвращается статус 400.
            - Если данные еще собираются, возвращаются статусы "В очереди" или "В процессе".
        """
        filial_id = request.GET.get('filial_id')

        # Проверка обязательного параметра
        if not filial_id:
            log_request_missing_items(request, ['filial_id'], 'params', 'missing_params')
            return Response({"error": "Отсутствует обязательный параметр - filial_id"}, status=400)

        service_url = f"{DGIS_SERVER_URL}/api/stats/{filial_id}"

        # Логируем запрос
        log_request_to_service("2GIS", service_url, 'GET', params={"filial_id": filial_id})

        try:
            response_data = async_to_sync(self._async_get)(service_url)

            # Если _async_get возвращает DRF-Response (ошибка)
            if isinstance(response_data, Response):
                if response_data.status_code == 404:
                    log_response(request=request, request_name="Отзывы 2GIS с микросервиса",
                                 result=None, status="Данных нет",
                                 )

                    return Response({"status": "Данных нет"}, status=200)

                log_error_response(
                    service_name='Микросервис 2GIS', service_url=service_url, method="GET",
                    params={"filial_id": filial_id}, response=response_data,
                )
                return response_data

            if isinstance(response_data, dict):
                log_successful_response("2GIS", service_url, None, response_data)

                # Обработка специфичных статусов
                status_mapping = {
                    "pending": "В очереди",
                    "in_progress": "В процессе"
                }

                if response_data.get("status") in status_mapping:
                    status_message = status_mapping[response_data.get("status")]

                    log_response(request=request, request_name="Отзывы 2GIS с микросервиса",
                                 result=None, status=status_message,
                                 )

                    return Response({"status": status_message}, status=200)

                # Обработка успешного ответа: считаем проценты
                data = response_data
                count_reviews = data.get("count_reviews") or 1  # На случай деления на 0
                result = {
                    "one_star_count": data["one_star"],
                    "one_star_percent": round((data["one_star"] / count_reviews) * 100),
                    "two_stars_count": data["two_stars"],
                    "two_stars_percent": round((data["two_stars"] / count_reviews) * 100),
                    "three_stars_count": data["three_stars"],
                    "three_stars_percent": round((data["three_stars"] / count_reviews) * 100),
                    "four_stars_count": data["four_stars"],
                    "four_stars_percent": round((data["four_stars"] / count_reviews) * 100),
                    "five_stars_count": data["five_stars"],
                    "five_stars_percent": round((data["five_stars"] / count_reviews) * 100),
                    "rating": data["rating"],
                    "count_reviews": data["count_reviews"],
                }

                log_response(request=request, request_name="Отзывы 2GIS с микросервиса",
                             result={
                                 "count_reviews": result["count_reviews"],
                                 "rating": result["rating"],
                                 "stars_distribution_percent": {
                                     "1_star": result["one_star_percent"],
                                     "2_stars": result["two_stars_percent"],
                                     "3_stars": result["three_stars_percent"],
                                     "4_stars": result["four_stars_percent"],
                                     "5_stars": result["five_stars_percent"],
                                 }
                             },
                             status="Данные собраны",
                             )

                return Response({"status": "Данные собраны", "result": result}, status=200)

        except httpx.RequestError as exc:
            log_error_response(
                service_name='Микросервис 2GIS', service_url=service_url, method='GET',
                params={"filial_id": filial_id}, exception=exc
            )
            return Response({"error": "Ошибка при подключении к сервису"}, status=500)

        except Exception as e:
            log_unexpected_error(
                request=request,
                service_name='Микросервис 2GIS',
                service_url=service_url,
                method="GET",
                params={"filial_id": filial_id},
                exception=str(e)
            )

            return Response({"error": "Внутренняя ошибка сервера"}, status=500)

    # ---------------------------
    # Синхронный метод для POST
    # ---------------------------
    def trigger_stats_collection(self, request):
        """
        Инициирует сбор статистики для указанного филиала 2GIS.

        Этот метод обрабатывает POST-запросы для запуска процесса сбора статистики филиала,
        передавая необходимые данные внешнему микросервису 2GIS.

        :param request: Объект HTTP-запроса, содержащий тело запроса:
            - filial_id (str): ID филиала с сайта 2GIS (обязательный).

        :return: Объект Response с JSON-ответом:
            - message (str): Сообщение о статусе инициирования сбора статистики.
            - error (str, optional): Описание ошибки, если возникла.

        :raises ParseError: Если тело запроса содержит некорректный JSON.
        :raises Exception: Если возникли неожиданные ошибки.

        Возможные ответы:
            - 200: Сбор статистики успешно инициирован.
            - 400: Отсутствует обязательный параметр `filial_id`.
            - 404: Указанный филиал не найден.
            - 502: Некорректный ответ от микросервиса 2GIS.
            - 500: Внутренняя ошибка сервера.

        Примечания:
            - Логируются запросы и ответы, включая ошибки и необработанные исключения.
            - Используются методы `async_to_sync` для асинхронного вызова микросервиса.
        """
        try:
            # Преобразование тела запроса в JSON
            try:
                body = request.data  # DRF автоматически парсит тело запроса
            except ParseError as e:
                logger.error(
                    "Ошибка при парсинге тела запроса: Некорректный формат JSON",
                    extra={
                        "error": str(e),
                        "raw_body": request.body.decode('utf-8', errors='replace'),  # Логируем сырое тело запроса
                    },
                )
                raise ParseError("Некорректный формат JSON")

            filial_id = body.get('filial_id')

            if not filial_id:
                log_request_missing_items(request, filial_id, 'params', 'missing_params')
                return Response({"error": "filial_id отсутствует в запросе"}, status=status.HTTP_400_BAD_REQUEST)

            logger.debug(f'filial_id: {filial_id}')

            # Ищем филиал по filial_id (синхронно)
            try:
                filial = DgisFilial.objects.select_related('profile').get(dgis_filial_id=str(filial_id))
            except DgisFilial.DoesNotExist:
                log_response(request=request, request_name="Отзывы 2GIS с микросервиса",
                             error="Филиал с таким filial_id не найден"
                             )

                return Response({"error": "Филиал с таким filial_id не найден"}, status=status.HTTP_404_NOT_FOUND)

            # Получаем ID профиля и ID филиала
            main_user_id = filial.profile.id

            # Формируем данные для запроса
            url = f"{DGIS_SERVER_URL}/api/start_stats_collection"
            payload = {
                "main_user_id": main_user_id,
                "filial_id": filial_id
            }

            log_request_to_service("2GIS", url, 'POST', payload=payload)
            # Отправляем запрос к сервису (асинхронно, но с async_to_sync)
            response_httpx = async_to_sync(self._async_post)(url, payload)

            # Если _async_post вернул сразу DRF Response — значит упали на ошибке
            if isinstance(response_httpx, Response):
                log_error_response(
                    service_name="2GIS",
                    service_url=url,
                    method="POST",
                    payload=payload,
                    response=response_httpx

                )
                return response_httpx

            # Если пришёл ответ, смотрим код
            if response_httpx.status_code == 200:
                log_response(request=request, request_name="Статистика 2GIS с микросервиса",
                             message="Сбор статистики инициирован"
                             )

                return Response({"message": "Сбор статистики инициирован"}, status=status.HTTP_200_OK)
            else:
                # Если сервис вернул не 200
                try:
                    details = response_httpx.json()
                except Exception:
                    details = {"raw_body": response_httpx.text}

                    logger.warning(
                        "Микросервис 2GIS вернул некорректный ответ",
                        extra={
                            "url": response_httpx.url,
                            "method": response_httpx.request.method,
                            "status_code": response_httpx.status_code,
                            "details": details,
                        }
                    )
                return Response(
                    {"error": "Ошибка при обращении к микросервису 2gis", "details": details},
                    status=status.HTTP_502_BAD_GATEWAY
                )

        except Exception as e:
            log_unexpected_error(
                request=request,
                service_name="Микросервис 2GIS",
                service_url=response_httpx.url if 'response_httpx' in locals() else None,
                method=response_httpx.request.method if 'response_httpx' in locals() else None,
                exception=str(e),
                exc_info=True

            )

            return Response({"error": f"Ошибка: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
            return Response({"error": "Тайм-аут подключения к микросервису 2gis"}, status=504)

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
            return Response({"error": "Ошибка подключения к микросервису 2gis"}, status=500)
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
            return Response({"error": f"Ошибка микросервиса 2gis: {exc.response.status_code}"},
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
            return Response({"error": "Тайм-аут подключения к микросервису 2gis"}, status=504)

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
            return Response({"error": "Ошибка подключения к микросервису 2gis"}, status=500)
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
            return Response({"error": f"Ошибка микросервиса 2gis: {exc.response.status_code}"},
                            status=exc.response.status_code)
