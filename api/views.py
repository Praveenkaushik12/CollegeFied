import random
import json
from django.utils.timezone import now 
#from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from api.serializer import (
    UserSerializer,UserLoginSerializer,ProductSerializer,ProductRequestSerializer,
    ProductRequestUpdateSerializer,RatingSerializer,UserChangePasswordSerializer,UserPasswordResetSerializer,SendPasswordResetEmailSerializer
)
from .models import User,UserProfile, Product,ProductImage,ProductRequest,OTP,Rating
from rest_framework import status,generics,permissions
from django.contrib.auth import authenticate
from api.renderers import UserRenderer
from rest_framework_simplejwt.tokens import RefreshToken
#from rest_framework_simplejwt.authentication import JWTAuthentication

from api.serializer import UserProfileSerializer
# from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
#from django.conf import settings
from rest_framework.exceptions import ValidationError,PermissionDenied
from django.db.models import Q
from django.core.mail import send_mail
from rest_framework.decorators import api_view, permission_classes
from django.apps import apps





def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }
    

class UserRegistrationView(APIView):
    def post(self, request, format=None):
        email=request.data.get('email')
        user=User.objects.filter(email=email).first()
        if user:
            if not user.is_email_verified:
                OTP.objects.filter(user=user).delete()
                otp_code = str(random.randint(100000, 999999))
                OTP.objects.update_or_create(user=user, defaults={'otp_code': otp_code, 'created_at': now()})
                
                return Response({"detail": "Email already registered but not verified. A new OTP has been sent."}, status=status.HTTP_200_OK)
            
            return Response({"detail": "Email already registered."}, status=status.HTTP_400_BAD_REQUEST)
        
        else:    
            serializer = UserSerializer(data=request.data)
            
            if serializer.is_valid(raise_exception=True):
                # Save the user first
                user = serializer.save(is_email_verified=False)
                email = user.email  # Get user email
                
                # Generate and send OTP
                otp_code = str(random.randint(100000, 999999))
                OTP.objects.update_or_create(user=user, defaults={'otp_code': otp_code, 'created_at': now()})
                
                send_mail(
                    'Email Verification OTP',
                    f'Your OTP is {otp_code}. It is valid for 5 minutes.',
                    'your_email@gmail.com',
                    [email],
                    fail_silently=False,
                )
                
                return Response({'msg': 'OTP sent to your email. Verify to complete registration.'}, status=status.HTTP_200_OK)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
 
