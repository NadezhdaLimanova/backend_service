from django.urls import path
from .views import RegisterUser, ConfirmEmail, LoginUser

app_name = 'service_app'

urlpatterns = [
    path('user/register/', RegisterUser.as_view(), name='user_register'),
    path(f'user/register/confirm/<str:token>/', ConfirmEmail.as_view(), name='confirm_email'),
    path('user/login/', LoginUser.as_view(), name='user_login'),
    ]
