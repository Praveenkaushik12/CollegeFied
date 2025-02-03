from django.urls import path
from api.views import (
     UserRegistrationView,
     UserLoginView,
     UserProfileDetailAPIView,
     UserProfileCreateAPIView,
     ProductCreateView,
     ProductDetailView,
     ProductUpdateView,SendProductRequestView,
     ProductRequestUpdateView,
     CancelProductRequestView,
     CreateRatingView,
     SendPasswordResetEmailView,
     UserPasswordResetView,
     UserChangePasswordView,
     ProductSearchAPIView,     
)


urlpatterns = [
    path('register/',UserRegistrationView.as_view()),
    path('login/',UserLoginView.as_view()),
    path('changepassword/',UserChangePasswordView.as_view(),name="changepass"),
    path('send-reset-password-email/', SendPasswordResetEmailView.as_view(), name='send-reset-password-email'),
    path('reset-password/<uid>/<token>/', UserPasswordResetView.as_view(), name='reset-password'),


    path('profile/<int:user_id>/', UserProfileDetailAPIView.as_view(), name='user-profile-detail'),
    path('profile/create/', UserProfileCreateAPIView.as_view(), name='user-profile-create'),
    
    path('products/', ProductCreateView.as_view(), name='product-create'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('products/<int:pk>/update', ProductUpdateView.as_view(), name='product-update'),
    path('products/search/', ProductSearchAPIView.as_view(), name='product-search'),
    
    path('product/<int:product_id>/send-request/', SendProductRequestView.as_view(), name='send-product-request'),
    path('product-request/<int:pk>/update/', ProductRequestUpdateView.as_view(), name='update_product_request'),
    path('product-requests/<int:pk>/cancel/', CancelProductRequestView.as_view(), name='cancel-product-request'),
    
    
    path('rate/',CreateRatingView.as_view(),name="rate-seller")
    
]


