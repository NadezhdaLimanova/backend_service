# from django.core.mail import EmailMultiAlternatives
from django.db.models.signals import post_save
from django.dispatch import receiver, Signal
from .models import User, ConfirmEmailUser, Order
from django.core.mail import send_mail
from django.conf import settings
from typing import Type
from django.utils import timezone

new_user_registered = Signal()

new_order = Signal()

"""
Ниже представлены два сигнала: send_activation_email(при регистрации нового пользователя отправляет письмо 
для подтверждения почты на email пользователя) и send_new_order_email(при создании нового заказа отправляет письмо
с информацией о заказе и его статусе)
"""


@receiver(post_save, sender=User)
def send_activation_email(sender: Type[User], instance: User, created: bool, **kwargs):
    if created and not instance.is_active:
        token = ConfirmEmailUser.object.get_or_create(user_id=instance.pk)
        from_email = settings.EMAIL_HOST_USER
        msg = (f'Для подтверждения регистрации перейдите по ссылке: '
               f'http://127.0.0.1:8000/api/v1/user/register/confirm/?email={instance.email}&token={token[0].key_token}')
        send_mail('Подтверждение регистрации', msg, from_email, [instance.email], fail_silently=False)
        print(token[0].key_token)


STATUS_MESSAGES = {
    'new': 'Ваш заказ сформирован.',
    'in_progress': 'Ваш заказ в процессе подтверждения.',
    'sent': 'Ваш заказ отправлен.',
    'done': 'Ваш заказ доставлен.'
}

@receiver(post_save, sender=Order)
def send_new_order_email(sender: Type[Order], instance: Order, **kwargs):
    if instance.dt.date() == timezone.now().date() and instance.status in STATUS_MESSAGES:
        from_email = settings.EMAIL_HOST_USER
        msg = STATUS_MESSAGES[instance.status]
        subject = f'Заказ {instance.status.capitalize()}'
        send_mail(subject, msg, from_email, [instance.user.email], fail_silently=False)