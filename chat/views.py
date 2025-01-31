from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework import status,viewsets
from .models import Chat, Message
from api.models import ProductRequest
from .serializers import ChatSerializer, MessageSerializer, CreateMessageSerializer
from django.shortcuts import get_object_or_404

class ChatViewSet(viewsets.ModelViewSet):
    queryset = Chat.objects.all()
    serializer_class = ChatSerializer

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Manually close the chat."""
        chat = self.get_object()
        chat.is_active = False
        chat.save()
        return Response({'status': 'Chat closed successfully'}, status=status.HTTP_200_OK)


# ✅ Message ViewSet - Handles message sending & retrieval
class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()

    def get_serializer_class(self):
        """Use different serializers for reading and creating messages."""
        if self.action == 'create':
            return CreateMessageSerializer  # Custom serializer for message creation
        return MessageSerializer

    def create(self, request, *args, **kwargs):
        """Create a message only if the chat is active."""
        chat_id = kwargs.get('chat_id')
        chat = get_object_or_404(Chat, id=chat_id)

        if not chat.is_active:
            return Response({'error': 'Chat is closed'}, status=status.HTTP_400_BAD_REQUEST)

        request.data['chat'] = chat.id
        request.data['sender'] = request.user.id

        return super().create(request, *args, **kwargs)


class SendMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, product_request_id):
        user = request.user  # Ensure user is authenticated
        content = request.data.get("content")

        # Validate input
        if not content:
            return Response({"error": "Message content is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Find the chat associated with the product request
        chat = Chat.objects.filter(product_request_id=product_request_id, is_active=True).first()

        if not chat:
            return Response({"error": "No active chat exists for this request"}, status=status.HTTP_404_NOT_FOUND)

        # Create and save the message
        message = Message.objects.create(chat=chat, sender=user, content=content)

        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)  

class RetrieveMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, product_request_id):
        """Retrieve all messages for a given chat."""
        # Find the chat associated with the product request
        chat = Chat.objects.filter(product_request_id=product_request_id,is_active=True).first()
        messages = Message.objects.filter(chat=chat).order_by('timestamp')

        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PollNewMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, product_request_id):
        """Fetch messages newer than the last message ID the client has."""
        try:
            chat = Chat.objects.get(product_request_id=product_request_id, is_active=True)  # Use `.get()`
        except Chat.DoesNotExist:
            return Response({"error": "Chat not found"}, status=status.HTTP_404_NOT_FOUND)

        last_message_id = request.query_params.get('last_message_id')
        
        if not last_message_id:
            return Response({"error": "last_message_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        new_messages = Message.objects.filter(chat=chat, id__gt=last_message_id).order_by('timestamp')

        serializer = MessageSerializer(new_messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