class VerifyOTPView(APIView):
    def post(self, request, format=None):
        username = request.data.get('username')
        email = request.data.get('email')
        otp_code = request.data.get('otp')
        password = request.data.get('password')

        if not email or not otp_code or not password:
            return Response({'error': 'Email, OTP, and password are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # ✅ Fetch the user using email
            user = User.objects.get(email=email)

            # ✅ Now get OTP using user instance
            otp_obj = OTP.objects.get(user=user)

            # ✅ Check OTP validity
            if otp_obj.otp_code == otp_code and (now() - otp_obj.created_at).seconds < 300:
                # Create user if OTP is correct
                user.is_email_verified = True
                user.username = username  # Assign the username
                user.set_password(password)  # Hash the password properly
                user.save()

                otp_obj.delete()  # Remove OTP after successful verification

                token = get_tokens_for_user(user)
                return Response({
                    'user_id': user.id,
                    'token': token,
                    'user': UserSerializer(user).data,
                    'msg': 'Registration Successful'
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({'error': 'Invalid or expired OTP'}, status=status.HTTP_400_BAD_REQUEST)

        except User.DoesNotExist:
            return Response({'error': 'User not found. Please register first.'}, status=status.HTTP_400_BAD_REQUEST)

        except OTP.DoesNotExist:
            return Response({'error': 'OTP not found. Please request a new one.'}, status=status.HTTP_400_BAD_REQUEST)
        
               
class UserLoginView(APIView):
    renderer_classes=[UserRenderer]
    def post(self, request, format=None):
        serializer=UserLoginSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            email=serializer.data.get('email')
            password=serializer.data.get('password')
            user=authenticate(email=email,password=password)
            if user is not None:
                #if not user.is_email_verified:
                 #   return Response({'error': 'Email not verified. Please verify your email to log in.'}, status=status.HTTP_403_FORBIDDEN)

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
    
# class UserProfileCreateAPIView(APIView):
#     permission_classes = [permissions.IsAuthenticated]
#     def post(self, request):
#         serializer = UserProfileSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
       
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
    def get(self, request, format=None):
        try:
            pk=request.data.get('product_id')
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductSerializer(product)
        return Response(serializer.data)
    
    
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
        print("Fetching product request object...")
        request_id=self.request.data.get('request_id')
        product_request = super().get_queryset().select_related('product__seller').get(pk=request_id)

        # Ensure only the product seller can update the request
        if product_request.product.seller != self.request.user:
            print("Permission denied: User is not the seller.")
            raise PermissionDenied("You do not have permission to update this request.")

        print("Product request object fetched successfully.")
        return product_request

    def partial_update(self, request, *args, **kwargs):
        print("PATCH request received.")
        product_request = self.get_object()
        print(f"Updating product request with status: {request.data.get('status')}")

        # Fetch the ChatRoom model
        ChatRoom = apps.get_model('chats', 'ChatRoom')

        # Handle chat room creation or deletion based on status
        new_status = request.data.get('status')
        if new_status == 'accepted':
            print("Product request accepted. Fetching or creating chat room...")
            try:
                chat_room = ChatRoom.objects.get(
                    product=product_request.product,
                    buyer=product_request.buyer,
                    seller=product_request.seller,
                )
                print(f"Chat room found: {chat_room.product.id}")
            except ChatRoom.DoesNotExist:
                print("Chat room does not exist. Creating a new one...")
                chat_room = ChatRoom.objects.create(
                    product=product_request.product,
                    buyer=product_request.buyer,
                    seller=product_request.seller,
                )
                print(f"Chat room created: {chat_room.product.id}")

        elif new_status == 'rejected':
            print("Product request rejected. Deleting chat room if it exists...")
            try:
                chat_room = ChatRoom.objects.get(
                    product=product_request.product,
                    buyer=product_request.buyer,
                    seller=product_request.seller,
                )
                chat_room.delete()
                print(f"Chat room deleted: {chat_room.product.id}")
            except ChatRoom.DoesNotExist:
                print("Chat room does not exist. Nothing to delete.")

        # Call the parent class's partial_update method to handle the update
        response = super().partial_update(request, *args, **kwargs)

        # Add chat_room_id and group_name to the response if the status is accepted
        if new_status == 'accepted':
            response.data['chat_room_id'] = chat_room.product.id
            response.data['group_name'] = f"chat_{chat_room.product.id}"

        print("PATCH request processed successfully.")
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

        # If request was 'accepted' or 'approved', revert product status
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
                Q(category__icontains=query)
            )
            #print("This is done------")
             
            if not products.exists():  # Check if the queryset is empty
                return Response({"message": "No products found matching your search."}, status=status.HTTP_200_OK)
            
            serializer = ProductSerializer(products,many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            # If no query is provided, return all products
            products = Product.objects.all()
            #print("else was running")
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
        context["request"] = self.request 
        return context


class UserReviewsView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    def get(self, request):
        user_id = request.data.get("user_id")  

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



class ProductListExcludeUserAPIView(generics.ListAPIView):
    serializer_class=ProductSerializer
    permission_classes=[permissions.IsAuthenticated]

    def get_queryset(self):
        return Product.objects.exclude(seller=self.request.user).exclude(status="sold")

class UserProductList(generics.ListAPIView):
    serializer_class=ProductSerializer
    permission_classes=[permissions.IsAuthenticated]

    def get_queryset(self):
        return Product.objects.filter(seller=self.request.user)
