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
    VerifyCreatePasswordView,
    #UserPasswordResetView,
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
    #------------ User -----------

    path('register/', UserRegistrationView.as_view(), name='register'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'), 
    path('login/', UserLoginView.as_view(), name='login'),
    path('changepassword/',UserChangePasswordView.as_view(),name="changepass"),
    path('send-reset-password-email/', SendPasswordResetEmailView.as_view(), name='send-reset-password-email'),
    path('reset-password/', VerifyCreatePasswordView.as_view(), name='reset-password'),
    path('profile/<int:pk>/', UserProfileDetailAPIView.as_view(), name='user-profile-detail'), 

    #---------------- Related to Products ---------------

    path('products/by-category/', FilteredProductListView.as_view(), name='products-by-category'), 
    path('products/',ProductListExcludeUserAPIView.as_view(),name='all-products'),
    path('myproducts/',UserProductList.as_view(),name='my-products'),

    path('create-product/', ProductCreateView.as_view(), name='product-create'),
    path('product-details/<int:pk>/', ProductDetailView.as_view(), name='product-detail'), 
    path('product-update/', update_product, name='product-update'),
    path('product-delete/', delete_product, name='product-delete'),
    path('products/search/', ProductSearchAPIView.as_view(), name='product-search'), 

    #--------- Buying and Selling History ----------
    
    path('history/buying/', BuyingHistoryView.as_view(), name='buying-history'), 
    path('history/selling/', SellingHistoryView.as_view(), name='selling-history'),
    
    #------------temporary(This will be done by admin)----------

    path('add-category/',AddCategory.as_view(),name='add-category'),

    #-------- Product Request -----------------
    path('product/send-request/', SendProductRequestView.as_view(), name='send-product-request'),
    path('product-request/update/', ProductRequestUpdateView.as_view(), name='update_product_request'),
    path('product-request/cancel/', CancelProductRequestView.as_view(), name='cancel-product-request'),

    path('requests/made/', RequestsMadeView.as_view(), name='requests-made'), 
    path('requests/received/', RequestsReceivedView.as_view(), name='requests-received'),    

    #------------Rating & Review---------
    path('rate/',CreateRatingView.as_view(),name="rate-seller"),
    path('reviews/<int:pk>/',UserReviewsView.as_view(), name='user-reviews'),

    
]


urlpatterns += router.urls
