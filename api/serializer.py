from datetime import timedelta
from django.utils.timezone import now
from django.utils.encoding import smart_str, force_bytes, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from api.utils import Util
from rest_framework import serializers
from django.apps import apps
from django.db.models import Avg
# from django.contrib.auth import get_user_model
# User = get_user_model()  # This fetches the User model based on the custom user model in settings

from .models import (
    User,
    UserProfile,
    Product,
    ProductImage,
    ProductRequest,
    Rating,
    OTP
)

class UserSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(style={'input_type': 'password'}, write_only=True)
    
    
    class Meta:
        model = User  # Ensure that the serializer is linked to the correct User model
        fields = ['email', 'username', 'password', 'password2']
        extra_kwargs = {
            'password': {'write_only': True},
            'username': {'required': True}  
        }
    

    def validate(self, attrs):
        password = attrs.get('password')
        password2 = attrs.get('password2')
        if password != password2:
            raise serializers.ValidationError("Password and Confirm Password don't match")
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')  # Remove password2 since it’s not stored in the User model
        return User.objects.create_user(**validated_data)


class OTPSerializer(serializers.ModelSerializer):
    class Meta:
        model = OTP
        fields = ['user', 'otp_code']
        
class UserLoginSerializer(serializers.ModelSerializer):
    email=serializers.EmailField(max_length=255)
    
    class Meta:
        model=User
        fields=['email','password']
    
    
class UserProfileSerializer(serializers.ModelSerializer):
    average_rating = serializers.SerializerMethodField()
    user = serializers.PrimaryKeyRelatedField(read_only=True)  # Prevent user field from being modified

    class Meta:
        model = UserProfile
        fields = ['user', 'name', 'address', 'course', 'college_year', 'gender', 'image', 'average_rating']
        read_only_fields = ['user', 'average_rating']  

    def get_average_rating(self, obj):
        return obj.user.received_ratings.aggregate(avg=Avg('rating'))['avg'] or 0

    
    def create(self, validated_data):
        # Automatically associate the profile with the authenticated user
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['image']

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)  # Make images read-only
    seller_id = serializers.SerializerMethodField()  # Adding seller_id

    class Meta:
        model = Product
        fields = ['id', 'title', 'description', 'price', 'seller_id', 'status', 'upload_date', 'images']
    
    
    def get_seller_id(self, obj):
        return obj.seller.id if obj.seller else None 
    
    def validate(self, attrs):
        seller = self.context['request'].user
        
    
        # Check if the user has a valid profile
        try:
            profile = seller.userprofile
        except UserProfile.DoesNotExist:
            raise serializers.ValidationError("User profile does not exist.")
        
        # Check if required fields in profile are filled
        required_fields = ['name', 'address', 'course', 'college_year', 'gender']
        missing_fields = [field for field in required_fields if not getattr(profile, field, None)]
        
        if missing_fields:
            raise serializers.ValidationError(
                f"Complete your profile to sell a product. Missing fields: {', '.join(missing_fields)}"
            )
           
        # Validate 'status' only if it is being updated
        if 'status' in attrs:
            new_status = attrs['status']
            if self.instance:  # If updating an existing product
                if new_status == 'sold' and self.instance.status == 'sold':
                    raise serializers.ValidationError("You cannot change the status of a sold product.")
                elif new_status!=self.instance.status and new_status != 'sold':
                    raise serializers.ValidationError(
                        "You can only change the product status to 'sold'. Other status updates are automatic."
                    )
        
        return attrs
    
    def update(self, instance, validated_data):
        images = self.context['request'].FILES.getlist('images')

        # Update other fields
        instance = super().update(instance, validated_data)

        if images:
            instance.images.all().delete()  # Remove old images
            for image in images:
                ProductImage.objects.create(product=instance, image=image)

        return instance


class ProductRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductRequest
        fields = ['id', 'buyer', 'seller', 'product', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'buyer', 'seller','status', 'created_at', 'updated_at']

    def create(self, validated_data):
        request_user = self.context['request'].user
        product = validated_data['product']

        # Ensure the request user is not the seller of the product
        if product.seller == request_user:
            raise serializers.ValidationError("You cannot request your own product.")
        
        # Prevent request if the product is already sold or unavailable
        if product.status in ['sold', 'unavailable']:
            raise serializers.ValidationError(f"You cannot send a request for a product that is {product.status}.")
        
        # Prevent duplicate pending requests
        if ProductRequest.objects.filter(buyer=request_user, product=product, status='pending').exists():
            raise serializers.ValidationError("You have already sent a request for this product.")
        
        # Create the product request
        return ProductRequest.objects.create(
            buyer=request_user,
            seller=product.seller,
            product=product,
            status='pending'
        )






class ProductRequestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductRequest
        fields = ['status']

    def validate_status(self, value):
        """
        Validates the status update request based on the user type (buyer/seller).
        """
        instance = self.instance
        request = self.context['request']
        product = instance.product

        # Buyers can only reject the request
        if instance.buyer == request.user:
            if value != 'rejected':
                raise serializers.ValidationError("Buyers can only cancel the request (set status to 'rejected').")

        # Sellers can only update to accepted, approved, or rejected
        elif instance.product.seller == request.user:
            if value not in ['accepted', 'approved', 'rejected']:
                raise serializers.ValidationError("Sellers can only update status to 'accepted', 'approved', or 'rejected'.")

        else:
            raise serializers.ValidationError("You do not have permission to update this request.")

        # Prevent multiple active requests
        if value in ['accepted', 'approved']:
            active_requests = ProductRequest.objects.filter(
                product=product,
                status__in=['accepted', 'approved']
            ).exclude(pk=instance.pk)

            if active_requests.exists():
                raise serializers.ValidationError("There is already an active request for this product.")

        # Prevent status from reverting to 'pending'
        if value == 'pending':
            raise serializers.ValidationError("Status cannot be changed back to 'pending'.")

        return value
    
    
    
 
class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ['id', 'buyer', 'seller', 'product', 'rating', 'review']
        read_only_fields = ['buyer', 'seller']


    def validate(self, data):  
        request = self.context['request']
        buyer = request.user
        product = data['product']  # Comes from validated data
        
        # Ensure the product was actually "sold"
        if product.status != "sold":
            raise serializers.ValidationError("You can only rate a product that has been sold.")

        # Check if the buyer has an "approved" request
        approved_request = ProductRequest.objects.filter(
            buyer=buyer,
            product=product,
            status='approved'
        ).first()  
        
        if not approved_request:
            raise serializers.ValidationError("You can only rate a product you were approved for.")

        #  Ensure rating is within 7 days of sale
        sale_date = product.updated_at  # Assuming `updated_at` is the last modified time
        if (now() - sale_date) > timedelta(days=7):
            raise serializers.ValidationError("You can only rate within 7 days of the product being sold.")

        # Ensure buyer has not already rated this product request
        if Rating.objects.filter(buyer=buyer, product=product).exists():
            raise serializers.ValidationError("You have already rated this product.")

        return data
    
    def validate_rating(self, value):
        if value < 1.0 or value > 5.0:
            raise serializers.ValidationError("Rating must be between 1.0 and 5.0")
        return value
    
    def create(self, validated_data):
        request = self.context['request']
        buyer = request.user
        product = validated_data['product']
        seller = product.seller

        return Rating.objects.create(
            buyer=buyer,
            seller=seller,
            **validated_data
        )
 
 
class UserChangePasswordSerializer(serializers.Serializer):
  password = serializers.CharField(max_length=255, style={'input_type':'password'}, write_only=True)
  password2 = serializers.CharField(max_length=255, style={'input_type':'password'}, write_only=True)
  class Meta:
    fields = ['password', 'password2']

  def validate(self, attrs):
    password = attrs.get('password')
    password2 = attrs.get('password2')
    user = self.context.get('user')
    if password != password2:
      raise serializers.ValidationError("Password and Confirm Password doesn't match")
    user.set_password(password)
    user.save()
    return attrs    

class SendPasswordResetEmailSerializer(serializers.Serializer):
  email = serializers.EmailField(max_length=255)
  class Meta:
    fields = ['email']

  def validate(self, attrs):
    email = attrs.get('email')
    if User.objects.filter(email=email).exists():
      user = User.objects.get(email = email)
      uid = urlsafe_base64_encode(force_bytes(user.id))
      print('Encoded UID', uid)
      token = PasswordResetTokenGenerator().make_token(user)
      print('Password Reset Token', token)
      link = 'http://localhost:3000/api/user/reset/'+uid+'/'+token
      print('Password Reset Link', link)
      # Send EMail
      body = 'Click Following Link to Reset Your Password '+link
      data = {
        'subject':'Reset Your Password',
        'body':body,
        'to_email':user.email
      }
      Util.send_email(data)
      return attrs
    else:
      raise serializers.ValidationError('You are not a Registered User')   
  
  
class UserPasswordResetSerializer(serializers.Serializer):
  password = serializers.CharField(max_length=255, style={'input_type':'password'}, write_only=True)
  password2 = serializers.CharField(max_length=255, style={'input_type':'password'}, write_only=True)
  class Meta:
    fields = ['password', 'password2']

  def validate(self, attrs):
    try:
      password = attrs.get('password')
      password2 = attrs.get('password2')
      uid = self.context.get('uid')
      token = self.context.get('token')
      if password != password2:
        raise serializers.ValidationError("Password and Confirm Password doesn't match")
      id = smart_str(urlsafe_base64_decode(uid))
      user = User.objects.get(id=id)
      if not PasswordResetTokenGenerator().check_token(user, token):
        raise serializers.ValidationError('Token is not Valid or Expired')
      user.set_password(password)
      user.save()
      return attrs
    except DjangoUnicodeDecodeError as identifier:
      PasswordResetTokenGenerator().check_token(user, token)
      raise serializers.ValidationError('Token is not Valid or Expired')