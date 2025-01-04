from asgiref.sync import async_to_sync
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from FeedbackGenerator.utils.check_method import check_method
from main_site.models.Dgis_models import DgisProfile, DgisFilial
from main_site.services.Dgis.Dgis_service_api import link_profile_to_2gis
from main_site.utils.password import encrypt_password


class DGISProfiles(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, action=None, profile_id=None):
        if action in ['create', 'link', 'update']:
            return Response(
                {'error': 'Метод не разрешён'},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        user = request.user
        # Получаем все профили пользователя
        dgis_profiles = user.dgis_profiles.all()

        # Формируем JSON-ответ
        profiles_data = [
            {
                'id': profile.id,
                'username': profile.username,
                'name': profile.name,
                'is_active': profile.is_active,  # Связано ли с сервисом
            }
            for profile in dgis_profiles
        ]

        return Response({'profiles': profiles_data}, status=200)

    def post(self, request, action=None, profile_id=None):
        # Проверяем разрешённые методы для каждого действия
        if action == 'create':
            method_check = check_method(request, ['POST'])
            if method_check:  # Если метод не разрешён, возвращаем Response
                return method_check
            return self.create_profile(request)

        elif action == 'link':
            method_check = check_method(request, ['POST'])
            if method_check:
                return method_check
            return self.link_profile(request, profile_id)

        elif action == 'update':
            method_check = check_method(request, ['POST'])
            if method_check:
                return method_check
            return self.update_profile(request, profile_id)

        return Response(
            {'error': 'Метод не разрешён'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def create_profile(self, request):
        user = request.user
        data = request.data

        required_fields = ['username', 'password']
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            return Response(
                {'error': f"Отсутствуют обязательные поля: {', '.join(missing_fields)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        username = data.get('username')
        password = data.get('password')
        name = data.get('name', None)  # Поле не обязательно

        try:
            # Хешируем пароль
            hashed_password = encrypt_password(password)

            # Создаем профиль пользователя
            new_profile = DgisProfile.objects.create(
                user=user,
                name=name,
                username=username,
                hashed_password=hashed_password,
            )

            # Возвращаем успешный ответ с данными профиля
            return Response({
                "status": 'ok',
                "profile": {
                    "id": new_profile.id,
                    "username": new_profile.username,
                    "name": new_profile.name,
                    "is_active": new_profile.is_active,
                }
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update_profile(self, request, profile_id):
        user = request.user
        data = request.data

        try:
            profile = DgisProfile.objects.get(id=profile_id)

            if profile.user != user:
                return Response({'error': 'Данный профиль не принадлежит вам!'}, status=status.HTTP_403_FORBIDDEN)

            username = data.get('username')
            password = data.get('password')
            name = data.get('name')

            if username:
                profile.username = username
            if password:
                hashed_password = encrypt_password(password)
                profile.hashed_password = hashed_password
            if name:
                profile.name = name

            profile.is_active = False
            profile.save()

            return Response({
                'status': 'ok',
                'message': 'Профиль обновлён!',
                'profile': {
                    'id': profile.id,
                    'username': profile.username,
                    'name': profile.name,
                    'is_active': profile.is_active,
                }
            }, status=status.HTTP_200_OK)

        except DgisProfile.DoesNotExist:
            return Response({'error': 'Профиль не найден!'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def link_profile(self, request, profile_id):
        user_id = request.user.id

        try:
            # Синхронно получаем профиль
            profile = DgisProfile.objects.select_related('user').get(id=profile_id)
        except DgisProfile.DoesNotExist:
            return Response({"error": "Профиль не найден!"}, status=status.HTTP_404_NOT_FOUND)

        # Проверка принадлежности профиля пользователю
        if profile.user_id != user_id:
            return Response(
                {'error': 'Данный профиль не принадлежит вам!'},
                status=status.HTTP_403_FORBIDDEN
            )

        data = {
            "main_user_id": profile.id,
            "username": profile.username,
            "hashed_password": profile.hashed_password,
        }

        try:
            # Вызываем асинхронную функцию link_profile_to_2gis через async_to_sync
            response_data = async_to_sync(link_profile_to_2gis)(data=data)

            # Обрабатываем ответ
            user_info_and_filials = response_data.get('user_info_and_filials', [])
            filial_data = []

            for item in user_info_and_filials:
                if 'filials_info' in item:
                    for filial in item['filials_info'].values():
                        if filial.get('items'):
                            for fil in filial['items']:
                                filial_data.append({
                                    'id': fil['id'],
                                    'name': fil['name']
                                })

            # Синхронно удаляем старые филиалы
            DgisFilial.objects.filter(profile=profile).delete()

            # Синхронно создаём новые
            for filial in filial_data:
                DgisFilial.objects.create(
                    dgis_filial_id=int(filial['id']),
                    profile=profile,
                    name=filial['name']
                )

            # Активируем профиль
            profile.is_active = True
            profile.save()

            return Response(
                {"status": 'ok', "message": "Профиль успешно привязан"},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            # Пытаемся извлечь статус-код из текста исключения
            try:
                status_code = int(str(e))
            except ValueError:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

            # Карта ошибок
            error_map = {
                401: "Ошибка авторизации, возможно вы ввели некорректные данные",
                501: "Не удалось получить данные о аккаунте",
                502: "Не удалось обновить данные на сервисе",
            }

            error_message = error_map.get(status_code, f"Неизвестная ошибка: {e}")
            return Response({"error": error_message}, status=status_code)

# @csrf_protect
# @api_login_required
# def render_2gis_profiles_selection(request):
#     profiles = DgisProfile.objects.filter(user=request.user, is_active=True)
#
#     # Передаем профили в контекст
#     context = {
#         'profiles': profiles
#     }
#     return render(request, 'main_site/2gis/profiles_list.html', context)
