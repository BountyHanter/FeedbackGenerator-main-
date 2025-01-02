import json
import os

import requests
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from dotenv import load_dotenv

from FeedbackGenerator.api_auth import api_login_required
from main_site.models.Dgis_models import DgisProfile, DgisFilial
from main_site.utils.password import encrypt_password


load_dotenv()

DGIS_SERVER_URL = os.getenv("DGIS_SERVICE_ADDRESS")


@csrf_protect
@api_login_required
def update_2gis_profile(request, profile_id):
    user = request.user

    if request.method == 'POST':
        try:
            username = request.POST.get('username')
            password = request.POST.get('password')
            name = request.POST.get('name')

            profile = DgisProfile.objects.get(id=profile_id)

            if profile.user != user:
                return JsonResponse({'error': 'Данный профиль не принадлежит вам!'}, status=403)
            if username:
                profile.username = username
            if password:
                hashed_password = encrypt_password(password)
                profile.hashed_password = hashed_password
            if name:
                profile.name = name
            profile.is_active = False
            profile.save()

            return JsonResponse({
                'message': 'Профиль обновлён!',
                'profile': {
                    'id': profile.id,
                    'username': profile.username,
                    'name': profile.name,
                    'is_active': profile.is_active,
                }
            }, status=200)
        except DgisProfile.DoesNotExist:
            return JsonResponse({'error': 'Профиль не найден!'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=404)

    return JsonResponse({'error': 'Метод не разрешён!'}, status=405)


@csrf_protect
@api_login_required
def trigger_2gis_stats_collection(request):
    """
    Инициирует сбор статистики для указанного филиала.

    :param request: HTTP-запрос с filial_id
    :return: JSON-ответ
    """
    if request.method == 'POST':
        try:
            # Парсим JSON из тела запроса
            body = json.loads(request.body)
            filial_id = body.get('filial_id')

            if not filial_id:
                return JsonResponse({"error": "filial_id отсутствует в запросе"}, status=400)

            # Ищем филиал по filial_id
            try:
                filial = DgisFilial.objects.select_related('profile').get(dgis_filial_id=str(filial_id))
            except DgisFilial.DoesNotExist:
                return JsonResponse({"error": "Филиал с таким filial_id не найден"}, status=404)

            # Получаем ID профиля и ID филиала
            main_user_id = filial.profile.id

            # Формируем данные для запроса
            url = f"{DGIS_SERVER_URL}/api/start_stats_collection"
            headers = {"Content-Type": "application/json"}
            payload = {
                "main_user_id": main_user_id,
                "filial_id": filial_id
            }

            # Отправляем POST-запрос на внешний сервис
            response = requests.post(url, json=payload, headers=headers)

            # Обрабатываем ответ от сервиса
            if response.status_code == 200:
                return JsonResponse({"message": "Сбор статистики инициирован"}, status=200)
            else:
                return JsonResponse({"error": "Ошибка при обращении к сервису", "details": response.json()},
                                    status=502)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Неверный формат JSON"}, status=400)

        except requests.RequestException as e:
            return JsonResponse({"error": f"Ошибка соединения: {str(e)}"}, status=500)

    return JsonResponse({"error": "Метод не поддерживается"}, status=405)
