import os
from datetime import datetime
from pprint import pprint

import httpx
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_protect

from dotenv import load_dotenv

from main_site.models.Dgis_models import DgisProfile, DgisFilial
from main_site.utils.words import pluralize_comments

load_dotenv()

DGIS_SERVER_URL = os.getenv("DGIS_SERVICE_ADDRESS")

@csrf_protect
@login_required
def render_2gis_reviews_page(request, profile_id):
    # Получаем профиль, проверяя, что он принадлежит текущему пользователю
    profile = get_object_or_404(DgisProfile, id=profile_id, user=request.user)

    # Получаем все филиалы, связанные с этим профилем
    filials = DgisFilial.objects.filter(profile=profile)

    # Формируем контекст для шаблона
    context = {
        'filials': filials,
        'main_user_id': profile.id,
    }

    return render(request, 'main_site/2gis/reviews.html', context)


@csrf_protect
@login_required
async def proxy_dgis_get_reviews(request):
    """
    Асинхронное проксирование запросов к внешнему API с фильтрацией нужных данных и рендерингом HTML.
    """
    main_user_id = request.GET.get('main_user_id')
    filial_id = request.GET.get('filial_id')
    limit = request.GET.get('limit', 20)
    offset_date = request.GET.get('offset_date')  # Получаем offset_date из параметров запроса
    rating = request.GET.get('rating')
    without_answer = request.GET.get('without_answer')
    is_favorite = request.GET.get('is_favorite')

    if not main_user_id or not filial_id:
        return JsonResponse({"error": "Missing required parameters"}, status=400)

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
            last_review = []

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
                    "formatedDateCreated": datetime.fromisoformat(review.get("created_at")),
                    "dateCreated": review.get("created_at"),
                    "name": review.get("user_name"),
                    "commentsCount": pluralize_comments(review.get("comments_count", 0)),
                    "likesCount": review.get("likes_count", 0),
                    "photos": filtered_photos,
                    "is_favorite": review.get('is_favorite'),

                }
                filtered_reviews.append(filtered_review)

            if len(filtered_reviews) == 20:
                last_review = filtered_reviews[-1]
            # Рендерим HTML-шаблон
            html = render_to_string("main_site/2gis/partials/reviews_card.html",
                                    {"reviews": filtered_reviews, 'lastReview': last_review, 'filial_id': filial_id})
            return JsonResponse({"html": html}, status=200)

        except httpx.RequestError as exc:
            print(f"Ошибка запроса: {exc}")
            return JsonResponse({"error": "Failed to connect to the service"}, status=500)

        except httpx.HTTPStatusError as exc:
            print(f"Ошибка HTTP: {exc.response.status_code}")
            return JsonResponse({"error": f"Service error: {exc.response.status_code}"},
                                status=exc.response.status_code)


@csrf_protect
@login_required
async def proxy_dgis_fetch_stats(request):
    filial_id = request.GET.get('filial_id')

    if not filial_id:
        return JsonResponse({"error": "Missing required parameters"}, status=400)

    SERVICE_URL = f"{DGIS_SERVER_URL}/api/stats/{filial_id}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(SERVICE_URL)
            print(response.json())
            data = response.json()
            if response.status_code == 404:
                # Отправляем шаблон с кнопкой "Запросить статистику"
                html_desktop = render_to_string("main_site/2gis/partials/stats_card.html",
                                                {"not_found": True, "filial_id": filial_id, })
                html_mobile = render_to_string("main_site/2gis/partials/stats_card_mobile.html",
                                               {"not_found": True, "filial_id": filial_id, })
                return JsonResponse({
                    "desktop_html": html_desktop,
                    "mobile_html": html_mobile
                }, status=200)
            if data["status"] == "in_progress":
                # Отправляем шаблон с информацией о сборе статистики
                html_desktop = render_to_string("main_site/2gis/partials/stats_card.html", {"in_progress": True, "end_parsing_time": data["end_parsing_time"]})
                html_mobile = render_to_string("main_site/2gis/partials/stats_card_mobile.html", {"in_progress": True, "end_parsing_time": data["end_parsing_time"]})
                return JsonResponse({
                    "desktop_html": html_desktop,
                    "mobile_html": html_mobile
                }, status=200)

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

            # Рендерим шаблоны для десктопа и мобильной версии
            html_desktop = render_to_string("main_site/2gis/partials/stats_card.html", {"result": result})
            html_mobile = render_to_string("main_site/2gis/partials/stats_card_mobile.html", {"result": result})

            # Возвращаем JSON с двумя HTML
            return JsonResponse({
                "desktop_html": html_desktop,
                "mobile_html": html_mobile
            }, status=200)

        except httpx.RequestError as exc:
            return JsonResponse({"error": "Failed to connect to the service"}, status=500)

        except httpx.HTTPStatusError as exc:
            return JsonResponse({"error": f"Service error: {exc.response.status_code}"},
                                status=exc.response.status_code)


