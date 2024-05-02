import os

import yaml
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.contrib.auth.validators import UnicodeUsernameValidator
from django_rest_passwordreset.tokens import get_token_generator
from rest_framework.response import Response

types_of_users = (('shop', 'Магазин'), ('buyer', 'Покупатель'))

status_of_orders = (
    ('new', 'Новый'),
    ('in_progress', 'В процессе'),
    ('confirmed', 'Подтвержден'),
    ('sent', 'Отправлен'),
    ('done', 'Завершена'),
    ('canceled', 'Отменен'))


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
            if instance:
                instances.append(instance)
        return instances

    @classmethod
    def _create_instance_from_yaml(cls, item):
        raise NotImplementedError("Метод _create_instance_from_yaml() должен быть"
                                  " определен в дочерней модели.")


class Shop(YamlLoaderMixin, models.Model):

    name = models.CharField(max_length=50, verbose_name='Название')
    url = models.URLField(verbose_name='Ссылка на магазин')
    user = models.ForeignKey(User, verbose_name='Пользователь', related_name='shops',
                             on_delete=models.CASCADE)
    status = models.BooleanField(verbose_name='Статус получения заказа', default=True)

    @classmethod
    def _create_instance_from_yaml(cls, item):
        user_id = item.get('user_id')
        user = User.objects.get(id=user_id)
        name = item.get('shop').get('name')
        url = item.get('shop').get('url')
        return cls.objects.create(name=name,
                                  url=url, user_id=user.id)

    # @classmethod
    # def load_from_yaml(cls, file_path):
    #     import yaml
    #     with open(file_path, 'r', encoding='utf-8') as file:
    #         data = yaml.safe_load(file)
    #     shops = []
    #     for shop_data in data:
    #         user_id = shop_data.get('user_id')
    #         user = User.objects.get(id=user_id)
    #         name = shop_data.get('shop').get('name')
    #         url = shop_data.get('shop').get('url')
    #         existing_shop = cls.objects.filter(name=name, url=url).first()
    #         if not existing_shop:
    #             shop = cls.objects.create(name=name,
    #                                   url=url, user_id=user.id)
    #             shops.append(shop)
    #         else:
    #             shops.append(existing_shop)
    #     return shops

    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = "Список магазинов"

    def __str__(self):
        return f'{self.name} {self.url}'


class Category(models.Model):

    # objects = models.manager.Manager()

    name = models.CharField(max_length=50, verbose_name='Название')
    shops = models.ManyToManyField(Shop, verbose_name='Магазины', related_name='categories')

    @classmethod
    def load_from_yaml(cls, file_path):
        import yaml
        with open(file_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
        categories = []
        for item in data:
            if 'categories' in item:
                categories_data = item['categories']
                for category_data in categories_data:
                    category_id = category_data.get('id')
                    name = category_data.get('name')
                    existing_category = cls.objects.filter(id=category_id, name=name).first()
                    if not existing_category:
                        category = cls.objects.create(id=category_id,
                                                  name=name)
                        categories.append(category)
                    else:
                        categories.append(existing_category)
        return categories

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = "Список категорий"

    def __str__(self):
        return f'{self.name}'


class Goods(models.Model):

    name = models.CharField(max_length=50, verbose_name='Название')
    category = models.ForeignKey(Category, verbose_name='Категория', related_name='products',
                                 on_delete=models.CASCADE)

    @classmethod
    def load_from_yaml(cls, file_path):
        import yaml
        with open(file_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
        goods = []
        for item in data:
            if 'goods' in item:
                goods_data = item['goods']
                for product in goods_data:
                    name = product.get('name')
                    existing_goods = cls.objects.filter(name=name).first()
                    if not existing_goods:
                        product = cls.objects.create(name=name)
                        goods.append(product)
                    else:
                        goods.append(existing_goods)
        return goods

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = "Список товаров"

    def __str__(self):
        return f'{self.name}'