from django.urls import path
from api.views import (
     UserRegistrationView,UserLoginView,UserProfileView,ProductCreateView,ProductUpdateView,SendProductRequestView,
     ProductRequestUpdateView,
)


urlpatterns = [
    path('register/',UserRegistrationView.as_view()),
    path('login/',UserLoginView.as_view()),
    path('profile/',UserProfileView.as_view()),
    path('products/', ProductCreateView.as_view(), name='product-create'),
    path('products/<int:pk>/', ProductUpdateView.as_view(), name='product-update'),
    
    path('product/<int:product_id>/send-request/', SendProductRequestView.as_view(), name='send-product-request'),
    path('product-request/<int:pk>/update/', ProductRequestUpdateView.as_view(), name='update_product_request'),
    
    
]


