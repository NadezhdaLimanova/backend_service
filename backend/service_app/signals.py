# from django.core.mail import EmailMultiAlternatives
from django.db.models.signals import post_save
from django.dispatch import receiver, Signal
from .models import User, ConfirmEmailUser, Order
from django.core.mail import send_mail
from django.conf import settings
from typing import Type

new_user_registered = Signal()

new_order = Signal()


@receiver(post_save, sender=User)
def send_activation_email(sender: Type[User], instance: User, created: bool, **kwargs):
    if created and not instance.is_active:
        token = ConfirmEmailUser.object.get_or_create(user_id=instance.pk)
        from_email = settings.EMAIL_HOST_USER
        msg = (f'Для подтверждения регистрации перейдите по ссылке: '
               f'http://127.0.0.1:8000/api/v1/user/register/confirm/?email={instance.email}&token={token[0].key_token}')
        send_mail('Подтверждение регистрации', msg, from_email, [instance.email], fail_silently=False)
        print(token[0].key_token)


@receiver(post_save, sender=Order)
def send_new_order_email(sender: Type[Order], instance: Order, created: bool, **kwargs):
    print('send_new_order_email')
    if created and not instance.status == 'new':
        print('send_new_order_email2')
        from_email = settings.EMAIL_HOST_USER
        msg = f'Ваш заказ подтвержден. '
        send_mail('Заказ оформлен', msg, from_email, [instance.user.email], fail_silently=False)

