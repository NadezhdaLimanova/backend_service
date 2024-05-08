import os

import yaml
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.contrib.auth.validators import UnicodeUsernameValidator
from django_rest_passwordreset.tokens import get_token_generator
from rest_framework.response import Response

types_of_users = (('shop', 'Магазин'), ('buyer', 'Покупатель'))

status_of_orders = (
    ('basket', 'Статус корзины'),
    ('new', 'Новый'),
    ('in_progress', 'В процессе'),
    ('confirmed', 'Подтвержден'),
    ('sent', 'Отправлен'),
    ('done', 'Завершена'),)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    email = models.EmailField(unique=True)
    username_validator = UnicodeUsernameValidator()
    username = models.CharField(max_length=150, error_messages={
        'unique': 'user already exists',
    })
    is_active = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    type_of_user = models.CharField(verbose_name='Тип пользователя', choices=types_of_users, max_length=5, default='buyer')

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = "Список пользователей"
        ordering = ('email',)


class ConfirmEmailUser(models.Model):
    object = models.manager.Manager()
    class Meta:
        verbose_name = 'Подтверждение почты пользователя'
        verbose_name_plural = "Список подтверждений почты пользователя"

    @staticmethod
    # генерация токена сброса пароля из библиотеки django_rest_passwordreset
    def generate_key_token():
        return get_token_generator().generate_token()

    user = models.ForeignKey(User, related_name='confirm_user', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    key_token = models.CharField(max_length=80, unique=True, default=None)

    def save(self, *args, **kwargs):
        if not self.key_token:
            self.key_token = self.generate_key_token()
        super(ConfirmEmailUser, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.user}'


class Contact(models.Model):

    objects = models.manager.Manager()

    user = models.ForeignKey(User, verbose_name='Пользователь', related_name='contacts', blank=True, on_delete=models.CASCADE)

    city = models.CharField(max_length=50, verbose_name='Город')
    street = models.CharField(max_length=100, verbose_name='Улица')
    house = models.CharField(max_length=15, verbose_name='Дом', blank=True)
    structure = models.CharField(max_length=15, verbose_name='Корпус', blank=True)
    building = models.CharField(max_length=15, verbose_name='Строение', blank=True)
    apartment = models.CharField(max_length=15, verbose_name='Квартира', blank=True)
    phone = models.CharField(max_length=20, verbose_name='Телефон')

    class Meta:
        verbose_name = 'Контакты пользователя'
        verbose_name_plural = "Список контактов пользователя"

    def __str__(self):
        return f'{self.user}{self.city}{self.street}'


class YamlLoaderMixin:
    @classmethod
    def load_from_yaml(cls, file_path):
        import yaml
        with open(file_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
        instances = []
        for item in data:
            instance = cls._create_instance_from_yaml(item)
            if isinstance(instance, list):
                instances.extend(instance)
            if isinstance(instance, cls):
                instances.append(instance)
        print(instances)
        return instances



class Shop(models.Model, YamlLoaderMixin):

    name = models.CharField(max_length=50, verbose_name='Название')
    url = models.URLField(verbose_name='Ссылка на магазин')
    user = models.ForeignKey(User, verbose_name='Пользователь', related_name='shops',
                             on_delete=models.CASCADE)
    status = models.BooleanField(verbose_name='Статус получения заказа', default=True)

    @classmethod
    def _create_instance_from_yaml(cls, item):
        if 'user_id' in item:
            user_id = item.get('user_id')
            user = User.objects.get(id=user_id)
            name = item.get('shop').get('name')
            url = item.get('shop').get('url')
            existing_shop = cls.objects.filter(name=name, url=url).first()
            if not existing_shop:
                return cls.objects.create(name=name,
                                      url=url, user_id=user.id)
            else:
                return existing_shop

    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = "Список магазинов"

    def __str__(self):
        return f'{self.name} {self.url}'


class Category(models.Model, YamlLoaderMixin):

    # objects = models.manager.Manager()

    name = models.CharField(max_length=50, verbose_name='Название')
    shops = models.ManyToManyField(Shop, verbose_name='Магазины', related_name='categories')

    @classmethod
    def _create_instance_from_yaml(cls, item):
        instances = []
        if 'categories' in item:
            categories_data = item['categories']
            for category_data in categories_data:
                category_id = category_data.get('id')
                name = category_data.get('name')
                existing_category = cls.objects.filter(id=category_id, name=name).first()
                if not existing_category:
                    new_category = cls.objects.create(id=category_id,
                                              name=name)
                    instances.append(new_category)
                else:
                    instances.append(existing_category)
        return instances


    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = "Список категорий"

    def __str__(self):
        return f'{self.name}'


class Goods(models.Model, YamlLoaderMixin):

    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=50, verbose_name='Название')
    category = models.ForeignKey(Category, verbose_name='Категория', related_name='products',
                                 on_delete=models.CASCADE)

    @classmethod
    def _create_instance_from_yaml(cls, item):
        instances = []
        if 'goods' in item:
            goods_data = item['goods']
            for product in goods_data:
                category_id = product.get('category')
                name = product.get('name')
                id = product.get('id')
                print(id)
                category = Category.objects.get(pk=category_id)
                existing_goods = cls.objects.filter(id=id, name=name).first()
                if not existing_goods:
                    new_product = cls.objects.create(id=id, name=name, category=category)
                    instances.append(new_product)
                else:
                    instances.append(existing_goods)
            return instances


    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = "Список товаров"

    def __str__(self):
        return f'{self.name}'


class ProductInfo(models.Model, YamlLoaderMixin):
    external_id = models.PositiveIntegerField(verbose_name='Внешний ИД')
    model = models.CharField(max_length=100, verbose_name='Модель')
    price = models.PositiveIntegerField(verbose_name='Цена')
    price_rrc = models.PositiveIntegerField(verbose_name='Розничная цена')
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    product = models.ForeignKey(Goods, verbose_name='Товар', related_name='product_info',
                                on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, verbose_name='Магазин', related_name='product_info',
                             on_delete=models.CASCADE)

    @classmethod
    def _create_instance_from_yaml(cls, item):
        instances = []
        if 'goods' in item:
            goods_data = item['goods']
            for product_info in goods_data:
                external_id = product_info.get('id')
                model = product_info.get('model')
                price = product_info.get('price')
                price_rrc = product_info.get('price_rrc')
                quantity = product_info.get('quantity')
                shop_id = product_info.get('shop')
                shop = Shop.objects.get(pk=shop_id)
                product = Goods.objects.get(pk=external_id)
                existing_product_info = cls.objects.filter(external_id=external_id, shop=shop).first()
                if not existing_product_info:
                    new_product_info = cls.objects.create(external_id=external_id, model=model, price=price, product=product,
                                                          price_rrc=price_rrc, quantity=quantity, shop=shop)
                    instances.append(new_product_info)
                else:
                    instances.append(existing_product_info)
            return instances

    class Meta:
        verbose_name = 'Информация о продукте'
        verbose_name_plural = "Список информации о продуктах"
        constraints = [
            models.UniqueConstraint(fields=['product', 'external_id', 'shop'],
                                    name='unique_product_info')
        ]

    def __str__(self):
        return f'{self.product.name} {self.shop.name}'


class Parameter(models.Model):
    objects = models.Manager()
    name = models.CharField(max_length=50, verbose_name='Название')

    class Meta:
        verbose_name = 'Параметр'
        verbose_name_plural = "Список параметров"

    def __str__(self):
        return f'{self.name}'


class ProductParameter(models.Model, YamlLoaderMixin):
    # objects = models.Manager()
    product_info = models.ForeignKey(ProductInfo, verbose_name='Информация о продукте',
                                     related_name='product_parameters', on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, verbose_name='Параметр', related_name='product_parameters',
                                  on_delete=models.CASCADE)
    value = models.CharField(max_length=100, verbose_name='Значение')


    @classmethod
    def _create_instance_from_yaml(cls, item):
        instances = []
        if 'goods' in item:
            goods_data = item['goods']
            for product_data in goods_data:
                product_info = ProductInfo.objects.get(id=product_data['id'])
            for param_name, param_value in product_data['parameters'].items():
                parameter, created = Parameter.objects.get_or_create(name=param_name)
                product_parameter = ProductParameter.objects.create(product_info=product_info,
                                                                    parameter=parameter, value=param_value)
                existing_product_parameter = cls.objects.filter(parameter=product_parameter,
                                                                product_info=product_info).first()
                if not existing_product_parameter:
                    instances.append(product_parameter)
                else:
                    instances.append(existing_product_parameter)
            return instances

    class Meta:
        verbose_name = 'Параметр'
        verbose_name_plural = "Список параметров"
        constraints = [
            models.UniqueConstraint(fields=['product_info', 'parameter'],
                                    name='unique_product_parameter')
        ]

    def __str__(self):
        return f'{self.product_info} {self.parameter} {self.value}'


class Order(models.Model):
    objects = models.Manager()
    user = models.ForeignKey(User, verbose_name='Пользователь', related_name='orders', blank=True,
                             on_delete=models.CASCADE)
    dt = models.DateTimeField(verbose_name='Дата', auto_now_add=True)
    status = models.CharField(verbose_name='Статус', max_length=15, choices=status_of_orders, default='new')
    contact = models.ForeignKey(Contact, verbose_name='Контакты', blank=True, null=True, on_delete=models.CASCADE)


    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = "Список заказов"
        ordering = ('-dt',)

    def __str__(self):
        return f'{self.user} {self.dt} {self.status}'


class OrderItem(models.Model):
    objects = models.Manager()
    order = models.ForeignKey(Order, verbose_name='Заказ', related_name='ordered_items',
                              on_delete=models.CASCADE)
    product_info = models.ForeignKey(ProductInfo, verbose_name='Информация о продукте',
                                     related_name='ordered_items', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(verbose_name='Количество')


    # @property
    # def sum(self):
    #     return self.ordered_items.aggregate(total=Sum("quantity"))["total"]

    # @property
    # def subtotal(self):
    #     return self.quantity * self.product_info.price
    #
    # def save(self, *args, **kwargs):
    #     self.subtotal = self.quantity * self.product_info.price
    #     super(OrderItem, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'Заказанный продукт'
        verbose_name_plural = "Список заказанных продуктов"
        constraints = [
            models.UniqueConstraint(fields=['order_id', 'product_info'], name='unique_order_item'),
        ]

    def __str__(self):
        return f'{self.order} {self.product_info} {self.quantity}'
