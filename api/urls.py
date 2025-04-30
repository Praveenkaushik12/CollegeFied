from django.urls import path
from api.views import (
    UserRegistrationView,
    VerifyOTPView,
    UserProfileDetailAPIView,
    ProductCreateView,
    ProductDetailView,
    UserLoginView,
    UserProfileDetailAPIView,
    ProductCreateView,
    ProductDetailView,
    update_product,
    delete_product,
    SendProductRequestView,
    ProductRequestUpdateView,
    CancelProductRequestView,
    CreateRatingView,
    SendPasswordResetEmailView,
    UserPasswordResetView,
    UserChangePasswordView,
    ProductSearchAPIView,   
    UserReviewsView,
    CategoryViewSet,
    FilteredProductListView,BuyingHistoryView, 
    SellingHistoryView,
    RequestsMadeView,
    RequestsReceivedView,
    ProductListExcludeUserAPIView,UserProductList,AddCategory
)
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register(r'category', CategoryViewSet, basename='category')



urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),  # Sends OTP to email
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),  # Verifies OTP and completes registration
    path('login/', UserLoginView.as_view(), name='login'),  # Handles login
    path('changepassword/',UserChangePasswordView.as_view(),name="changepass"),
    path('send-reset-password-email/', SendPasswordResetEmailView.as_view(), name='send-reset-password-email'),
    path('reset-password/<uid>/<token>/', UserPasswordResetView.as_view(), name='reset-password'),


    path('profile/<int:pk>/', UserProfileDetailAPIView.as_view(), name='user-profile-detail'), #GET --done
    
    path('create-product/', ProductCreateView.as_view(), name='product-create'),
    path('product-details/<int:pk>/', ProductDetailView.as_view(), name='product-detail'), #GET
    path('product-update/', update_product, name='product-update'),
    path('product-delete/', delete_product, name='product-delete'),
    
    path('products/search/', ProductSearchAPIView.as_view(), name='product-search'), #GET

    #---------new changes----------
    
    path('history/buying/', BuyingHistoryView.as_view(), name='buying-history'), #GET
    path('history/selling/', SellingHistoryView.as_view(), name='selling-history'), #GET

    path('add-category/',AddCategory.as_view(),name='add-category'),

    #-------------------------------


    path('products/by-category/', FilteredProductListView.as_view(), name='products-by-category'), #GET
    path('requests/made/', RequestsMadeView.as_view(), name='requests-made'), #GET
    path('requests/received/', RequestsReceivedView.as_view(), name='requests-received'), #GET
    path('products/',ProductListExcludeUserAPIView.as_view(),name='all-products'),
    path('myproducts/',UserProductList.as_view(),name='my-products'),


    
    path('product/send-request/', SendProductRequestView.as_view(), name='send-product-request'),
    path('product-request/update/', ProductRequestUpdateView.as_view(), name='update_product_request'),
    
    path('product-request/cancel/', CancelProductRequestView.as_view(), name='cancel-product-request'),
    
    
    path('rate/',CreateRatingView.as_view(),name="rate-seller"),
    path('reviews/',UserReviewsView.as_view(), name='user-reviews'),
    
]


urlpatterns += router.urls
