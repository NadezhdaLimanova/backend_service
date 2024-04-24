from django.shortcuts import render
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import User, ConfirmEmailUser, Contact
from .serializers import UserSerializer, ContactSerializer
from django.http import JsonResponse
from rest_framework.request import Request
from django.contrib.auth import authenticate, login
from rest_framework.authtoken.models import Token


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
            if request.user.is_authenticated:
                return Response({'Status': False, 'Errors': 'Пользователь уже аутентифицирован'})
            user = authenticate(request, username=request.data['email'], password=request.data['password'])

            if user:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)
                    login(request, user)
                    return Response({'Status': True, 'Token': token.key, 'User': user.email})
                else:
                    return Response({'Status': False, 'Errors': 'Аккаунт не активирован'})
            else:
                return Response({'Status': False, 'Errors': 'Пользователь не найден'})
        return Response({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    def check_token_in_db(self, token_key):
        try:
            token = Token.objects.get(key=token_key)
            return 'True'
        except Token.DoesNotExist:
            return 'False'



class ModifyUser(APIView):
    """
    Получение и изменение данных пользователя
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response({'Status': True, 'User': serializer.data})

    def post(self, request, *args, **kwargs):
        if 'first_name' in request.data:
            request.user.first_name = request.data['first_name']
            request.user.save()
        if 'last_name' in request.data:
            request.user.last_name = request.data['last_name']
            request.user.save()
        if 'email' in request.data:
            request.user.email = request.data['email']
            request.user.save()
        serializer = UserSerializer(request.user)
        return Response({'Status': True, 'User': serializer.data})


class ContactView(APIView):
    """
    Получение, создание и изменение контактов пользователя
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    # получение контактов
    def get(self, request, *args, **kwargs):
        contacts = Contact.objects.filter(user=request.user)
        serializer = ContactSerializer(contacts, many=True)
        return Response({'Status': True, 'Contacts': serializer.data})

    # создание контакта
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if {'city', 'street', 'phone'}.issubset(request.data):
                request.data['user'] = request.user.id
                serializer = ContactSerializer(data=request.data)
                if serializer.is_valid():
                    print(request.data)
                    serializer.save(user=request.user)
                    return Response({'Status': True, 'Contact': serializer.data})
                else:
                    return Response({'Status': False, 'Errors': serializer.errors})
            else:
                return Response({'Status': False, 'Errors': 'Missing required fields'})
        else:
            return Response({'Status': False, 'Errors': 'User is not authenticated'})


    # изменение контакта
    def put(self, request, *args, **kwargs):
        # contact = Contact.objects.get(id=request.data['id'])
        contact = Contact.objects.filter(id=request.data['id'],user_id=request.user.id).first()
        print(contact)
        if contact:
            serializer = ContactSerializer(contact, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({'Status': True, 'Contact': serializer.data})
            else:
                return Response({'Status': False, 'Errors': serializer.errors})

    # удаление контакта
    def delete(self, request, *args, **kwargs):
        contact = Contact.objects.filter(id=request.data['id'],user_id=request.user.id).first()
        if contact:
            contact.delete()
            return Response({'Status': True})
        else:
            return Response({'Status': False, 'Errors': 'Контакт не найден'})

