from rest_framework import generics,permissions
from .models import ChatRoom, Message
from .serializers import ChatRoomSerializer, MessageSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import PermissionDenied
from api.models import ProductRequest
from django.shortcuts import render


class ChatRoomListView(generics.ListAPIView):
    queryset = ChatRoom.objects.all()
    serializer_class = ChatRoomSerializer

class MessageListView(generics.ListAPIView):
    serializer_class = MessageSerializer

    def get_queryset(self):
        pk = self.kwargs.get('pk')
        user=self.request.user

        try:
            chat_room=ChatRoom.objects.select_related('buyer','seller').get(id=pk)
        except:
            raise PermissionDenied("chat room does not exits")
        
        if user!=chat_room.buyer and user!=chat_room.seller:
            raise PermissionError("You do not have permission to view these messages.")
        

        # print(f"Fetching messages for chat_room_id={pk}")


        return Message.objects.filter(chat_room=chat_room).order_by('timestamp')


