from rest_framework import serializers
from .models import User
from django.contrib.auth.password_validation import validate_password




class UserSerializer(serializers.ModelSerializer):

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('User with this email already exists')
        return value

    def validate_password(self, value): # проверяем пароль на сложность
        # sad = 'asd'
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

        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
        )

        return user

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email', 'password')
        read_only_fields = ('id', )
