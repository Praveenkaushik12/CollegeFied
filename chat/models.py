from django.db import models
from django.contrib.auth import get_user_model

class Chat(models.Model):
    product_request = models.OneToOneField('api.ProductRequest', on_delete=models.CASCADE, related_name='chat')
    is_active = models.BooleanField(default=True)  # Indicates if the chat is active\

    def __str__(self):
            return f"Chat for {self.product_request.product.title}"

class Message(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.username}: {self.content}"