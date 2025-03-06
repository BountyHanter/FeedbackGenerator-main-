import logging

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from FeedbackGenerator.utils.logging_templates import log_error_response, log_response
from main_site.models import FlampProfile

logger = logging.getLogger(__name__)


class FlampFilialAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, profile_id):
        """
        Возвращает список филиалов для указанного профиля пользователя.
        """
        try:
            logger.info(f"Данные запроса филиалов Flamp - {profile_id}, {request.user.id}")
            # Проверяем, что профиль принадлежит текущему пользователю
            profile = get_object_or_404(FlampProfile, id=profile_id, user=request.user)
        except Exception as e:
            log_error_response(
                request=request,
                service_name='Профили Flamp',
                exc_info=True,
                exception=str(e),
                profile_id=profile_id,
            )
            raise
        # Получаем все филиалы, связанные с профилем
        filials = profile.flamp_filials.all()

        # Формируем JSON-ответ с данными филиалов
        filials_data = [
            {
                'id': filial.id,
                'flamp_filial_id': filial.flamp_filial_id,
                'name': filial.name,
                'is_active': filial.is_active,
            }
            for filial in filials
        ]

        logger.debug(f"Список филиалов:\n\n{filials_data}")

        log_response(request=request, request_name="Филиалы Flamp",
                     profile_id=profile.id,
                     profile_name=profile.name,
                     filials_count=len(filials),
                     )

        return Response({
            'profile_id': profile.id,
            'profile_name': profile.name,
            'filials': filials_data,
        }, status=200)
