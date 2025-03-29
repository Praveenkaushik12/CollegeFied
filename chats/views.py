from rest_framework import generics,permissions
from .models import ChatRoom, Message
from .serializers import ChatRoomSerializer, MessageSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import PermissionDenied
from chats.utils import create_chat_room, delete_chat_room
from api.models import ProductRequest
from django.shortcuts import render


class ChatRoomListCreateView(generics.ListCreateAPIView):
    queryset = ChatRoom.objects.all()
    serializer_class = ChatRoomSerializer

class MessageListCreateView(generics.ListCreateAPIView):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer

    def get_queryset(self):
        room_id = self.kwargs['room_id']
        return Message.objects.filter(chat_room_id=room_id)

class ChatRoomManagementView(APIView):
    """
    API endpoint to manage chat rooms based on product request status updates.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Handles enabling or disabling chat rooms based on product request status.
        """
        product_request_id = kwargs.get('pk')
        try:
            product_request = ProductRequest.objects.select_related('product__seller', 'buyer').get(pk=product_request_id)
        except ProductRequest.DoesNotExist:
            return Response({"detail": "Product request not found."}, status=status.HTTP_404_NOT_FOUND)

        # Ensure only the seller can update the chat room
        if product_request.product.seller != request.user:
            raise PermissionDenied("You do not have permission to manage this chat room.")

        new_status = request.data.get('status')

        # if new_status == 'accepted':
        #     # Create a chat room
        #     chat_room = create_chat_room(
        #         product=product_request.product,
        #         buyer=product_request.buyer,
        #         seller=product_request.seller,
        #     )
        #     return Response({"detail": "Chat room enabled.", "group_name": f"chat_{chat_room.id}"}, status=status.HTTP_200_OK)

        # elif new_status == 'rejected':
        #     # Delete the chat room
        #     delete_chat_room(
        #         product=product_request.product,
        #         buyer=product_request.buyer,
        #         seller=product_request.seller,
        #     )
        #     return Response({"detail": "Chat room disabled."}, status=status.HTTP_200_OK)

        return Response({"detail": "No action taken."}, status=status.HTTP_200_OK)
    
    
def index(request,group_name):
    return render(request, 'chats/index.html', {'groupname':group_name})