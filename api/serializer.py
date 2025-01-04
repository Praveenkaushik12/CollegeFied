from rest_framework import serializers
from django.contrib.auth import get_user_model
User = get_user_model()  # This fetches the User model based on the custom user model in settings
from .models import (
    User,
    UserProfile,
    Product,
    ProductRequest,
    Rating,
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


class UserLoginSerializer(serializers.ModelSerializer):
    email=serializers.EmailField(max_length=255)
    class Meta:
        model=User
        fields=['email','password']
    


class UserProfileSerializer(serializers.ModelSerializer):
    average_rating = serializers.FloatField(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['name', 'address', 'course','college_year', 'gender', 'image','average_rating']
        
    def get_avg_rating(self, obj):
        return obj.average_rating
    

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
    

class ProductSerializer(serializers.ModelSerializer):
    resourceImg = serializers.ImageField(required=False)
    seller = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Product
        fields = ['id', 'title', 'description', 'price', 'seller', 'status', 'upload_date', 'resourceImg']

    def validate(self, attrs):
        seller = self.context['request'].user
        
        # Check if the user has a valid profile
        try:
            profile = seller.userprofile
        except UserProfile.DoesNotExist:
            raise serializers.ValidationError("User profile does not exist")
        
        # Check if required fields in profile are filled
        required_fields = ['name', 'address', 'course', 'college_year', 'gender']
        missing_fields = [field for field in required_fields if not getattr(profile, field)]
        
        if missing_fields:
            raise serializers.ValidationError(
                f"Complete your profile to sell a product. Missing fields: {', '.join(missing_fields)}"
            )
        
        # If 'status' is being updated, ensure that it can only change from 'available' to other values, and not if it's 'sold'
        if 'status' in attrs and attrs['status'] == 'sold':
            if self.instance and self.instance.status == 'sold':
                raise serializers.ValidationError("You cannot change the status of a sold product.")
        
        return attrs
             
        

class ProductRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductRequest
        fields = ['id', 'buyer', 'seller', 'product', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'buyer', 'seller', 'status', 'created_at', 'updated_at']

    def create(self, validated_data):
        request_user = self.context['request'].user
        product = validated_data['product']

        # Ensure the request user is not the seller of the product
        if product.seller == request_user:
            raise serializers.ValidationError("You cannot request your own product.")
        
         # Prevent request if the product is already sold
        if product.status == 'sold':
            raise serializers.ValidationError("This product is already sold.")

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
        allowed_statuses = ['pending', 'accepted', 'rejected', 'approved']

        if value not in allowed_statuses:
            raise serializers.ValidationError(
                f"Invalid status. Allowed values are: {', '.join(allowed_statuses)}."
            )

        # Prevent the seller from setting status back to 'pending'
        if value == 'pending':
            raise serializers.ValidationError("Status cannot be changed back to 'pending'.")

        return value

    def update(self, instance, validated_data):
        new_status = validated_data.get('status')

        # Prevent status from changing directly to 'approved' unless it's currently 'accepted'
        if new_status == 'approved' and instance.status != 'accepted':
            raise serializers.ValidationError("You can only approve a request that has been accepted.")

        # If the current status is 'approved', prevent any further updates
        if instance.status == 'approved':
            raise serializers.ValidationError("You cannot update a request that has already been approved.")

        instance.status = new_status
        instance.save()
        return instance
    
    
class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ['id', 'product', 'seller', 'buyer', 'rating', 'feedback', 'created_at']
        read_only_fields = ['id', 'seller', 'buyer', 'created_at']

    def validate(self, data):
        buyer = self.context['request'].user
        product = data['product']
        seller = data['seller']

        # Check if the product is sold
        if product.status != 'sold':
            raise serializers.ValidationError("You can only rate a seller for sold products.")

        # Check if the ProductRequest is approved for the logged-in user
        product_request = ProductRequest.objects.filter(
            product=product, 
            buyer=buyer, 
            status='approved'
        ).first()

        if not product_request:
            raise serializers.ValidationError("You can only rate the seller for approved requests.")

        return data

    def create(self, validated_data):
        return super().create(validated_data)