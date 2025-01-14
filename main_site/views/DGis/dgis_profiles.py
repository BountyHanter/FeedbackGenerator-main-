import logging

from asgiref.sync import async_to_sync
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from FeedbackGenerator.utils.check_method import check_method
from FeedbackGenerator.utils.logging_templates import log_request_missing_items, log_request_not_allowed, log_response, \
    log_error_response
from FeedbackGenerator.utils.mask_data import mask_sensitive_data
from main_site.models.Dgis_models import DgisProfile, DgisFilial
from main_site.services.Dgis.Dgis_service_api import link_profile_to_2gis
from main_site.utils.password import encrypt_password

logger = logging.getLogger(__name__)


class DGISProfiles(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, action=None, profile_id=None):
        if action in ['create', 'link', 'update']:
            log_request_not_allowed(request, action, "GET")
            return Response(
                {'error': 'Метод не разрешён'},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )

        user = request.user
        # Получаем все профили пользователя
        dgis_profiles = user.dgis_profiles.all()
        logger.debug(f'dgis_profiles: {dgis_profiles}')

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

        logger.debug(f'profiles_data: {profiles_data}')

        log_response(request=request, request_name="Профиль 2GIS",
                     action=action, profiles_count=len(profiles_data),
                     )

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

        log_request_not_allowed(request, action, "POST")

        return Response(
            {'error': 'Метод не разрешён'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def patch(self, request, action=None, profile_id=None):
        # Разрешённые действия для PATCH
        allowed_actions = ['update']

        if action not in allowed_actions:
            log_request_not_allowed(request, action, "PATCH")
            return Response(
                {'error': 'Метод не разрешён'},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )

        if action == 'update':
            return self.update_profile(request, profile_id)

        log_error_response(request=request,
                           action=action,
                           service_name="Профиль 2GIS",
                           exception='Неизвестное действие')

        # Если action не обработан, вернём ошибку (на всякий случай)
        return Response(
            {'error': 'Неизвестное действие'},
            status=status.HTTP_400_BAD_REQUEST
        )

    def create_profile(self, request):
        user = request.user
        data = request.data

        masked_data = mask_sensitive_data(
            {
                'user_id': user.id,
                **data
            },
            fields_to_mask=['password']
        )

        logger.debug(f'user: {user.id}\n\ndata: {data}')

        required_fields = ['username', 'password']
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            log_request_missing_items(request, missing_fields, 'fields', 'missing_fields')
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

            log_response(request=request, request_name="Профили 2GIS",
                         action="create",
                         profile_info={
                             "id": new_profile.id,
                             "username": new_profile.username,
                             "name": new_profile.name,
                             "is_active": new_profile.is_active,
                         },
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
            log_error_response(
                request=request,
                service_name='Профили 2GIS',
                action='create',
                data=masked_data,
                exception=str(e),
                exc_info=True,
            )

            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update_profile(self, request, profile_id):
        user = request.user
        data = request.data

        masked_data = mask_sensitive_data(
            {
                'user_id': user.id,
                **data
            },
            fields_to_mask=['password']
        )

        logger.debug(f'user: {user.id}\n\ndata: {masked_data}')

        if not data:
            log_error_response(service_name='Профили 2GIS(Обновление)',
                               request=request,
                               exception='Данные для обновления не переданы',
                               )
            return Response({'error': 'Данные для обновления не переданы'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            profile = DgisProfile.objects.get(id=profile_id)

            if profile.user != user:
                log_error_response(
                    request=request,
                    service_name='Профили 2GIS(Обновление)',
                    exception='Данный профиль не принадлежит пользователю',
                    profile_id=profile_id,
                    profile_user_id=profile.user.id,
                    exc_info=True,
                )
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

            log_response(request=request, request_name='Профили 2GIS',
                         action="update",
                         profile_info={
                             "id": profile.id,
                             "username": profile.username,
                             "name": profile.name,
                             "is_active": profile.is_active,
                         },
                         )
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
            log_error_response(
                request=request,
                service_name='Профили 2GIS(Обновление)',
                exception='Юзер не найден',
                exc_info=True,
            )

            return Response({'error': 'Профиль не найден!'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            log_error_response(
                request=request,
                service_name='Профили 2GIS(Обновление)',
                exc_info=True,
                data=masked_data,
                exception=str(e),
            )

            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def link_profile(self, request, profile_id):
        user_id = request.user.id
        logger.debug(f'user: {user_id}')

        try:
            # Синхронно получаем профиль
            profile = DgisProfile.objects.select_related('user').get(id=profile_id)
        except DgisProfile.DoesNotExist:

            log_error_response(
                request=request,
                service_name='Профили 2GIS(Связка)',
                exception='Профиль не найден'
            )

            return Response({"error": "Профиль не найден!"}, status=status.HTTP_404_NOT_FOUND)

        logger.info(f"Профиль {profile.id} - {profile.username} найден")

        # Проверка принадлежности профиля пользователю
        if profile.user_id != user_id:
            log_error_response(
                request=request,
                service_name='Профили 2GIS(Связка)',
                exception='Профиль не пренадлежит юзеру',
            )

            return Response(
                {'error': 'Данный профиль не принадлежит вам!'},
                status=status.HTTP_403_FORBIDDEN
            )

        data = {
            "main_user_id": profile.id,
            "username": profile.username,
            "hashed_password": profile.hashed_password,
        }

        masked_data = mask_sensitive_data(data, ['hashed_password'])

        logger.debug(f"Данные профиля пользователя - {user_id}:\n\n{masked_data}")

        try:
            # Вызываем асинхронную функцию link_profile_to_2gis через async_to_sync
            response_data = async_to_sync(link_profile_to_2gis)(data=data)
            logger.debug(f"Результат link_profile_to_2gis:\n\n{response_data}")

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

            logger.debug(f"Новые филиалы - {filial_data}")

            log_response(request=request, request_name="Профили 2GIS",
                         action="link",
                         profile_info={
                             "id": profile.id,
                             "username": profile.username,
                             "name": profile.name,
                             "is_active": profile.is_active,
                         },
                         filials=filial_data,
                         )
            return Response(
                {"status": 'ok', "message": "Профиль успешно привязан"},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            # Пытаемся извлечь статус-код из текста исключения
            try:
                status_code = int(str(e))
            except ValueError:
                logger.error(
                    "Некорректный формат исключения для извлечения status_code",
                    extra={"error": str(e)},
                    exc_info=True
                )
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

            # Карта ошибок
            error_map = {
                401: "Ошибка авторизации, возможно вы ввели некорректные данные",
                501: "Не удалось получить данные о аккаунте",
                502: "Не удалось обновить данные на сервисе",
            }

            error_message = error_map.get(status_code, f"Неизвестная ошибка")

            log_error_response(
                request=request,
                service_url='/api/create_or_update_user',
                service_name='Микросервис 2GIS',
                profile_id=profile_id,
                data=masked_data,
                status_code=status_code,
                exception=str(e),
                error_message=error_message,
                exc_info=True,

            )

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
