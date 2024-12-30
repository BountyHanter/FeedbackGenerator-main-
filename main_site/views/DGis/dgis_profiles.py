from asgiref.sync import sync_to_async
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect

from main_site.models.Dgis_models import DgisProfile, DgisFilial
from main_site.services.Dgis.Dgis_service_api import link_profile_to_2gis
from main_site.utils.password import encrypt_password


@csrf_protect
@login_required
def list_2gis_profiles(request):
    user = request.user
    dgis_profiles = user.dgis_profiles.all()
    return render(request, 'main_site/2gis/profiles_settings.html', {'dgis_profiles': dgis_profiles})


@csrf_protect
@login_required
def render_2gis_profiles_selection(request):
    profiles = DgisProfile.objects.filter(user=request.user, is_active=True)

    # Передаем профили в контекст
    context = {
        'profiles': profiles
    }
    return render(request, 'main_site/2gis/profiles_list.html', context)


@csrf_protect
@login_required
def create_2gis_profile(request):
    user = request.user

    if request.method == 'POST':
        try:
            username = request.POST.get('username')
            password = request.POST.get('password')

            if not username or not password:
                return JsonResponse({'error': 'username or password is empty'}, status=400)

            # Хешируем пароль
            hashed_password = encrypt_password(password)

            # Создаем профиль пользователя
            DgisProfile.objects.create(
                user=user,
                username=username,
                hashed_password=hashed_password,
            )

            # Возвращаем успешный ответ
            return JsonResponse({"success": True})

        except Exception as e:
            print(f"Ошибка: {e}")
            return JsonResponse({"error": str(e)}, status=500)


@csrf_protect
@login_required
async def update_or_create_2gis_profile(request, profile_id):
    user_id = request.session.get('_auth_user_id')
    if not user_id:
        return JsonResponse({'error': 'Не авторизован'}, status=401)

    user_id = await sync_to_async(lambda: request.user.id)()

    if request.method == 'POST':
        # Предзагружаем связанный user, чтобы обращаться к user_id без доп. запросов
        profile = await sync_to_async(
            lambda: DgisProfile.objects.select_related('user').get(id=profile_id)
        )()

        # Сравниваем по user_id
        if profile.user_id != user_id:
            return JsonResponse({'error': 'Данный профиль не принадлежит вам!'}, status=403)

        data = {
            "main_user_id": profile.id,
            "username": profile.username,
            "hashed_password": profile.hashed_password,
        }

        try:
            response_data = await link_profile_to_2gis(data=data)

            user_info_and_filials = response_data.get('user_info_and_filials', [])
            filial_data = []

            for item in user_info_and_filials:
                if 'filials_info' in item:
                    for filial in item['filials_info'].values():
                        # Проверяем, есть ли элементы в 'items'
                        if filial.get('items'):  # Если items не пусто
                            for fil in filial['items']:
                                filial_data.append({
                                    'id': fil['id'],
                                    'name': fil['name']
                                })

            # Получаем все филиалы для данного профиля из базы данных
            # Я ни как по другому не знаю как сделать с этой асинхронщиной сраной
            await sync_to_async(
                lambda: DgisFilial.objects.filter(profile=profile).delete()
            )()

            # Обновляем или создаем новые филиалы
            for filial in filial_data:
                # Обновляем или создаем филиал
                await sync_to_async(DgisFilial.objects.create)(
                    filial_id=int(filial['id']),
                    profile=profile,
                    name=filial['name']
                )

            profile.is_active = True
            await sync_to_async(profile.save)()

        except Exception as e:
            status_code = int(str(e))  # Преобразуем к целому, если нужно
            # В зависимости от статус-кода делаем нужную логику
            if status_code == 401:
                return JsonResponse({"error": "Ошибка авторизации, возможно вы ввели не корректные данные"}, status=401)
            if status_code == 501:
                return JsonResponse({"error": "Не удалось получить данные о аккаунте"}, status=501)
            elif status_code == 502:
                return JsonResponse({"error": "Не удалось обновить данные на сервисе"}, status=404)
            else:
                return JsonResponse({"error": f"Неизвестная ошибка {status_code}"}, status=status_code)

        # Возвращаем результат
        return JsonResponse({"message": "Задача успешно обработана"})
