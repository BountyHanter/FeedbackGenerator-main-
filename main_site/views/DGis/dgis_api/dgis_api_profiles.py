import json
import os

import httpx
from asgiref.sync import async_to_sync
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
    """
    Синхронный вариант вью, но сами запросы к внешнему сервису выполняются асинхронно
    и оборачиваются в async_to_sync, чтобы мы могли дождаться их результата.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, action=None):
        """
        Обработка GET-запросов в зависимости от действия.
        """
        if action == 'reviews':
            return self.get_reviews(request)
        elif action == 'stats':
            return self.fetch_stats(request)
        else:
            return Response(
                {'error': 'Метод не разрешён'},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )

    def post(self, request, action=None):
        if action == 'trigger_stats':
            return self.trigger_stats_collection(request)
        else:
            return Response(
                {'error': 'Метод не разрешён'},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
    # ---------------------------
    # Синхронные методы для GET
    # ---------------------------
    def get_reviews(self, request):
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

        # Выполняем асинхронный запрос через async_to_sync
        response_data = async_to_sync(self._async_get)(service_url, params)

        # Если _async_get вернёт уже готовый DRF-Response (ошибка или что-то подобное),
        # то просто возвращаем его. Иначе это словарь, распарсенный из JSON.
        if isinstance(response_data, Response):
            return response_data

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

        return Response(
            {
                "reviews": filtered_reviews,
                "count": len(filtered_reviews),
                "filial_id": filial_id
            },
            status=200
        )

    def fetch_stats(self, request):
        filial_id = request.GET.get('filial_id')

        if not filial_id:
            return Response({"error": "Отсутствует обязательный параметр - filial_id"}, status=400)

        service_url = f"{DGIS_SERVER_URL}/api/stats/{filial_id}"

        response_data = async_to_sync(self._async_get)(service_url)
        if isinstance(response_data, Response):
            if response_data.status_code == 404:
                # При желании можно вернуть, например, статус 200, но с сообщением, что данных нет
                return Response({"status": "Данных нет"}, status=200)
            return response_data

        # Разбор состояния
        if response_data.get("status") == "pending":
            return Response({"status": "В очереди"}, status=200)

        if response_data.get("status") == "in_progress":
            return Response(
                {
                    "status": "В процессе",
                    "end_parsing_time": response_data.get("end_parsing_time")
                },
                status=200
            )

        # Считаем проценты
        data = response_data
        count_reviews = data.get("count_reviews") or 1  # на всякий случай от деления на 0
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
        return Response({"status": "Данные собраны", "result": result}, status=200)

    # ---------------------------
    # Синхронный метод для POST
    # ---------------------------
    def trigger_stats_collection(self, request):
        """
        Инициирует сбор статистики для указанного филиала.
        """
        try:
            # Преобразование тела запроса в JSON
            try:
                body = request.data
            except (json.JSONDecodeError, AttributeError):
                raise ParseError("Некорректный формат JSON")

            filial_id = body.get('filial_id')

            if not filial_id:
                return Response({"error": "filial_id отсутствует в запросе"}, status=status.HTTP_400_BAD_REQUEST)

            # Ищем филиал по filial_id (синхронно)
            try:
                filial = DgisFilial.objects.select_related('profile').get(dgis_filial_id=str(filial_id))
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

            # Отправляем запрос к сервису (асинхронно, но с async_to_sync)
            response_httpx = async_to_sync(self._async_post)(url, payload, headers)

            # Если _async_post вернул сразу DRF Response — значит упали на ошибке
            if isinstance(response_httpx, Response):
                return response_httpx

            # Если пришёл ответ, смотрим код
            if response_httpx.status_code == 200:
                return Response({"message": "Сбор статистики инициирован"}, status=status.HTTP_200_OK)
            else:
                # Если сервис вернул не 200
                try:
                    details = response_httpx.json()
                except Exception:
                    details = {"raw_body": response_httpx.text}
                return Response(
                    {"error": "Ошибка при обращении к микросервису 2gis", "details": details},
                    status=status.HTTP_502_BAD_GATEWAY
                )

        except Exception as e:
            return Response({"error": f"Ошибка: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # --------------------------------------------------
    # Вспомогательные асинхронные методы для запросов
    # --------------------------------------------------
    async def _async_get(self, url, params=None):
        """
        Асинхронный GET-запрос, возвращает либо словарь (response.json()),
        либо DRF Response (при ошибке).
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.RequestError:
                return Response({"error": "Ошибка подключения к микросервису 2gis"}, status=500)
            except httpx.HTTPStatusError as exc:
                return Response({"error": f"Ошибка микросервиса 2gis: {exc.response.status_code}"},
                                status=exc.response.status_code)

    async def _async_post(self, url, payload, headers):
        """
        Асинхронный POST-запрос, возвращает сам объект response (чтобы мы взяли .status_code и т.п.),
        либо DRF Response (при ошибке).
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                return response  # Возвращаем httpx.Response, чтобы в основном коде смотреть статус и тело
            except httpx.RequestError:
                return Response({"error": "Ошибка подключения к микросервису 2gis"}, status=500)
            except httpx.HTTPStatusError as exc:
                return Response({"error": f"Ошибка микросервиса 2gis: {exc.response.status_code}"},
                                status=exc.response.status_code)
