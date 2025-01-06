from django.urls import path
from api.views import (
     UserRegistrationView,UserLoginView,UserProfileView,ProductCreateView,
     ProductDetailView,
     ProductUpdateView,SendProductRequestView,
     ProductRequestUpdateView,
     CancelProductRequestView,
     CreateRatingView,
     SellerRatingsView
)


urlpatterns = [
    path('register/',UserRegistrationView.as_view()),
    path('login/',UserLoginView.as_view()),
    path('profile/',UserProfileView.as_view()),
    path('products/', ProductCreateView.as_view(), name='product-create'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('products/<int:pk>/update', ProductUpdateView.as_view(), name='product-update'),
    
    path('product/<int:product_id>/send-request/', SendProductRequestView.as_view(), name='send-product-request'),
    path('product-request/<int:pk>/update/', ProductRequestUpdateView.as_view(), name='update_product_request'),
     path('product-requests/<int:pk>/cancel/', CancelProductRequestView.as_view(), name='cancel-product-request'),
    
    
    path('product/rate/', CreateRatingView.as_view(), name='create-rating'),
    path('seller/<int:seller_id>/ratings/', SellerRatingsView.as_view(), name='seller-ratings'),
    
]


