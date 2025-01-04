from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from api.serializer import (
    UserSerializer,UserLoginSerializer,ProductSerializer,ProductRequestSerializer,
    ProductRequestUpdateSerializer,RatingSerializer
)
from rest_framework import status,generics,permissions
from django.contrib.auth import authenticate
from api.renderers import UserRenderer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import UserProfile, Product,ProductRequest,Rating
from api.serializer import UserProfileSerializer
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.conf import settings



# Create your views here.

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class UserRegistrationView(APIView):
    renderer_classes=[UserRenderer]
    def post(self, request,format=None):
        serializer=UserSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user=serializer.save()
            token=get_tokens_for_user(user)
            return Response({'token': token, 'user': UserSerializer(user).data,'msg':'Registration Successful'},status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
class UserLoginView(APIView):
    renderer_classes=[UserRenderer]
    def post(self, request, format=None):
        serializer=UserLoginSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            email=serializer.data.get('email')
            password=serializer.data.get('password')
            user=authenticate(email=email,password=password)
            if user is not None:
                token=get_tokens_for_user(user)
                return Response({'token': token,'msg':'Login success'},status=status.HTTP_200_OK)
            else:
                 return Response({'erors':{'non_field_errors':['Email or Password is not Valid']}},status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# @login_required
class UserProfileView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """Retrieve or initialize the user's profile."""
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(user_profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        """Update the user's profile."""
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            serializer = UserProfileSerializer(user_profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found'}, status=status.HTTP_404_NOT_FOUND)

class ProductCreateView(generics.CreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Automatically set the logged-in user as the seller
        serializer.save(seller=self.request.user)
        
class ProductUpdateView(generics.UpdateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_update(self, serializer):
        # Get the product instance being updated
        instance = self.get_object()

        # If the product's status is 'sold', no fields can be updated
        if instance.status == 'sold':
            return Response(
                {"detail": "You cannot update a sold product."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Save the updated product instance
        serializer.save()

class SendProductRequestView(generics.CreateAPIView):
    serializer_class = ProductRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        product_id = kwargs.get('product_id')
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
        product_request = super().get_object()

        # Ensure the logged-in user is the seller of the product
        if product_request.product.seller != self.request.user:
            raise PermissionDenied("You do not have permission to update this request.")

        return product_request

    def patch(self, request, *args, **kwargs):
        product_request = self.get_object()
        serializer = self.get_serializer(product_request, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)

class CreateRatingView(generics.CreateAPIView):
    serializer_class = RatingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        product_id = self.request.data.get('product')
        product = get_object_or_404(Product, id=product_id)
        serializer.save(
            buyer=self.request.user,
            seller=product.seller,
            product=product
        )

class SellerRatingsView(generics.ListAPIView):
    serializer_class = RatingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        seller = get_object_or_404(settings.AUTH_USER_MODEL, id=self.kwargs['seller_id'])
        return Rating.objects.filter(seller=seller)


