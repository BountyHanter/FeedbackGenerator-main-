import json
import os

import httpx
from asgiref.sync import async_to_sync
from dotenv import load_dotenv
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

load_dotenv()

DGIS_SERVER_URL = os.getenv("DGIS_SERVICE_ADDRESS")


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

        # Вызываем асинхронный метод через async_to_sync
        response = async_to_sync(self._async_post)(service_url, payload)

        # Если _async_post вернул DRF Response (значит была ошибка при запросе)
        if isinstance(response, Response):
            return response

        # Разбираем response как httpx.Response
        try:
            response.raise_for_status()
        except httpx.RequestError as e:
            return Response({'error': f'Ошибка соединения: {str(e)}'}, status=502)
        except httpx.HTTPStatusError as e:
            return Response({'error': f'Ошибка сервиса: {str(e)}'}, status=502)

        # Парсим JSON
        try:
            response_data = response.json()
            return Response({'is_favorite': response_data.get('is_favorite')}, status=200)
        except json.JSONDecodeError:
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

        response = async_to_sync(self._async_post)(service_url, data)
        if isinstance(response, Response):
            return response

        # Проверяем статус
        if response.status_code == 200:
            return Response({"status": "ok"}, status=200)
        else:
            error_message = response.text.strip() or "Неизвестная ошибка от внешнего сервиса"
            if len(error_message) > 200:
                error_message = error_message[:200] + "..."
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

        response = async_to_sync(self._async_post)(service_url, data)
        if isinstance(response, Response):
            return response

        if response.status_code == 200:
            return Response({"status": "ok"}, status=200)
        else:
            error_message = response.text.strip() or "Неизвестная ошибка от внешнего сервиса"
            if len(error_message) > 200:
                error_message = error_message[:200] + "..."
            return Response(
                {"error": f"Не удалось отправить ответ на отзыв, причина: {error_message}"},
                status=502,
            )

    # --------------------------------------------------
    # Вспомогательный асинхронный метод для запросов
    # --------------------------------------------------
    async def _async_post(self, url, payload):
        """
        Асинхронный POST-запрос, возвращаем либо httpx.Response (если всё ок),
        либо DRF Response (если словили RequestError).
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload)
                return response  # Вернём httpx.Response
            except httpx.RequestError as e:
                return Response({'error': f'Ошибка соединения: {str(e)}'}, status=502)
