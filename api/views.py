import random
import json
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
#from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from api.serializer import (
    UserSerializer,UserLoginSerializer,ProductSerializer,ProductRequestSerializer,
    ProductRequestUpdateSerializer,RatingSerializer,
    UserChangePasswordSerializer,
    #UserPasswordResetSerializer,SendPasswordResetEmailSerializer,
    CategorySerializer,ProductRequestHistorySerializer
)
from .models import User,UserProfile, Product,ProductImage,ProductRequest,OTP,Rating,Category
from rest_framework import status,generics,permissions
from django.contrib.auth import authenticate
from api.renderers import UserRenderer
from rest_framework_simplejwt.tokens import RefreshToken
#from rest_framework_simplejwt.authentication import JWTAuthentication

from api.serializer import UserProfileSerializer
# from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
#from django.http import JsonResponse
#from django.views.decorators.csrf import csrf_exempt
#from django.conf import settings
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q
from django.core.mail import send_mail
from rest_framework.decorators import api_view, permission_classes
from django.apps import apps
from rest_framework import viewsets


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class UserRegistrationView(APIView):
    def post(self, request, format=None):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
            if not user.is_email_verified:
                OTP.objects.filter(user=user).delete()
                otp_code = str(random.randint(100000, 999999))
                OTP.objects.create(user=user, otp_code=otp_code, created_at=timezone.now())
                send_mail(
                    'Email Verification OTP',
                    f'Your OTP is {otp_code}. It is valid for 5 minutes.',
                    'your_email@gmail.com',
                    [email],
                    fail_silently=False,
                )
                return Response({"detail": "Email already registered but not verified. A new OTP has been sent."}, status=status.HTTP_200_OK)
            return Response({"detail": "Email already registered and verified."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            serializer = UserSerializer(data=request.data)
            if serializer.is_valid(raise_exception=True):
                user = serializer.save(is_email_verified=False)

                user.username = request.data.get('username') # Get username here
                user.set_password(request.data.get('password')) # Set password here
                user.save() 

                otp_code = str(random.randint(100000, 999999))
                OTP.objects.create(user=user, otp_code=otp_code, created_at=timezone.now())
                send_mail(
                    'Email Verification OTP',
                    f'Your OTP is {otp_code}. It is valid for 5 minutes.',
                    'your_email@gmail.com',
                    [user.email],
                    fail_silently=False,
                )
                return Response({'msg': 'OTP sent to your email. Verify to complete registration.'}, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyOTPView(APIView):
    def post(self, request, format=None):
        email = request.data.get('email')
        otp_code = request.data.get('otp')

        if not email or not otp_code:
            return Response({'error': 'Email and OTP are required'}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, email=email)

        try:
            otp_obj = OTP.objects.get(user=user, otp_code=otp_code)
            if (timezone.now() - otp_obj.created_at) < timedelta(minutes=5):
                user.is_email_verified = True
                user.save()
                otp_obj.delete()
                token = get_tokens_for_user(user)
                return Response({
                    'user_id': user.id,
                    'token': token,
                    'user': UserSerializer(user).data,
                    'msg': 'Email verification successful. You can now log in.'
                }, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Invalid or expired OTP'}, status=status.HTTP_400_BAD_REQUEST)
        except OTP.DoesNotExist:
            return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    renderer_classes=[UserRenderer]
    def post(self, request, format=None):
        serializer=UserLoginSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            email=serializer.data.get('email')
            password=serializer.data.get('password')
            user=authenticate(email=email,password=password)
            if user is not None:
                if not user.is_email_verified:
                   return Response({'error': 'Email not verified. Please verify your email to log in.'}, status=status.HTTP_403_FORBIDDEN)

                token=get_tokens_for_user(user)
                return Response({
                    'user_id': user.id,
                    'token': token,
                    'msg':'Login success'
                },status=status.HTTP_200_OK)
            else:
                 return Response({'erors':{'non_field_errors':['Email or Password is not Valid']}},status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class UserProfileDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get(self, request,pk):
        user_profile = get_object_or_404(UserProfile, user__id=pk)
        serializer = UserProfileSerializer(user_profile)
        return Response(serializer.data)

    def patch(self, request,pk):
        user_profile = get_object_or_404(UserProfile, user__id=pk)
        if request.user != user_profile.user:
            return Response({"detail": "You do not have permission to update this profile."}, status=status.HTTP_403_FORBIDDEN)
        serializer = UserProfileSerializer(user_profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
       
class ProductCreateView(generics.CreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        product = serializer.save(seller=self.request.user)
        images = self.request.FILES.getlist('images')
        if images:
            for image in images:
                ProductImage.objects.create(product=product, image=image)


class ProductDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, format=None):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        # Pass context so the serializer can access request (for has_requested logic)
        serializer = ProductSerializer(product, context={"request": request})

        return Response({
            "product": serializer.data,
        })

    
    
@api_view(['PATCH'])
@permission_classes([permissions.IsAuthenticated])
def update_product(request):
    pk=request.data.get('product_id')
    product = get_object_or_404(Product, pk=pk)
    
    # Check if the requesting user is the seller of the product
    if product.seller != request.user:
        return Response({"detail": "You do not have permission to update this product."}, status=status.HTTP_403_FORBIDDEN)
    
    old_status = product.status
    serializer = ProductSerializer(product, data=request.data, partial=True, context={'request': request})
    
    if serializer.is_valid():
        new_status = serializer.validated_data.get('status', product.status)
        
        if old_status != 'sold' and new_status == 'sold':
        
            ProductRequest.objects.filter(product=product, status__in=['pending','accepted']).update(status='rejected')
            

            product_requests = ProductRequest.objects.filter(
                product=product, 
                status='approved'
            )

            # Close active chats related to these product requests
            if product_requests.exists():
                ChatRoom = apps.get_model('chats', 'ChatRoom')
                active_chats = ChatRoom.objects.filter(
                    product__in=product_requests.values_list('product', flat=True),
                    is_active=True
                )

                if active_chats.exists():
                    active_chats.update(is_active=False)
                    
        product = serializer.save()
        
        # Handle product images
        images = request.FILES.getlist('images')
        if images:
            product.images.all().delete()
            for image in images:
                ProductImage.objects.create(product=product, image=image)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_product(request):
    pk=request.data.get('product_id')
    product = get_object_or_404(Product, pk=pk)
    
    if product.seller!= request.user:
        return Response({"detail": "You do not have permission to delete this product."}, status=status.HTTP_403_FORBIDDEN)
    
    product.delete()
    return Response({"detail": "Product deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


class SendProductRequestView(generics.CreateAPIView):
    serializer_class = ProductRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        product_id = request.data.get('product')
        product = get_object_or_404(Product, id=product_id)

        # Check if the logged-in user is the seller
        if product.seller == request.user:
            return Response(
                {"detail": "You cannot request your own product."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Prevent request if the product is already sold
        if product.status =='sold':
            return Response(
                {"detail": "You cannot request a sold product."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if a pending request already exists
        if ProductRequest.objects.filter(buyer=request.user, product=product, status='pending').exists():
            return Response(
                {"detail": "You have already sent a request for this product."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate user profile completeness
        try:
            profile = request.user.userprofile
            required_fields = ['name', 'address', 'course', 'college_year', 'gender']
            missing_fields = [field for field in required_fields if not getattr(profile, field)]
            if missing_fields:
                return Response(
                    {"detail": f"Complete your profile to send a product request. Missing fields: {', '.join(missing_fields)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except UserProfile.DoesNotExist:
            return Response(
                {"detail": "User profile does not exist. Please complete your profile."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create the product request
        product_request = ProductRequest.objects.create(
            buyer=request.user,
            product=product,
            seller=product.seller,
            status='pending'
        )

        return Response(
            ProductRequestSerializer(product_request).data,
            status=status.HTTP_201_CREATED
        )


class ProductRequestUpdateView(generics.UpdateAPIView):
    queryset = ProductRequest.objects.all()
    serializer_class = ProductRequestUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        request_id = self.request.data.get('request_id')
        product_request=super().get_queryset().select_related('product__seller').get(pk=request_id)

        if product_request.seller != self.request.user:
            raise PermissionDenied("You do not have permission to update this request.")
        
        return product_request
    
    def partial_update(self, request, *args, **kwargs):
        response = super().partial_update(request, *args, **kwargs)

        full_serializer = ProductRequestSerializer(self.get_object(), context={'request': request})
        response.data = full_serializer.data
        return response


            
class CancelProductRequestView(generics.UpdateAPIView):
    queryset = ProductRequest.objects.all()
    serializer_class = ProductRequestUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        request_id = self.request.data.get('request_id')
        product_request = super().get_queryset().select_related('product__seller').get(pk=request_id)

        # Ensure the logged-in user is the buyer
        if product_request.buyer != self.request.user:
            raise PermissionDenied("You do not have permission to cancel this request.")
        
        return product_request


    def patch(self, request, *args, **kwargs):
        product_request = self.get_object()

        # Store original status before updating
        original_status = product_request.status

        # Cancel request
        product_request.status = 'rejected'
        product_request.save()

        # If request was 'accepted' or 'approved', revert product status only when no other request accepted for that product.
        if original_status in ['accepted', 'approved']:
            if not ProductRequest.objects.filter(product=product_request.product, status='accepted').exists():
                product_request.product.status = 'available'
                product_request.product.save()

        return Response({"detail": "Request cancelled successfully."}, status=status.HTTP_200_OK)

class ProductSearchAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    """
    Search products by title, description.
    """
    def get(self, request):
        query = request.query_params.get('q', None)  # Get the search query from URL parameters
        if query:
            # Search for products where name, description, or category contains the query
            products = Product.objects.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(category__name__icontains=query)
            )
            #print("This is done------")
             
            if not products.exists():  # Check if the queryset is empty
                return Response({"message": "No products found matching your search."}, status=status.HTTP_200_OK)
            
            serializer = ProductSerializer(products,many=True,context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            # If no query is provided, return all products
            products = Product.objects.all()
            #print("else was running")
            if not products.exists():  # Check if the queryset is empty
                return Response({"message": "No products available."}, status=status.HTTP_200_OK)
            serializer = ProductSerializer(products, many=True,context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        
class CreateRatingView(generics.CreateAPIView):
    serializer_class = RatingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        """Pass request to serializer for validation."""
        context = super().get_serializer_context()
        context["request"] = self.request 
        return context


class UserReviewsView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    def get(self,request,pk):
        user_id = User.objects.get(pk=pk).id

        if not user_id:
            return Response({"error": "User ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, id=user_id)  # Fetch the user or return 404
        reviews = Rating.objects.filter(seller=user).select_related('buyer', 'product')
        
        if not reviews.exists():
            return Response({"error": "No reviews found for this user"}, status=status.HTTP_200_OK)

        review_list = [
            {
                "buyer": review.buyer.username,
                "product": review.product.title,
                "rating": float(review.rating),
                "review": review.review,
                "created_at": review.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for review in reviews
        ]

        return Response({"reviews": review_list}, status=status.HTTP_200_OK)
    

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):  # Read only for listing categories
    queryset = Category.objects.all()
    serializer_class = CategorySerializer



#-------temporary---------
class AddCategory(APIView):
    #permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#------------------------------

class FilteredProductListView(APIView):
    permission_classes=[permissions.IsAuthenticated]

    def get(self, request, format=None):
        category_slug = request.query_params.get('category')

        if not category_slug:
            return Response({"detail": "Category slug is required."}, status=status.HTTP_400_BAD_REQUEST)

        products = Product.objects.filter(category__slug=category_slug)

        if request.user.is_authenticated:
            products = products.exclude(seller=request.user).exclude(status='sold')   

        serializer = ProductSerializer(products,many=True,context={'request':request})
        return Response(serializer.data)

#------------------------------------------
class BuyingHistoryView(generics.ListAPIView):
    serializer_class=ProductRequestHistorySerializer
    permission_classes=[permissions.IsAuthenticated]

    def get_queryset(self):
        return ProductRequest.objects.filter(
            buyer=self.request.user,
            status='approved'
        ).select_related('product','buyer','seller').prefetch_related('product__images')

class SellingHistoryView(generics.ListAPIView):
    serializer_class=ProductRequestHistorySerializer
    permission_classes=[permissions.IsAuthenticated]

    def get_queryset(self):
        return ProductRequest.objects.filter(
            seller=self.request.user,
            product__status='sold'
        ).select_related('product','buyer','seller').prefetch_related('product__images')
#-------------------------------------

class RequestsMadeView(generics.ListAPIView):
    serializer_class=ProductRequestSerializer
    permission_classes=[permissions.IsAuthenticated]

    def get_queryset(self):
        return ProductRequest.objects.filter(buyer=self.request.user).order_by('-created_at')

class RequestsReceivedView(generics.ListAPIView):
    serializer_class=ProductRequestSerializer
    permission_classes=[permissions.IsAuthenticated]

    def get_queryset(self):
        return ProductRequest.objects.filter(seller=self.request.user).order_by('-created_at')

#------------------------------------------

class ProductListExcludeUserAPIView(generics.ListAPIView):
    serializer_class=ProductSerializer
    permission_classes=[permissions.IsAuthenticated]

    def get_queryset(self):
        return Product.objects.exclude(seller=self.request.user).exclude(status="sold")
        
    def get_serializer_context(self):
        context=super().get_serializer_context()
        context.update({"request":self.request})
        return context

class UserProductList(generics.ListAPIView):
    serializer_class=ProductSerializer
    permission_classes=[permissions.IsAuthenticated]

    def get_queryset(self):
        return Product.objects.filter(seller=self.request.user)

#-------------change password (validation still leeft)---------------------
class UserChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, format=None):
        if not request.user:
            return Response({'error': 'User is not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        serializer = UserChangePasswordSerializer(data=request.data, context={'user': request.user})
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response({'msg': 'Password Changed Successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class SendPasswordResetEmailView(APIView):
    def post(self,request,format=None):
        email=request.data.get('email')
        try:
            user=User.objects.get(email=email)
            if user.is_email_verified:
                OTP.objects.filter(user=user).delete()
                otp_code=str(random.randint(100000,999999))
                OTP.objects.create(user=user,otp_code=otp_code,created_at=timezone.now())
                send_mail(
                    'Reset Password OTP',
                    f'Your OTP is {otp_code}.It is valid for 5 minutes.',
                    'your_email@gmail.com',
                    [email],
                    fail_silently=False,
                )
                return Response({"detail":"OTP has been sent."},status=status.HTTP_200_OK)
            return Response({"detail":"Email is not registered or verified."},status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"detail":"Email is not registered."},status=status.HTTP_404_NOT_FOUND)

class VerifyCreatePasswordView(APIView):
    def post(self, request, format=None):
        email = request.data.get('email')
        otp_code = request.data.get('otp')
        password=request.data.get('password')
        password1=request.data.get('password2')


        if not all([email, otp_code, password, password1]):
            return Response({'error': 'All fields are required.'}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, email=email)

        try:
            otp_obj = OTP.objects.get(user=user, otp_code=otp_code)
            if (timezone.now() - otp_obj.created_at) < timedelta(minutes=5):
                user.is_email_verified = True

                # 1. Check if passwords match
                if password != password1:
                    return JsonResponse({'error': "Passwords does not match"}, status=400)
                

                user.set_password(password)
                user.save()

                otp_obj.delete()

                token = get_tokens_for_user(user)
                return Response({
                    'user_id': user.id,
                    'token': token,
                    'user': UserSerializer(user).data,
                    'msg': 'Email verification successful. You can now log in.'
                }, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Invalid or expired OTP'}, status=status.HTTP_400_BAD_REQUEST)
        except OTP.DoesNotExist:
            return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)