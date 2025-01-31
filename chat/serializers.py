from rest_framework import serializers
from .models import Chat,Message
from api.serializer import UserSerializer

# Chat Serializer
class ChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = ['id', 'product_request', 'is_active']

# Message Serializer
class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)  # Nested serializer for sender details

    class Meta:
        model = Message
        fields = ['id', 'chat', 'sender', 'content', 'timestamp']
        read_only_fields = ['timestamp']  # Timestamp is auto-generated, so it's read-only
        
# Create Message Serializer (for sending messages)
class CreateMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['content']  # Only the content is needed when creating a message