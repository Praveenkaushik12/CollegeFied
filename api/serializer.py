from rest_framework import serializers
from django.contrib.auth import get_user_model
User = get_user_model()  # This fetches the User model based on the custom user model in settings
from .models import (
    User,
    UserProfile,
    Product,
    SaleHistory,
    PurchaseHistory,
    Reviews,
)

class UserSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(style={'input_type': 'password'}, write_only=True)

    class Meta:
        model = User  # Ensure that the serializer is linked to the correct User model
        fields = ['email', 'name', 'password', 'password2']
        extra_kwargs = {
            'password': {'write_only': True}
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
    user = UserSerializer()

    class Meta:
        model = UserProfile
        fields = ['user', 'name', 'address', 'college_year', 'gender', 'image']

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = UserSerializer.create(UserSerializer(), validated_data=user_data)
        user_profile = UserProfile.objects.create(user=user, **validated_data)
        return user_profile

class ProductSerializer(serializers.ModelSerializer):
    seller=UserSerializer(read_only=True)
    class Meta:
        model=Product
        fields= ['id', 'title', 'description', 'price', 'seller', 'status', 'upload_date', 'resourceImg']
    
class SaleHistorySerializer(serializers.ModelSerializer):
    seller = UserSerializer(read_only=True)
    buyer = UserSerializer(read_only=True)
    product = ProductSerializer(read_only=True)

    class Meta:
        model = SaleHistory
        fields = ['id', 'seller', 'product', 'buyer', 'price', 'sale_date']
        
        
class PurchaseHistorySerializer(serializers.ModelSerializer):
    buyer = UserSerializer(read_only=True)
    seller = UserSerializer(read_only=True)
    product = ProductSerializer(read_only=True)

    class Meta:
        model = PurchaseHistory
        fields = ['id', 'buyer', 'product', 'seller', 'price', 'purchase_date']
        

class ReviewSerializer(serializers.ModelSerializer):
    reviewer = UserSerializer(read_only=True)

    class Meta:
        model = Reviews
        fields = ['id', 'reviewer', 'rating', 'review_text', 'created_at']

        

    