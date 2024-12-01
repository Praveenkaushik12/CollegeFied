from django.contrib import admin
from .models import (
    User,
    UserProfile,
    Product,
    SaleHistory,
    PurchaseHistory,
    Reviews,
)

# Register your models here.
@admin.register(User)
class UserModelAdmin(admin.ModelAdmin):
    list_display = ['id', 'email', 'name', 'is_active','is_admin','is_staff']
    
@admin.register(UserProfile)
class UserProfileModelAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'name','address','college_year', 'gender', 'image']
    
@admin.register(Product)
class ProductModelAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'description', 'price', 'seller', 'status', 'upload_date','resourceImg']

@admin.register(SaleHistory)
class SaleHistoryModelAdmin(admin.ModelAdmin):
    list_display = ['id', 'seller', 'product','buyer','price','sale_date']

@admin.register(PurchaseHistory)
class PurchaseHistoryModelAdmin(admin.ModelAdmin):
    list_display = ['id', 'buyer', 'product', 'seller', 'price', 'purchase_date']
    
@admin.register(Reviews)
class ReviewModelAdmin(admin.ModelAdmin):
    list_display = ['id','reviewer','rating', 'review_text', 'created_at']