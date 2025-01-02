import json
import os
from json import JSONDecodeError

import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from dotenv import load_dotenv
from requests import RequestException

from FeedbackGenerator.api_auth import api_login_required

load_dotenv()

DGIS_SERVER_URL = os.getenv("DGIS_SERVICE_ADDRESS")


@csrf_protect
@api_login_required
def toggle_dgis_favorite(request, review_id):
    if request.method != "POST":
        return JsonResponse({'error': "Неверный тип запроса"}, status=405)

    try:
        service_url = f"{DGIS_SERVER_URL}/api/favorite/{review_id}"
        response = requests.post(service_url, json={'review_id': review_id})
        response.raise_for_status()  # Проверяем на 2xx статус

        try:
            response_data = response.json()
            return JsonResponse({'is_favorite': response_data.get('is_favorite')}, status=200)
        except JSONDecodeError:
            return JsonResponse({'error': 'Некорректный формат JSON'}, status=400)

    except RequestException as e:
        return JsonResponse({'error': str(e)}, status=502)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_protect
@api_login_required
def toggle_dgis_complaint(request, review_id):
    if request.method == "POST":

        body = json.loads(request.body)
        text = body.get('complaint_text')
        main_user_id = body.get('main_user_id')
        is_no_client_complaint = body.get('is_no_client_complaint')

        service_url = f"{DGIS_SERVER_URL}/api/complaints/{review_id}"

        data = {
            "text": text,
            "main_user_id": main_user_id,
            "is_no_client_complaint": is_no_client_complaint,
        }

        try:
            response = requests.post(service_url, json=data)

            if response.status_code == 200:
                return JsonResponse({"status": "ok"}, status=200)
            else:
                error_message = response.text.strip() or "Неизвестная ошибка от внешнего сервиса"
                if len(error_message) > 200:  # Ограничиваем длину текста
                    error_message = error_message[:200] + "..."

                return JsonResponse(
                    {"error": f"Не удалось отправить жалобу, причина: {error_message}"},
                    status=502,
                )

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Метод не поддерживается"}, status=405)


@csrf_protect
@api_login_required
def toggle_dgis_reply_review(request, review_id):
    if request.method == "POST":
        body = json.loads(request.body)
        main_user_id = body.get('main_user_id')
        text = body.get('text')
        is_official = body.get('is_official')

        service_url = f"{DGIS_SERVER_URL}/api/post_review_reply/{review_id}"

        data = {
            "main_user_id": main_user_id,
            "text": text,
            "is_official": is_official,
        }

        try:
            response = requests.post(service_url, json=data)
            if response.status_code == 200:
                return JsonResponse({"status": "ok"}, status=200)
            else:
                error_message = response.text.strip() or "Неизвестная ошибка от внешнего сервиса"
                if len(error_message) > 200:
                    error_message = error_message[:200] + "..."

                return JsonResponse(
                    {"error": f"Не удалось отправить ответ на отзыв, причина: {error_message}"},
                    status=502,
                )
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Метод не поддерживается"}, status=405)
