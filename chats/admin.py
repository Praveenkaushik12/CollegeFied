from django.contrib import admin
from .models import ChatRoom, Message
# Register your models here.
@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    field ='__all__'
    
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    field ='__all__'

    