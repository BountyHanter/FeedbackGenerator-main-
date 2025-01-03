import os

from django.shortcuts import get_object_or_404

from dotenv import load_dotenv
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from main_site.models.Dgis_models import DgisProfile

load_dotenv()

DGIS_SERVER_URL = os.getenv("DGIS_SERVICE_ADDRESS")


class FilialAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, profile_id):
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
                'id': filial.id,
                'dgis_filial_id': filial.dgis_filial_id,
                'name': filial.name,
                'is_active': filial.is_active,
            }
            for filial in filials
        ]

        return Response({
            'profile_id': profile.id,
            'profile_name': profile.name,
            'filials': filials_data,
        }, status=200)
