import os

import httpx
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_protect

from dotenv import load_dotenv

from FeedbackGenerator.api_auth import api_login_required
from main_site.models.Dgis_models import DgisProfile
from main_site.utils.words import pluralize_comments

load_dotenv()

DGIS_SERVER_URL = os.getenv("DGIS_SERVICE_ADDRESS")


@csrf_protect
@api_login_required
def get_2gis_filials(request, profile_id):
    """
    Возвращает список филиалов для указанного профиля пользователя.
    """
    # Проверяем, что профиль принадлежит текущему пользователю
    profile = get_object_or_404(DgisProfile, id=profile_id, user=request.user)

    # Получаем все филиалы, связанные с профилем
    filials = profile.filials.all()

    # Формируем JSON-ответ с данными филиалов
    filials_data = [
        {
            'id': filial.id,  # Внутренний ID в вашей базе
            'dgis_filial_id': filial.dgis_filial_id,  # Внешний ID из 2ГИС
            'name': filial.name,  # Название филиала
            'is_active': filial.is_active,  # Активность филиала
        }
        for filial in filials
    ]

    return JsonResponse({
        'profile_id': profile.id,
        'profile_name': profile.name,
        'filials': filials_data,
    }, status=200)


@csrf_protect
@api_login_required
async def proxy_dgis_get_reviews(request):
    """
    Асинхронное проксирование запросов к внешнему API с фильтрацией нужных данных.
    """
    if request.method == "GET":
        required_params = ['main_user_id', 'filial_id']
        missing_params = [param for param in required_params if not request.GET.get(param)]

        if missing_params:
            return JsonResponse({
                'error': f"Отсутствуют обязательные параметры: {', '.join(missing_params)}"
            }, status=400)

        # Получаем параметры
        main_user_id = request.GET.get('main_user_id')
        filial_id = request.GET.get('filial_id')
        limit = request.GET.get('limit', 20)
        offset_date = request.GET.get('offset_date')
        rating = request.GET.get('rating')
        without_answer = request.GET.get('without_answer')
        is_favorite = request.GET.get('is_favorite')

        SERVICE_URL = f"{DGIS_SERVER_URL}/api/get_reviews"  # Замените на адрес из .env

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
                response.raise_for_status()  # Проверяем статус ответа
                response_data = response.json()  # Получаем JSON-данные от API

                # Фильтруем данные, оставляя только нужные
                reviews = response_data.get("reviews", [])
                filtered_reviews = []

                for review in reviews:
                    # Проверяем, что "photos" - список строк, если нет, приводим к нужному формату
                    photos = review.get("photos")
                    if isinstance(photos, list) and all(isinstance(photo, str) for photo in photos):
                        filtered_photos = photos
                    elif isinstance(photos, list):
                        filtered_photos = [photo.get("preview_urls", {}).get("url") for photo in photos if
                                           isinstance(photo, dict)]
                    else:
                        filtered_photos = None

                    filtered_review = {
                        "id": review.get("id"),
                        "rating": list(range(review.get("rating", 0))),
                        "text": review.get("text", "Без текста"),
                        "dateCreated": review.get("created_at"),
                        "name": review.get("user_name"),
                        "commentsCount": pluralize_comments(review.get("comments_count", 0)),
                        "likesCount": review.get("likes_count", 0),
                        "photos": filtered_photos,
                        "is_favorite": review.get('is_favorite'),
                    }
                    filtered_reviews.append(filtered_review)

                # Возвращаем JSON-ответ
                return JsonResponse({
                    "reviews": filtered_reviews,
                    "count": len(filtered_reviews),
                    "filial_id": filial_id
                }, status=200)

            except httpx.RequestError as exc:
                print(f"Ошибка запроса: {exc}")
                return JsonResponse({"error": "Ошибка подключения к сервису"}, status=500)

            except httpx.HTTPStatusError as exc:
                print(f"Ошибка HTTP: {exc.response.status_code}")
                return JsonResponse({"error": f"Ошибка сервиса: {exc.response.status_code}"},
                                    status=exc.response.status_code)

    return JsonResponse({'error': 'Метод не разрешён!'}, status=405)


@csrf_protect
@api_login_required
async def proxy_dgis_fetch_stats(request):
    filial_id = request.GET.get('filial_id')

    if not filial_id:
        return JsonResponse({"error": "Отсутствует обязательный параметр - filial_id"}, status=400)

    SERVICE_URL = f"{DGIS_SERVER_URL}/api/stats/{filial_id}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(SERVICE_URL)
            data = response.json()
            if response.status_code == 404:
                return JsonResponse({
                    "status": "Данных нет"}, status=200)

            if data["status"] == "pending":
                return JsonResponse({"status": "В очереди"}, status=200)

            if data["status"] == "in_progress":
                return JsonResponse({"status": "В процессе",
                                     "end_parsing_time": data["end_parsing_time"]},
                                    status=200)

            result = {"one_star_percent": round((data["one_star"] / data["count_reviews"]) * 100),
                      "two_stars_percent": round((data["two_stars"] / data["count_reviews"]) * 100),
                      "three_stars_percent": round((data["three_stars"] / data["count_reviews"]) * 100),
                      "four_stars_percent": round((data["four_stars"] / data["count_reviews"]) * 100),
                      "five_stars_percent": round((data["five_stars"] / data["count_reviews"]) * 100),
                      "one_star": data["one_star"],
                      "two_stars": data["two_stars"],
                      "three_stars": data["three_stars"],
                      "four_stars": data["four_stars"],
                      "five_stars": data["five_stars"],
                      "rating": data["rating"],
                      "count_reviews": data["count_reviews"],
                      }

            return JsonResponse({"status": "Данные собраны", "result": result}, status=200)

        except httpx.RequestError as exc:
            return JsonResponse({"error": "Ошибка подключения к сервису"}, status=503)

        except httpx.HTTPStatusError as exc:
            error_details = exc.response.text if exc.response else "Нет данных от сервиса"
            return JsonResponse(
                {"error": f"Ошибка сервиса: Статус - {exc.response.status_code}, Подробности: {error_details}"},
                status=500,
            )
