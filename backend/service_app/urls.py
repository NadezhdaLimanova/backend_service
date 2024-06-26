from django.urls import path
from .views import (RegisterUser, ConfirmEmail, LoginUser,
                    ModifyUser, ContactView, ShopView,
                    CategoryView, GoodsView, ProductInfoView, ProductInfoFiltersView,
                    BasketView, OrderView, ShopUpdate, ShopStatus, ListOfOrdersView)

app_name = 'service_app'

urlpatterns = [
    path('user/register/', RegisterUser.as_view(), name='user_register'),
    path('user/register/confirm/', ConfirmEmail.as_view(), name='confirm_email'),
    path('user/login/', LoginUser.as_view(), name='user_login'),
    path('user/get/', ModifyUser.as_view(), name='user_get'),
    path('user/modify/', ModifyUser.as_view(), name='user_modify'),
    path('user/contact/', ContactView.as_view(), name='contact'),
    path('shop/', ShopView.as_view(), name='shop'),
    path('categories/', CategoryView.as_view(), name='category'),
    path('goods/', GoodsView.as_view(), name='goods'),
    path('import_products/', ProductInfoView.as_view(), name='product_info'),
    path('filter_products/', ProductInfoFiltersView.as_view(), name='product_info_filters'),
    path('basket/', BasketView.as_view(), name='basket'),
    path('order/', OrderView.as_view(), name='order'),
    path('shop_update/', ShopUpdate.as_view(), name='shop_update'),
    path('shop_status/', ShopStatus.as_view(), name='shop_status'),
    path('list_of_orders/', ListOfOrdersView.as_view(), name='list_of_orders'),
    ]




