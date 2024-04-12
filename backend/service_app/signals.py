# from django.core.mail import EmailMultiAlternatives
from django.db.models.signals import post_save
from django.dispatch import receiver, Signal
from django_rest_passwordreset.signals import reset_password_token_created
from .models import User, ConfirmEmailUser
from django.core.mail import send_mail
from django.conf import settings
from typing import Type

new_user_registered = Signal()


@receiver(post_save, sender=User)
def send_activation_email(sender: Type[User], instance: User, created: bool, **kwargs):
    if created and not instance.is_active:
        token = ConfirmEmailUser.object.get_or_create(user_id=instance.pk)
        from_email = settings.EMAIL_HOST_USER
        msg = (f'Для подтверждения регистрации перейдите по ссылке: '
               f'http://127.0.0.1:8000/api/v1/user/register/confirm/{token[0].key_token}')
        send_mail('Подтверждение регистрации', msg, from_email, [instance.email], fail_silently=False)