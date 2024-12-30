import json
import os

import requests
from django.http import JsonResponse
from dotenv import load_dotenv

load_dotenv()

DGIS_SERVER_URL = os.getenv("DGIS_SERVICE_ADDRESS")


def toggle_dgis_favorite(request, review_id):
    if request.method == "POST":
        try:
            service_url = f"{DGIS_SERVER_URL}/api/favorite/{review_id}"

            response = requests.post(service_url, json={'review_id': review_id})
            if response.status_code == 200:
                response_data = response.json()
                return JsonResponse({'success': True, 'is_favorite': response_data.get('is_favorite')}, status=200)
            else:
                return JsonResponse({'success': False, 'error': response.text}, status=response.status_code)

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Не верный формат JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    return JsonResponse({'success': False, 'error': "Не верный тип запроса"}, status=405)


def toggle_dgis_complaint(request, review_id):
    if request.method == "POST":

        body = json.loads(request.body)
        text = body.get('complaint_text')
        main_user_id = body.get('main_user_id')
        is_no_client_complaint = body.get('is_no_client_complaint')

        service_url = f"{DGIS_SERVER_URL}/api/complaints/{review_id}"

        # Формируем JSON-данные для отправки
        data = {
            "text": text,
            "main_user_id": main_user_id,
            "is_no_client_complaint": is_no_client_complaint,
        }

        try:
            response = requests.post(service_url, json=data)

            if response.status_code == 200:
                # Успешная отправка
                return JsonResponse({"status": "ok"}, status=200)
            else:
                # Обработка неудачного запроса
                return JsonResponse({"error": f"Не удалось отправить жалобу, причина: {response.text}"},
                                    status=response.status_code)

        except Exception as e:
            # Обработка ошибки
            return JsonResponse({"error": str(e)}, status=500)

            # Если метод не POST, вернём ошибку
    return JsonResponse({"error": "Метод не поддерживается"}, status=405)


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
                return JsonResponse({"error": f"Не удалось отправить ответ на отзыв, причина: {response.text}"}, status=response.status_code)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Метод не поддерживается"}, status=405)
