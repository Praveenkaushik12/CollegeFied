from django.db import models
from django.contrib.auth import get_user_model

from api.models import Product

User = get_user_model()

class ChatRoom(models.Model):
    buyer = models.ForeignKey(User, related_name='buyer_chatrooms', on_delete=models.CASCADE)
    seller = models.ForeignKey(User, related_name='seller_chatrooms', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)  # Assuming you have a Product model
    is_active = models.BooleanField(default=True) 
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ChatRoom: {self.buyer.username} and {self.seller.username}"

class Message(models.Model):
    chat_room = models.ForeignKey(ChatRoom, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message by {self.sender.username} in {self.chat_room}"