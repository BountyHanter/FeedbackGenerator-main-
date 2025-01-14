import logging

from django.contrib.auth.models import User
from django.db import models

logger = logging.getLogger(__name__)


class DgisProfile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dgis_profiles')
    username = models.CharField(max_length=50)
    name = models.CharField(max_length=50, blank=True, null=True)
    hashed_password = models.CharField(max_length=100)
    is_active = models.BooleanField(default=False)  # Связан ли аккаунт с сервисом

    def __str__(self):
        return f"Профиль для {self.user.username}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None  # Проверяем, новый ли объект
        super().save(*args, **kwargs)  # Сохраняем объект, чтобы получить self.pk

        if is_new:
            logger.info("2GIS Профиль",
                        extra={'dgis_profile_id': self.pk,
                               'username': self.username,
                               'action': 'create'})
        else:
            logger.info("2GIS Профиль",
                        extra={'dgis_profile_id': self.pk,
                               'username': self.username,
                               'is_active': self.is_active,
                               'action': 'update'})

    def delete(self, *args, **kwargs):
        logger.warning("2GIS Профиль",
                       extra={'dgis_profile_id': self.pk,
                              'username': self.username,
                              'action': 'delete'})

        super().delete(*args, **kwargs)


class DgisFilial(models.Model):
    profile = models.ForeignKey(DgisProfile, on_delete=models.CASCADE, related_name="filials")
    dgis_filial_id = models.CharField(max_length=50)  # ID филиала
    name = models.CharField(max_length=255)  # Название филиала
    is_active = models.BooleanField(default=False)  # Выбран ли филиал юзером

    def __str__(self):
        return f"{self.name} ({self.dgis_filial_id})"

    def save(self, *args, **kwargs):
        is_new = self.pk is None  # Проверяем, новый ли объект
        super().save(*args, **kwargs)  # Сохраняем объект, чтобы получить self.pk

        if is_new:
            logger.info("2GIS Филиал",
                        extra={'owner_profile': self.profile.pk,
                               'filial_id': self.pk,
                               'dgis_filial_id': self.dgis_filial_id,
                               '_name': self.name,
                               'action': 'create'})
        else:
            logger.info("2GIS Филиал",
                        extra={'owner_profile': self.profile.pk,
                               'filial_id': self.pk,
                               'dgis_filial_id': self.dgis_filial_id,
                               '_name': self.name,
                               'is_active': self.is_active,
                               'action': 'update'})

    def delete(self, *args, **kwargs):
        logger.warning("2GIS Филиал",
                       extra={'filial_id': self.pk,
                              '_name': self.name,
                              'action': 'delete'})

        super().delete(*args, **kwargs)
