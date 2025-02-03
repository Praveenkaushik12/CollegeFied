from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from api.serializer import (
    UserSerializer,UserLoginSerializer,ProductSerializer,ProductRequestSerializer,
    ProductRequestUpdateSerializer,RatingSerializer,UserChangePasswordSerializer,UserPasswordResetSerializer,SendPasswordResetEmailSerializer
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
from rest_framework.exceptions import ValidationError,PermissionDenied
from django.db.models import Q


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
            return Response({
                'user_id':user.id,
                'token': token,
                'user': UserSerializer(user).data,
                'msg':'Registration Successful'
            },status=status.HTTP_201_CREATED)
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
                return Response({
                    'user_id': user.id,
                    'token': token,
                    'msg':'Login success'
                },status=status.HTTP_200_OK)
            else:
                 return Response({'erors':{'non_field_errors':['Email or Password is not Valid']}},status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class UserProfileDetailAPIView(APIView):
    """
    Retrieve or update a user's profile.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get(self, request, user_id):
        user_profile = get_object_or_404(UserProfile, user__id=user_id)
        serializer = UserProfileSerializer(user_profile)
        return Response(serializer.data)

    def put(self, request, user_id):
        user_profile = get_object_or_404(UserProfile, user__id=user_id)
        if request.user != user_profile.user:
            return Response({"detail": "You do not have permission to update this profile."}, status=status.HTTP_403_FORBIDDEN)
        serializer = UserProfileSerializer(user_profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class UserProfileCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        serializer = UserProfileSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
       
class ProductCreateView(generics.CreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Save the product with the logged-in user as the seller
        serializer.save(seller=self.request.user)

class ProductDetailView(APIView):
    def get(self, request, pk, format=None):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductSerializer(product)
        return Response(serializer.data)

class ProductUpdateView(generics.UpdateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_update(self, serializer):
        # Get the product instance being updated
        instance = self.get_object()

        # Check if the seller is the one making the update
        if instance.seller != self.request.user:
            raise ValidationError("You do not have permission to update this product.")
        
        old_status=instance.status 

        # Get the new status being set
        new_status = serializer.validated_data.get('status',instance.status)

        # Handle transition to 'sold'
        if old_status!='sold' and new_status == 'sold':
            # Reject all active requests (pending) for the product
            ProductRequest.objects.filter(product=instance, status='pending').update(status='rejected')
            
            
            # # #close the chat if there
            # Chat=get_model('chat','Chat')
            # chat = Chat.objects.filter(product_request__product=instance)
            # if chat:
            #     chat.is_active = False
            #     chat.save()
            
        # Save the updated product instance
        serializer.save()

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

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
        # product_request = super().get_object()
         
        product_request = super().get_queryset().select_related('product__seller').get(pk=self.kwargs['pk'])
        # print(product_request.product.seller)
        # print(self.request.user)
        
        # Ensure only the product seller can update the request
        if product_request.product.seller != self.request.user:
            raise PermissionDenied("You do not have permission to update this request.")

        return product_request

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


    
class CancelProductRequestView(generics.UpdateAPIView):
    queryset = ProductRequest.objects.all()
    serializer_class = ProductRequestUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        product_request = super().get_object()

        # Ensure the logged-in user is the buyer
        if product_request.buyer != self.request.user:
            raise PermissionDenied("You do not have permission to cancel this request.")
        return product_request


    def patch(self, request, *args, **kwargs):
        product_request = self.get_object()

        # Cancel the request
        product_request.status = 'rejected'
        product_request.save()

        # Revert product status if necessary
        if product_request.status in ['accepted', 'approved']:
            if not ProductRequest.objects.filter(product=product_request.product, status='accepted').exists():
                product_request.product.status = 'available'
                product_request.product.save()

        return Response({"detail": "Request cancelled successfully."}, status=status.HTTP_200_OK)


class ProductSearchAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    """
    Search products by name, description, or category.
    """
    def get(self, request):
        query = request.query_params.get('q', None)  # Get the search query from URL parameters
        if query:
            # Search for products where name, description, or category contains the query
            products = Product.objects.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(category__icontains=query)
            )
            if not products.exists():  # Check if the queryset is empty
                return Response({"message": "No products found matching your search."}, status=status.HTTP_200_OK)
            serializer = ProductSerializer(products, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            # If no query is provided, return all products
            products = Product.objects.all()
            if not products.exists():  # Check if the queryset is empty
                return Response({"message": "No products available."}, status=status.HTTP_200_OK)
            serializer = ProductSerializer(products, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
class CreateRatingView(generics.CreateAPIView):
    serializer_class = RatingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        """Pass request to serializer for validation."""
        context = super().get_serializer_context()
        context["request"] = self.request  # ✅ Pass request to serializer
        return context


class UserChangePasswordView(APIView):
  renderer_classes = [UserRenderer]
  permission_classes = [permissions.IsAuthenticated]
  def post(self, request, format=None):
    serializer = UserChangePasswordSerializer(data=request.data, context={'user':request.user})
    if serializer.is_valid(raise_exception=True):
        return Response({'msg':'Password Changed Successfully'}, status=status.HTTP_200_OK)
    return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

class SendPasswordResetEmailView(APIView):
  renderer_classes = [UserRenderer]
  def post(self, request, format=None):
    serializer = SendPasswordResetEmailSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return Response({'msg':'Password Reset link send. Please check your Email'}, status=status.HTTP_200_OK)
  
class UserPasswordResetView(APIView):
  renderer_classes = [UserRenderer]
  def post(self, request, uid, token, format=None):
    serializer = UserPasswordResetSerializer(data=request.data, context={'uid':uid, 'token':token})
    serializer.is_valid(raise_exception=True)
    return Response({'msg':'Password Reset Successfully'}, status=status.HTTP_200_OK)