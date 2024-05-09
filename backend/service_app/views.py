from distutils.util import strtobool
from django.core.validators import URLValidator
from django.db import IntegrityError
from django.db.models import Q, Sum, F
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import (User, ConfirmEmailUser, Contact, Shop, Category, Goods,
                     ProductInfo, Order, OrderItem, ProductParameter, Parameter)
from .serializers import (UserSerializer, ContactSerializer,
                          ShopSerializer, CategorySerializer,
                          GoodsSerializer, ProductInfoSerializer,
                          OrderItemSerializer, OrderSerializer)
from django.http import JsonResponse
from django.contrib.auth import authenticate, login
from rest_framework.authtoken.models import Token
import os
from yaml import load as load_yaml, Loader
from requests import get


class RegisterUser(APIView):
    """
    Регистрация пользователя.
    метод post проверяет и сохраняет данные пользователя
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
    Подтверждение почтового адреса.
    метод post проверяет наличие почты и токена в запросе, если они совпадают с базой данных - активирует пользователя
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
    метод post проверяет наличие пароля и почты в запросе, если они совпадают с базой данных -
    авторизует пользователя и возвращает токен
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
    метод post проверяет авторизован ли пользователь, присутствуют ли данные в запросе
    и обновляет данные пользователя в соответствии с запросом
    метод get проверяет авторизован ли пользователь и возвращает данные пользователя
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
        if 'type_of_user' in request.data:
            request.user.type_of_user = request.data['type_of_user']
            request.user.save()
        serializer = UserSerializer(request.user)
        return Response({'Status': True, 'User': serializer.data})


class ContactView(APIView):
    """
    Получение, создание и изменение контактов пользователя
    метод get проверяет авторизован ли пользователь и возвращает контакты пользователя
    метод post проверяет авторизован ли пользователь, есть ли в запросе данные о контактах пользователя
    и создает контакт
    метод put проверяет авторизован ли пользователь, есть ли в запросе данные о контактах пользователя
    и изменяет данные о контактах пользователя
    метод delete проверяет авторизован ли пользователь и удаляет выбранный контакт пользователя
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
    метод get возвращает список магазинов, импортируя информацию из yaml-файла
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
    метод get возвращает список категорий, импортируя информацию из yaml-файла
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
    метод get возвращает список товаров, импортируя информацию из yaml-файла
    """

    serializer_class = GoodsSerializer

    def get(self, request):
        file_path = os.path.join(os.path.dirname(__file__), 'data/shop1.yaml')
        queryset = Goods.load_from_yaml(file_path)
        serializer = self.serializer_class(queryset, many=True)
        return Response({'Status': True, 'Goods': serializer.data})

class ProductInfoView(APIView):
    """
    Получение информации о каждом товаре
    метод get возвращает информацию о каждом товаре, импортируя информацию из yaml-файла
    """

    def get(self, request):
        file_path = os.path.join(os.path.dirname(__file__), 'data/shop1.yaml')
        queryset = ProductInfo.load_from_yaml(file_path)
        serializer = self.serializer_class(queryset, many=True)
        return Response({'Status': True, 'ProductInfo': serializer.data})

class ProductInfoFiltersView(APIView):
    """
    Получение информации о продукте по фильтрам
    метод get выводит информацию о товаре, согласно переданным фильтрам по магазину и категории
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
    """
    получение корзины пользователя
    метод get проверяет авторизован ли пользователь и возвращает информацию о корзине
    метод post проверяет авторизован ли пользователь и добавляет в корзину товары
    метод put проверяет авторизован ли пользователь и обновляет информацию о корзине
    метод delete проверяет авторизован ли пользователь и удаляет из корзины все лишние позиции
    """
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
    """
    получение списка заказов пользователя
    метод get проверяет авторизован ли пользователь и возвращает список заказов
    метод post проверяет авторизован ли пользователь и создает новый заказ
    метод put проверяет авторизован ли пользователь и обновляет статус заказа
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    # получение списка заказов пользователя
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
        else:
            return JsonResponse({'Status': False, 'Error': 'Заказов нет'})

    # создание нового заказа
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

    # изменение статуса заказа
    def put(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'User is not authenticated'},
                                status=403)
        if {'id', 'status'}.issubset(request.data):
            if 'id' in request.data and request.data['id'].isdigit():
                try:
                    order = Order.objects.get(
                        id=request.data['id'], user_id=request.user.id)
                    order.status = request.data['status']
                    order.save()
                except IntegrityError as error:
                    return JsonResponse({'Status': False, 'Errors': str(error)})
                return JsonResponse({'Status': True, 'order': order.id})
        else:
            return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class ShopUpdate(APIView):
    """
    обновление информации от магазина
    метод post проверяет авторизован ли пользователь и обновляет информацию о магазине, категориях и товарахб
    импортируя ее из файла по ссылке
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'User is not authenticated'},
                                status=403)
        if request.user.type_of_user != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'},
                                status=403)
        url = request.data.get('url')
        if url:
            validate_url = URLValidator()
            try:
                validate_url(url)
            except ValidationError:
                return JsonResponse({'Status': False, 'Error': 'Некорректная ссылка'})
            else:
                stream = get(url).content
                stream = stream.decode('utf-8')
                data = load_yaml(stream, Loader=Loader)

            shop, _ = Shop.objects.get_or_create(name=data[0]['users'][0]['shop']['name'], url=data[0]['users'][0]['shop']['url'], user_id=request.user.id)
            for category in data[1]['categories']:
                category, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
                category.shops.add(shop.id)
                category.save()
            ProductInfo.objects.filter(shop_id=shop.id).delete()
            for item in data[2]['goods']:
                product, _ = Goods.objects.get_or_create(name=item['name'], category_id=item['category'])
                product_info = ProductInfo.objects.create(product_id=product.id,
                                                          external_id=item['id'],
                                                          model=item['model'],
                                                          price=item['price'],
                                                          price_rrc=item['price_rrc'],
                                                          quantity=item['quantity'],
                                                          shop_id=shop.id)
                for name, value in item['parameters'].items():
                    parameter, _ = Parameter.objects.get_or_create(name=name)
                    ProductParameter.objects.get_or_create(product_info_id=product_info.id,
                                                           parameter_id=parameter.id,
                                                           value=value)

                return JsonResponse({'Status': True})
        return JsonResponse({'Status': False, 'Errors': 'Пользователь не найден'})


class ShopStatus(APIView):
    """
    изменение статуса магазина
    метод post проверяет авторизован ли пользователь и обновляет статус получения заказа
    метод get проверяет авторизован ли пользователь и возвращает статус получения заказа
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'User is not authenticated'},
                                status=403)
        if request.user.type_of_user != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'},
                                status=403)
        status = request.data.get('status')
        if status:
            try:
                shop = Shop.objects.filter(user_id=request.user.id).update(status=strtobool(status))
                return JsonResponse({'Status': True})
            except ValueError as error:
                return JsonResponse({'Status': False, 'Error': str(error)})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'User is not authenticated'},
                                status=403)
        if request.user.type_of_user != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'},
                                status=403)
        shop = request.user.shops.first()
        serializer = ShopSerializer(shop)
        return Response(serializer.data)


class ListOfOrdersView(APIView):
    """
    список заказов
    метод get проверяет авторизован ли пользователь и возвращает список заказов
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):

        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type_of_user != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        orders = Order.objects.filter(
            user_id=request.user.id).exclude(status='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        if orders:
            serializer = OrderSerializer(orders, many=True)
            return Response(serializer.data)
        else:
            return JsonResponse({'Status': False, 'Error': 'Заказов нет'})




