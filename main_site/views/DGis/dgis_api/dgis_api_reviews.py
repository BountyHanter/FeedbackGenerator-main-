import json
import os

import httpx
from dotenv import load_dotenv
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

load_dotenv()

DGIS_SERVER_URL = os.getenv("DGIS_SERVICE_ADDRESS")


class APIDGISReviews(APIView):
    permission_classes = [IsAuthenticated]

    async def post(self, request, action=None, review_id=None):
        if action == 'toggle_favorite':
            return await self.toggle_favorite(request, review_id)
        elif action == 'toggle_complaint':
            return await self.toggle_complaint(request, review_id)
        elif action == 'toggle_reply':
            return await self.toggle_reply(request, review_id)
        else:
            return Response({'error': 'Неизвестное действие'}, status=status.HTTP_400_BAD_REQUEST)

    async def toggle_favorite(self, request, review_id):
        """
        Переключение статуса избранного для отзыва.
        """
        service_url = f"{DGIS_SERVER_URL}/api/favorite/{review_id}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(service_url, json={'review_id': review_id})
                response.raise_for_status()

                try:
                    response_data = response.json()
                    return Response({'is_favorite': response_data.get('is_favorite')}, status=200)
                except json.JSONDecodeError:
                    return Response({'error': 'Некорректный формат JSON'}, status=400)

            except httpx.RequestError as e:
                return Response({'error': f'Ошибка соединения: {str(e)}'}, status=502)
            except Exception as e:
                return Response({'error': str(e)}, status=500)

    async def toggle_complaint(self, request, review_id):
        """
        Отправка жалобы на отзыв.
        """
        try:
            body = json.loads(request.body.decode('utf-8'))
            text = body.get('complaint_text')
            main_user_id = body.get('main_user_id')
            is_no_client_complaint = body.get('is_no_client_complaint')

            service_url = f"{DGIS_SERVER_URL}/api/complaints/{review_id}"

            data = {
                "text": text,
                "main_user_id": main_user_id,
                "is_no_client_complaint": is_no_client_complaint,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(service_url, json=data)

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
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    async def toggle_reply(self, request, review_id):
        """
        Отправка ответа на отзыв.
        """
        try:
            body = json.loads(request.body.decode('utf-8'))
            main_user_id = body.get('main_user_id')
            text = body.get('text')
            is_official = body.get('is_official')

            service_url = f"{DGIS_SERVER_URL}/api/post_review_reply/{review_id}"

            data = {
                "main_user_id": main_user_id,
                "text": text,
                "is_official": is_official,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(service_url, json=data)

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
        except Exception as e:
            return Response({'error': str(e)}, status=500)