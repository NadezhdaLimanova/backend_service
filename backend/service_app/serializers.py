from rest_framework import serializers
from .models import User, Contact, Shop, Category, Goods
from django.contrib.auth.password_validation import validate_password


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ('id', 'city', 'street', 'house', 'structure', 'building', 'apartment', 'phone')
        read_only_fields = ('id',)

    def validate(self, data):
        user = self.context['request'].user
        existing_contact = Contact.objects.filter(user=user, **data).exists()
        if existing_contact:
            raise serializers.ValidationError('Contact with the same data already exists')
        return data


class UserSerializer(serializers.ModelSerializer):
    contacts = ContactSerializer(read_only=True, many=True)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('User with this email already exists')
        return value

    # проверяем пароль на сложность
    def validate_password(self, value):
        try:
            validate_password(value)
        except Exception as password_error:
            error_array = []
            # noinspection PyTypeChecker
            for item in password_error:
                error_array.append(item)
            raise serializers.ValidationError({'password': error_array})
        else:
            return value

    def create(self, validated_data):

        if 'password' not in validated_data:
            raise serializers.ValidationError('Password is required')

        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
        )

        return user

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email', 'password', 'contacts')
        read_only_fields = ('id', )


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ('id', 'name', 'url')
        read_only_fields = ('id',)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name')
        read_only_fields = ('id',)


class GoodsSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()

    class Meta:
        model = Goods
        fields = ('name', 'category')
