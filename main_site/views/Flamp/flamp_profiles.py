import json
import logging

from asgiref.sync import async_to_sync
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from FeedbackGenerator.utils.check_method import check_method
from FeedbackGenerator.utils.logging_templates import log_request_not_allowed, log_response, log_error_response, \
    log_request_missing_items
from FeedbackGenerator.utils.mask_data import mask_sensitive_data
from main_site.models import FlampProfile, FlampFilial
from main_site.services.Flamp.Flamp_service_api import link_profile_to_flamp
from main_site.utils.password import encrypt_password

logger = logging.getLogger(__name__)


class FlampProfiles(APIView):
    """
    API-контроллер для управления профилями Flamp.

    Как работает:
    - Проверяет, авторизован ли пользователь.
    - В `GET` возвращает список профилей пользователя.
    - В `POST` создаёт новый профиль или привязывает к микросервису.
    - В `PATCH` обновляет профиль.
    - Логирует все запросы и ошибки.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, action=None, profile_id=None):
        """
        Получение списка профилей пользователя.

        Как работает:
        - Проверяет, что `action` не требует `POST` (иначе возвращает 405).
        - Берёт у пользователя все его профили из БД.
        - Формирует JSON-ответ с данными профилей.
        - Логирует запрос и ответ.

        :param request: Запрос от клиента.
        :param action: Игнорируется, но проверяется на некорректные значения.
        :param profile_id: Не используется.
        :return: JSON-ответ со списком профилей.
        """
        if action in ['create', 'link', 'update']:
            log_request_not_allowed(request, action, "GET")
            return Response(
                {'error': 'Метод не разрешён'},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )

        user = request.user
        # Получаем все профили пользователя
        flamp_profiles = user.flamp_profiles.all()
        logger.debug(f'flamp_profiles: {flamp_profiles}')

        # Формируем JSON-ответ
        profiles_data = [
            {
                'id': profile.id,
                'username': profile.username,
                'name': profile.name,
                'is_active': profile.is_active,  # Связано ли с сервисом
            }
            for profile in flamp_profiles
        ]

        logger.debug(f'profiles_data: {profiles_data}')

        log_response(request=request, request_name="Профиль Flamp",
                     action=action, profiles_count=len(profiles_data),
                     )

        return Response({'profiles': profiles_data}, status=200)

    def post(self, request, action=None, profile_id=None):
        """
        Обработка POST-запросов.

        Как работает:
        - Проверяет `action`:
            - `create` → вызывает `create_profile()`
            - `link` → вызывает `link_profile()`
            - Остальное → возвращает 405 (метод не разрешён).
        - Логирует запрещённые методы.

        :param request: Запрос от клиента.
        :param action: Действие (create, link).
        :param profile_id: Используется только для `link`.
        :return: JSON-ответ с результатом операции.
        """
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
        """
        Обновление профиля пользователя.

        Как работает:
        - Проверяет, что `action` == 'update', иначе 405.
        - Вызывает `update_profile()`, передавая `profile_id`.

        :param request: Запрос от клиента.
        :param action: Должно быть 'update'.
        :param profile_id: ID обновляемого профиля.
        :return: JSON-ответ с результатом обновления.
        """
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
                           service_name="Профиль Flamp",
                           exception='Неизвестное действие')

        # Если action не обработан, вернём ошибку (на всякий случай)
        return Response(
            {'error': 'Неизвестное действие'},
            status=status.HTTP_400_BAD_REQUEST
        )

    def create_profile(self, request):
        """
        Создаёт новый профиль Flamp.

        Как работает:
        - Проверяет, переданы ли `username` и `password` (иначе 400).
        - Хеширует пароль перед сохранением.
        - Создаёт новый профиль в БД.
        - Логирует созданный профиль.
        - Возвращает JSON-ответ с ID и статусом.

        :param request: Запрос от клиента.
        :return: JSON-ответ с созданным профилем.
        """
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
            new_profile = FlampProfile.objects.create(
                user=user,
                name=name,
                username=username,
                hashed_password=hashed_password,
            )

            log_response(request=request, request_name="Профили Flamp",
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
                service_name='Профили Flamp',
                action='create',
                data=masked_data,
                exception=str(e),
                exc_info=True,
            )

            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update_profile(self, request, profile_id):
        """
        Обновляет данные профиля Flamp.

        Как работает:
        - Проверяет, переданы ли данные для обновления (иначе 400).
        - Ищет профиль в БД:
            - Если нет → 404.
            - Если не принадлежит пользователю → 403.
        - Обновляет `username`, `password`, `name`, делает `is_active = False`.
        - Сохраняет изменения и логирует их.
        - Возвращает JSON-ответ с обновлёнными данными.

        :param request: Запрос от клиента.
        :param profile_id: ID профиля, который нужно обновить.
        :return: JSON-ответ с обновлёнными данными профиля.
        """
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
            log_error_response(service_name='Профили Flamp(Обновление)',
                               request=request,
                               exception='Данные для обновления не переданы',
                               )
            return Response({'error': 'Данные для обновления не переданы'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            profile = FlampProfile.objects.get(id=profile_id)

            if profile.user != user:
                log_error_response(
                    request=request,
                    service_name='Профили Flamp(Обновление)',
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

            log_response(request=request, request_name='Профили Flamp',
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

        except FlampProfile.DoesNotExist:
            log_error_response(
                request=request,
                service_name='Профили Flamp(Обновление)',
                exception='Юзер не найден',
                exc_info=True,
            )

            return Response({'error': 'Профиль не найден!'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            log_error_response(
                request=request,
                service_name='Профили Flamp(Обновление)',
                exc_info=True,
                data=masked_data,
                exception=str(e),
            )

            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def link_profile(self, request, profile_id):
        """
        Привязывает профиль Flamp к микросервису.

        Как работает:
        - Проверяет, существует ли профиль в БД:
            - Нет → 404.
            - Не принадлежит пользователю → 403.
        - Собирает данные профиля и передаёт в `link_profile_to_flamp()`.
        - Получает из микросервиса список филиалов.
        - Удаляет старые филиалы в БД, записывает новые.
        - Делает профиль `is_active = True`, если есть филиалы.
        - Логирует и возвращает успешный ответ.

        :param request: Запрос от клиента.
        :param profile_id: ID профиля, который нужно привязать.
        :return: JSON-ответ с результатом привязки.
        """
        user_id = request.user.id
        logger.debug(f'user: {user_id}')

        try:
            # Синхронно получаем профиль
            profile = FlampProfile.objects.select_related('user').get(id=profile_id)
        except FlampProfile.DoesNotExist:

            log_error_response(
                request=request,
                service_name='Профили Flamp(Связка)',
                exception='Профиль не найден'
            )

            return Response({"error": "Профиль не найден!"}, status=status.HTTP_404_NOT_FOUND)

        logger.info(f"Профиль {profile.id} - {profile.username} найден")

        # Проверка принадлежности профиля пользователю
        if profile.user_id != user_id:
            log_error_response(
                request=request,
                service_name='Профили Flamp(Связка)',
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
            response_data = async_to_sync(link_profile_to_flamp)(data=data)
            logger.debug(f"Результат link_profile_to_2gis:\n\n{response_data}")

            # Получаем список филиалов из ответа
            filials = response_data.get("extras", {}).get("filials", [])
            filial_data = []

            for filial in filials:
                filial_data.append({
                    'id': filial['filial_id'],  # Используем filial_id вместо id
                    'name': filial['name']
                })

            # Синхронно удаляем старые филиалы
            FlampFilial.objects.filter(profile=profile).delete()

            # Синхронно создаём новые
            for filial in filial_data:
                FlampFilial.objects.create(
                    flamp_filial_id=int(filial['id']),
                    profile=profile,
                    name=filial['name']
                )

            # Активируем профиль, если есть филиалы
            profile.is_active = True
            profile.save()

            logger.debug(f"Новые филиалы - {filial_data}")

            log_response(request=request, request_name="Профили Flamp",
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
            error_info = "Неизвестная ошибка"

            try:
                # Преобразуем строку в JSON
                error_json = json.loads(str(e))

                # Достаем message из detail, если есть
                error_info = error_json.get("detail", {}).get("message", "Ошибка без описания")
            except json.JSONDecodeError:
                # Если строка не JSON, просто берём текст ошибки
                error_info = str(e)

            log_error_response(
                request=request,
                service_url='api/users/create or api/users/{owner_id}/update',
                service_name='Микросервис Flamp',
                profile_id=profile_id,
                data=masked_data,
                exception=str(e),
                error_message=error_info,
                exc_info=True,

            )

            return Response({"error": error_info}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
