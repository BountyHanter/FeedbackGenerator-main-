"""
URL configuration for FeedbackGenerator project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

from django.contrib.auth import views as auth_views

from main_site.views.auth import user_login

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth
    path('login/', user_login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('', include('main_site.urls')),
]


def custom_404(request, exception=None):
    return JsonResponse({"error": "Ресурс не найден", "status": 404}, status=404)


def custom_500(request):
    return JsonResponse({"error": "Внутренняя ошибка сервера", "status": 500}, status=500)


def custom_403(request, exception=None):
    return JsonResponse({"error": "Доступ запрещён", "status": 403}, status=403)


def custom_400(request, exception=None):
    return JsonResponse({"error": "Некорректный запрос", "status": 400}, status=400)


handler404 = 'FeedbackGenerator.urls.custom_404'
handler500 = 'FeedbackGenerator.urls.custom_500'
handler403 = 'FeedbackGenerator.urls.custom_403'
handler400 = 'FeedbackGenerator.urls.custom_400'
