from django.contrib.auth.models import User
from django.db import models


class DgisProfile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dgis_profiles')
    username = models.CharField(max_length=50)
    name = models.CharField(max_length=50, blank=True, null=True)
    hashed_password = models.CharField(max_length=100)
    is_active = models.BooleanField(default=False)  # Связан ли аккаунт с сервисом

    def __str__(self):
        return f"Профиль для {self.user.username}"


class DgisFilial(models.Model):
    profile = models.ForeignKey(DgisProfile, on_delete=models.CASCADE, related_name="filials")
    filial_id = models.CharField(max_length=50)  # ID филиала
    name = models.CharField(max_length=255)  # Название филиала
    is_active = models.BooleanField(default=False)  # Выбран ли филиал юзером

    def __str__(self):
        return f"{self.name} ({self.filial_id})"
