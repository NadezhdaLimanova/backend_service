from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import User, ConfirmEmailUser
from .serializers import UserSerializer
from django.http import JsonResponse
from rest_framework.request import Request
from django.contrib.auth import authenticate, login


class RegisterUser(APIView):
    """
    Регистрация пользователя
    """

    def post(self, request, *args, **kwargs):
        if {'first_name', 'last_name', 'email', 'password'}.issubset(request.data):

            serializer = UserSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.save()
                user.set_password(request.data['password'])
                user.save()
                user_str = user.__str__()
                return Response({'Status': True, 'User': user_str})
            else:
                return Response({'Status': False, 'Errors': serializer.errors})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class ConfirmEmail(APIView):
    """
    Подтверждение почтового адреса
    """

    def post(self, request, *args, **kwargs):
        email = request.query_params.get('email')
        token = request.query_params.get('token')
        if email and token:
            token_object = ConfirmEmailUser.object.filter(user__email=email,
                                                            key_token=token).first()
            if token_object:
                token_object.user.is_active = True
                token_object.user.save()
                token_object.delete()
                return Response({'Status': True})
            else:
                return Response({'Status': False, 'Errors': 'неправильно указан email'})
        else:
            return Response({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class LoginUser(APIView):
    """
    Аутентификация пользователя
    """

    def post(self, request, *args, **kwargs):
        if {'email', 'password'}.issubset(request.data):
            user = authenticate(request, username=request.data['email'], password=request.data['password'])
            if user:
                if user.check_password(request.data['password']):
                    if user.is_active:
                        login(request, user)
                        token = ConfirmEmailUser.object.get_or_create(user_id=user.pk)
                        return Response({'Status': True, 'User': user.key_token})
                    else:
                        return Response({'Status': False, 'Errors': 'Аккаунт не активирован'})
                else:
                    return Response({'Status': False, 'Errors': 'Неверный пароль'})
            else:
                return Response({'Status': False, 'Errors': 'Пользователь не найден'})
        return Response({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})