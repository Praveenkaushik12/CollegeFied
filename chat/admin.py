from django.contrib import admin
from .models import (Chat,Message)
# Register your models here.
@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ['product_request','is_active']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display=['chat','sender','content','timestamp']