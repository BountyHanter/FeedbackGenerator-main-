from django.http import HttpRequest, HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User
from django.shortcuts import render, redirect


def user_login(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        # Check if the user exists and is active
        try:
            user = User.objects.get(username=username)
            if not user.is_active:
                return JsonResponse({'error': 'Ваш аккаунт деактивирован. Обратитесь к администрации.'}, status=403)
        except User.DoesNotExist:
            return JsonResponse({'error': 'Юзер не найден.'}, status=404)

        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return JsonResponse({'message': 'Удачная авторизация.'}, status=200)
        else:
            return JsonResponse({'error': 'Не верный логин или пароль.'}, status=400)
    return JsonResponse({'error': 'Метод не разрешён!'}, status=405)
