from django.core.validators import URLValidator
from django.db import IntegrityError
from django.db.models import Q, Sum, F
from django.shortcuts import render
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import (User, ConfirmEmailUser, Contact, Shop, Category, Goods,
                     ProductInfo, Order, OrderItem)
from .serializers import (UserSerializer, ContactSerializer,
                          ShopSerializer, CategorySerializer,
                          GoodsSerializer, ProductInfoSerializer,
                          OrderItemSerializer, OrderSerializer)
from django.http import JsonResponse
from rest_framework.request import Request
from django.contrib.auth import authenticate, login
from rest_framework.authtoken.models import Token
import yaml
import os
from ujson import loads as load_json


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
            print(user)
            if user:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)
                    login(request, user)
                    print(token.key)
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
                serializer = ContactSerializer(data=request.data, context={'request': request})
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
        if 'id' not in request.data:
            return Response({'Status': False, 'Errors': 'Не указан ID контакта'})
        contact = Contact.objects.filter(id=request.data['id'], user_id=request.user.id).first()
        if contact is not None:
            serializer = ContactSerializer(contact, data=request.data, context={'request': request}, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({'Status': True, 'Contact': serializer.data})
            else:
                return Response({'Status': False, 'Errors': serializer.errors})
        else:
            return Response({'Status': False, 'Errors': 'Контакт не найден'})

    # удаление контакта
    def delete(self, request, *args, **kwargs):
        contact_id = request.data.get('id')
        contact = Contact.objects.filter(id=contact_id, user_id=request.user.id).first()
        if contact:
            contact.delete()
            return Response({'Status': True})
        else:
            return Response({'Status': False, 'Errors': 'Контакт не найден'})


class ShopView(APIView):
    """
    Получение списка магазинов
    """

    serializer_class = ShopSerializer

    def get(self, request):
        file_path = os.path.join(os.path.dirname(__file__), 'data/shop1.yaml')
        queryset = Shop.load_from_yaml(file_path)
        serializer = self.serializer_class(queryset, many=True)
        return Response({'Status': True, 'Shops': serializer.data})



class CategoryView(APIView):
    """
    Получение списка категорий
    """

    serializer_class = CategorySerializer

    def get(self, request):
        file_path = os.path.join(os.path.dirname(__file__), 'data/shop1.yaml')
        queryset = Category.load_from_yaml(file_path)
        serializer = self.serializer_class(queryset, many=True)
        return Response({'Status': True, 'Categories': serializer.data})

class GoodsView(APIView):
    """
    Получение списка товаров
    """

    serializer_class = GoodsSerializer

    def get(self, request):
        file_path = os.path.join(os.path.dirname(__file__), 'data/shop1.yaml')
        queryset = Goods.load_from_yaml(file_path)
        serializer = self.serializer_class(queryset, many=True)
        return Response({'Status': True, 'Goods': serializer.data})

class ProductInfoView(APIView):
    """
    Импорт информации о продукте
    """

    def get(self, request):
        file_path = os.path.join(os.path.dirname(__file__), 'data/shop1.yaml')
        queryset = ProductInfo.load_from_yaml(file_path)
        serializer = self.serializer_class(queryset, many=True)
        return Response({'Status': True, 'ProductInfo': serializer.data})

class ProductInfoFiltersView(APIView):
    """
    Получение информации о продукте по фильтрам
    """
    def get(self, request, *args, **kwargs):

        query = Q(shop__status=True)
        shop_id = request.query_params.get('shop_id')
        category_id = request.query_params.get('category_id')

        if shop_id:
            query = query & Q(shop_id=shop_id)
        if category_id:
            query = query & Q(product__category_id=category_id)

        queryset = (ProductInfo.objects.filter(query).select_related('shop', 'product__category').
                    prefetch_related('product_parameters__parameter').distinct())

        serializer = ProductInfoSerializer(queryset, many=True)

        return Response(serializer.data)


class BasketView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):

        if not request.user.is_authenticated:
            return Response({'Status': False, 'Error': 'User is not authenticated'})
        basket = Order.objects.filter(
            user_id=request.user.id, status='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        if basket:
            serializer = OrderSerializer(basket, many=True)
            return Response({'Status': True, 'Basket': serializer.data})


    def post(self, request, *args, **kwargs):

        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'User is not authenticated'},
                                status=403)
        items_string = request.data.get('items')
        if items_string:
            basket, _ = Order.objects.get_or_create(user_id=request.user.id, status='basket')
            objects_created = 0
            for order_item in items_string:
                order_item.update({'order': basket.id})
                serializer = OrderItemSerializer(data=order_item)
                if serializer.is_valid():
                    try:
                        serializer.save()
                    except IntegrityError as error:
                        return JsonResponse({'Status': False, 'Errors': str(error)})
                    else:
                        objects_created += 1
                else:
                    return JsonResponse({'Status': False, 'Errors': serializer.errors})
                return JsonResponse({'Status': True, 'Создано объектов': objects_created})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    def put(self, request, *args, **kwargs):

        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'User is not authenticated'},
                                status=403)
        items = request.data.get('items')
        if items:
            basket, _ = Order.objects.get_or_create(user_id=request.user.id, status='basket')
            objects_updated = 0
            for order_item in items:
                if isinstance(order_item['id'], int) and isinstance(order_item['quantity'], int):
                    objects_updated += OrderItem.objects.filter(id=order_item['id'], order_id=basket.id).update(
                        quantity=order_item['quantity'])
            basket_info = Order.objects.select_related('contact').get(id=basket.id)
            return JsonResponse({'Status': True, 'Обновлено объектов': objects_updated, 'basket': basket_info.id})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    def delete(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'User is not authenticated'},
                                status=403)
        items = request.data.get('items')
        if items:
            basket, _ = Order.objects.get_or_create(user_id=request.user.id, status='basket')
            objects_deleted = 0
            for order_item in items:
                if isinstance(order_item['id'], int):
                    objects_deleted += OrderItem.objects.filter(id=order_item['id'], order_id=basket.id).delete()[0]
            return JsonResponse({'Status': True, 'Удалено объектов': objects_deleted})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class OrderView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'User is not authenticated'},
                                status=403)
        orders = Order.objects.filter(user_id=request.user.id).prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        if orders:
            serializer = OrderSerializer(orders, many=True)
            return JsonResponse({'Status': True, 'Orders': serializer.data}, safe=False)


    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'User is not authenticated'},
                                status=403)
        if {'id', 'contact'}.issubset(request.data):
            if 'id' in request.data and request.data['id'].isdigit():
                try:
                    new_order = Order.objects.get(
                        id=request.data['id'], user_id=request.user.id)
                    new_order.contact_id = request.data['contact']
                    new_order.status = 'new'
                    new_order.save()
                except IntegrityError as error:
                    return JsonResponse({'Status': False, 'Errors': str(error)})
                return JsonResponse({'Status': True, 'order': new_order.id})
        else:
            return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})



# class BuyerUpdate(APIView):
#
#     def post(self, request, *args, **kwargs):
#         if not request.user.is_authenticated:
#             return JsonResponse({'Status': False, 'Error': 'User is not authenticated'},
#                                 status=403)
#         if request.user.type_of_user != 'shop':
#             return JsonResponse({'Status': False, 'Error': 'Только для магазинов'},
#                                 status=403)
#         url = request.data.get('url')
#         if url:
#             try:
#                 user = Shop.objects.get(user_id=request.user.id)
#             except Shop.DoesNotExist:
#                 return JsonResponse({'Status': False, 'Error': 'Магазин не существует'})
#             validate_url = URLValidator()
#             try:
#                 validate_url(url)
#             except ValidationError:
#                 return JsonResponse({'Status': False, 'Error': 'Некорректная ссылка'})
#             else:
#                 stream = requests.get(url).content
#                 data = load_yaml(stream, Loader=Loader)
#
#
#         if user is not None:
#             user.is_active = True
#             user.save()
#             return JsonResponse({'Status': True})
#         return JsonResponse({'Status': False, 'Errors': 'Пользователь не найден'})


