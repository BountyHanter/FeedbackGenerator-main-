import json
import logging
import os

import httpx
from asgiref.sync import async_to_sync
from dotenv import load_dotenv
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from FeedbackGenerator.utils.logging_templates import log_request_not_allowed, log_request_to_service, \
    log_error_response, log_unexpected_error, log_response

load_dotenv()

DGIS_SERVER_URL = os.getenv("DGIS_SERVICE_ADDRESS")

logger = logging.getLogger(__name__)


class APIDGISReviews(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, action=None, review_id=None):
        """
        Синхронный метод post, который внутри вызывает нужные методы
        (toggle_favorite / toggle_complaint / toggle_reply),
        также синхронные. Но сами запросы к микросервису будут асинхронными
        (через _async_post) и обёрнуты в async_to_sync.
        """
        if action == 'toggle_favorite':
            return self.toggle_favorite(request, review_id)
        elif action == 'toggle_complaint':
            return self.toggle_complaint(request, review_id)
        elif action == 'toggle_reply':
            return self.toggle_reply(request, review_id)
        else:
            log_request_not_allowed(request=request, action=action, method="POST")
            return Response(
                {'error': 'Метод не разрешён'},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )

    def toggle_favorite(self, request, review_id):
        """
        Переключение статуса избранного для отзыва (СИНХРОННО).
        """
        service_url = f"{DGIS_SERVER_URL}/api/favorite/{review_id}"

        # Формируем payload
        payload = {'review_id': review_id}

        logger.debug(f"review_id: {review_id}")

        log_request_to_service("2GIS", service_url, 'POST', payload={"review_id": review_id})

        # Вызываем асинхронный метод через async_to_sync
        response = async_to_sync(self._async_post)(service_url, payload)

        # Если _async_post вернул DRF Response (значит была ошибка при запросе)
        if isinstance(response, Response):
            log_error_response(
                service_name="Микросервис 2GIS",
                service_url=service_url,
                method="POST",
                payload=payload,
                response=response
            )
            return response

        # Разбираем response как httpx.Response
        try:
            response.raise_for_status()
        except httpx.RequestError as e:
            log_unexpected_error(
                request=request,
                service_name="Микросервис 2GIS",
                service_url=service_url,
                exception=str(e),
                exc_info=True
            )
            return Response({'error': f'Ошибка соединения: {str(e)}'}, status=502)
        except httpx.HTTPStatusError as e:
            log_error_response(
                service_name="Микросервис 2GIS",
                service_url=service_url,
                method="POST",
                payload=payload,
                exception=str(e)
            )
            return Response({'error': f'Ошибка сервиса: {str(e)}'}, status=502)

        # Парсим JSON
        try:
            response_data = response.json()
            log_response(
                request=request,
                request_name="Микросервис 2GIS",
                is_favorite=response_data.get('is_favorite')
            )
            return Response({'is_favorite': response_data.get('is_favorite')}, status=200)
        except json.JSONDecodeError:
            logger.error(
                "Некорректный формат JSON в ответе",
                extra={
                    "service_url": service_url,
                    "response_text": response.text
                }
            )
            return Response({'error': 'Некорректный формат JSON'}, status=400)

    def toggle_complaint(self, request, review_id):
        """
        Отправка жалобы на отзыв (СИНХРОННО).
        """
        # Читаем тело
        body = request.data
        text = body.get('complaint_text')
        main_user_id = body.get('main_user_id')
        is_no_client_complaint = body.get('is_no_client_complaint')

        service_url = f"{DGIS_SERVER_URL}/api/complaints/{review_id}"

        data = {
            "text": text,
            "main_user_id": main_user_id,
            "is_no_client_complaint": is_no_client_complaint,
        }

        logger.debug("Содержание запроса",
                     extra={
                         'text': text,
                         'main_user_id': main_user_id,
                         'is_no_client_complaint': is_no_client_complaint,
                     })

        log_request_to_service("2GIS", service_url, 'POST', payload=data)

        response = async_to_sync(self._async_post)(service_url, data)
        if isinstance(response, Response):
            log_error_response(
                service_name="Микросервис 2GIS",
                service_url=service_url,
                method="POST",
                payload=data,
                response=response
            )
            return response

        # Проверяем статус
        if response.status_code == 200:
            log_response(
                request=request,
                request_name="Микросервис 2GIS",
                status="ok"
            )

            return Response({"status": "ok"}, status=200)
        else:
            error_message = response.text.strip() or "Неизвестная ошибка от внешнего сервиса"
            if len(error_message) > 200:
                error_message = error_message[:200] + "..."

            log_error_response(
                service_name="Микросервис 2GIS",
                service_url=service_url,
                method="POST",
                payload=data,
                response=response,
                exception=error_message
            )

            return Response(
                {"error": f"Не удалось отправить жалобу, причина: {error_message}"},
                status=502,
            )

    def toggle_reply(self, request, review_id):
        """
        Отправка ответа на отзыв (СИНХРОННО).
        """
        body = request.data
        main_user_id = body.get('main_user_id')
        text = body.get('text')
        is_official = body.get('is_official')

        service_url = f"{DGIS_SERVER_URL}/api/post_review_reply/{review_id}"

        data = {
            "main_user_id": main_user_id,
            "text": text,
            "is_official": is_official,
        }

        logger.debug("Содержание запроса",
                     extra={
                         "main_user_id": main_user_id,
                         "text": text,
                         "is_official": is_official,
                     })

        log_request_to_service("Микросервис 2GIS", service_url, 'POST', payload=data)

        response = async_to_sync(self._async_post)(service_url, data)
        if isinstance(response, Response):
            log_error_response(
                service_name="Микросервис 2GIS",
                service_url=service_url,
                method="POST",
                payload=data,
                response=response
            )
            return response

        if response.status_code == 200:
            return Response({"status": "ok"}, status=200)
        else:
            error_message = response.text.strip() or "Неизвестная ошибка от внешнего сервиса"
            if len(error_message) > 200:
                error_message = error_message[:200] + "..."

            log_error_response(
                service_name="Микросервис 2GIS",
                service_url=service_url,
                method="POST",
                payload=data,
                response=response,
                exception=error_message
            )

            return Response(
                {"error": f"Не удалось отправить ответ на отзыв, причина: {error_message}"},
                status=502,
            )

    # --------------------------------------------------
    # Вспомогательный асинхронный метод для запросов
    # --------------------------------------------------
    async def _async_post(self, url, payload, headers):
        """
        Асинхронный POST-запрос, возвращаем либо httpx.Response (если всё ок),
        либо DRF Response (если словили RequestError).
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload)
                logger.info(
                    "Успешный POST-запрос к микросервису",
                    extra={
                        "url": url,
                        "payload": payload,
                        "status_code": response.status_code,
                    }
                )
                return response  # Вернём httpx.Response
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
