from django.contrib import admin
from .models import (
    User,
    UserProfile,
    Category,
    Product,
    ProductImage,
    ProductRequest,
    Rating,
)

# Register your models here.
@admin.register(User)
class UserModelAdmin(admin.ModelAdmin):
    list_display = ['id', 'email','username', 'is_active','is_admin','is_staff']
    
@admin.register(UserProfile)
class UserProfileModelAdmin(admin.ModelAdmin):
    list_display = ['id', 'user','name','address','college_year', 'gender', 'image']
    
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'slug', 'image']

@admin.register(Product)
class ProductModelAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'description', 'price', 'seller','category', 'category_id','status', 'upload_date']
    
@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['id', 'product', 'image']
    
@admin.register(ProductRequest)
class ProductRequestModelAdmin(admin.ModelAdmin):
    field = '__all__'

@admin.register(Rating)
class RatingModelAdmin(admin.ModelAdmin):
    list_display = ['id', 'buyer', 'seller', 'product', 'rating', 'review', 'created_at']
