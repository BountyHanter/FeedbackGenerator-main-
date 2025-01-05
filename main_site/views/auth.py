from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.models import User


class UserLoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]  # Или другие нужные разрешения

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        # Проверим, что такой пользователь существует
        try:
            user_obj = User.objects.get(username=username)
            if not user_obj.is_active:
                return Response({'error': 'Ваш аккаунт деактивирован. Обратитесь к администрации.'},
                                status=status.HTTP_403_FORBIDDEN)
        except User.DoesNotExist:
            return Response({'error': 'Пользователь не найден.'},
                            status=status.HTTP_404_NOT_FOUND)

        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return Response({'message': 'Удачная авторизация.'},
                            status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Неверный логин или пароль.'},
                            status=status.HTTP_400_BAD_REQUEST)


class LogoutAPIView(APIView):
    def post(self, request, *args, **kwargs):
        logout(request)
        return Response({"detail": "Успешный логаут"}, status=status.HTTP_200_OK)
