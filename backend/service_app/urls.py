from django.urls import path
from .views import RegisterUser, ConfirmEmail, LoginUser, ModifyUser, ContactView, ShopView

app_name = 'service_app'

urlpatterns = [
    path('user/register/', RegisterUser.as_view(), name='user_register'),
    path(f'user/register/confirm/', ConfirmEmail.as_view(), name='confirm_email'),
    path('user/login/', LoginUser.as_view(), name='user_login'),
    path('user/get/', ModifyUser.as_view(), name='user_get'),
    path('user/modify/', ModifyUser.as_view(), name='user_modify'),
    path('user/contact/', ContactView.as_view(), name='contact'),
    path('shop/', ShopView.as_view(), name='shop'),
    ]




