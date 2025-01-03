import json
import os

import httpx
from asgiref.sync import sync_to_async
from dotenv import load_dotenv
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from main_site.models.Dgis_models import DgisFilial

load_dotenv()

DGIS_SERVER_URL = os.getenv("DGIS_SERVICE_ADDRESS")


class APIDGISProfiles(APIView):
    permission_classes = [IsAuthenticated]

    async def get(self, request, action=None):
        """
        Обработка GET-запросов в зависимости от действия.
        """
        if action == 'reviews':
            return await self.get_reviews(request)
        elif action == 'stats':
            return await self.fetch_stats(request)
        else:
            return Response({'error': 'Неизвестное действие'}, status=status.HTTP_400_BAD_REQUEST)

    async def post(self, request, action=None):
        if action == 'trigger_stats':
            return await self.trigger_stats_collection(request)
        else:
            return Response({'error': 'Неизвестное действие'}, status=status.HTTP_400_BAD_REQUEST)

    async def get_reviews(self, request):
        required_params = ['main_user_id', 'filial_id']
        missing_params = [param for param in required_params if not request.GET.get(param)]

        if missing_params:
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

        SERVICE_URL = f"{DGIS_SERVER_URL}/api/get_reviews"

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

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(SERVICE_URL, params=params)
                response.raise_for_status()
                response_data = response.json()

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
                        "rating": list(range(review.get("rating", 0))),
                        "text": review.get("text", "Без текста"),
                        "dateCreated": review.get("created_at"),
                        "name": review.get("user_name"),
                        "commentsCount": review.get("comments_count", 0),
                        "likesCount": review.get("likes_count", 0),
                        "photos": filtered_photos,
                        "is_favorite": review.get('is_favorite'),
                    }
                    filtered_reviews.append(filtered_review)

                return Response(
                    {
                        "reviews": filtered_reviews,
                        "count": len(filtered_reviews),
                        "filial_id": filial_id
                    },
                    status=200
                )

            except httpx.RequestError as exc:
                return Response({"error": "Ошибка подключения к сервису"}, status=500)
            except httpx.HTTPStatusError as exc:
                return Response(
                    {"error": f"Ошибка сервиса: {exc.response.status_code}"},
                    status=exc.response.status_code
                )

    async def fetch_stats(self, request):
        filial_id = request.GET.get('filial_id')

        if not filial_id:
            return Response({"error": "Отсутствует обязательный параметр - filial_id"}, status=400)

        SERVICE_URL = f"{DGIS_SERVER_URL}/api/stats/{filial_id}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(SERVICE_URL)
                response.raise_for_status()
                data = response.json()

                if response.status_code == 404:
                    return Response({"status": "Данных нет"}, status=200)

                if data["status"] == "pending":
                    return Response({"status": "В очереди"}, status=200)

                if data["status"] == "in_progress":
                    return Response(
                        {"status": "В процессе", "end_parsing_time": data.get("end_parsing_time")},
                        status=200
                    )

                result = {
                    "one_star_percent": round((data["one_star"] / data["count_reviews"]) * 100),
                    "two_stars_percent": round((data["two_stars"] / data["count_reviews"]) * 100),
                    "three_stars_percent": round((data["three_stars"] / data["count_reviews"]) * 100),
                    "four_stars_percent": round((data["four_stars"] / data["count_reviews"]) * 100),
                    "five_stars_percent": round((data["five_stars"] / data["count_reviews"]) * 100),
                    "rating": data["rating"],
                    "count_reviews": data["count_reviews"],
                }

                return Response({"status": "Данные собраны", "result": result}, status=200)

            except httpx.RequestError:
                return Response({"error": "Ошибка подключения к сервису"}, status=503)
            except httpx.HTTPStatusError as exc:
                return Response(
                    {"error": f"Ошибка сервиса: {exc.response.status_code}"},
                    status=exc.response.status_code
                )

    async def trigger_stats_collection(self, request):
        """
        Инициирует сбор статистики для указанного филиала.
        """
        try:
            # Преобразование тела запроса в JSON
            try:
                body = json.loads(request.body.decode('utf-8'))
            except (json.JSONDecodeError, AttributeError):
                raise ParseError("Некорректный формат JSON")

            filial_id = body.get('filial_id')

            if not filial_id:
                return Response({"error": "filial_id отсутствует в запросе"}, status=status.HTTP_400_BAD_REQUEST)

            # Ищем филиал по filial_id
            try:
                filial = await sync_to_async(
                    lambda: DgisFilial.objects.select_related('profile').get(dgis_filial_id=str(filial_id))
                )()
            except DgisFilial.DoesNotExist:
                return Response({"error": "Филиал с таким filial_id не найден"}, status=status.HTTP_404_NOT_FOUND)

            # Получаем ID профиля и ID филиала
            main_user_id = filial.profile.id

            # Формируем данные для запроса
            url = f"{DGIS_SERVER_URL}/api/start_stats_collection"
            headers = {"Content-Type": "application/json"}
            payload = {
                "main_user_id": main_user_id,
                "filial_id": filial_id
            }

            # Асинхронный запрос к внешнему сервису
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)

                if response.status_code == 200:
                    return Response({"message": "Сбор статистики инициирован"}, status=status.HTTP_200_OK)
                else:
                    return Response(
                        {"error": "Ошибка при обращении к сервису", "details": response.json()},
                        status=status.HTTP_502_BAD_GATEWAY
                    )

        except Exception as e:
            return Response({"error": f"Ошибка: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
