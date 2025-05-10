from channels.generic.websocket import AsyncWebsocketConsumer
from django.apps import apps
from channels.db import database_sync_to_async
import json
from django.contrib.auth.models import AnonymousUser


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """
        Handles WebSocket connection requests.
        Allows read-only access if chat room is inactive.
        """
        #print(" USING UPDATED ChatConsumer ")
        self.group_name = self.scope['url_route']['kwargs']['group_name']
        self.user = self.scope['user']

        # Reject if user is not authenticated
        if isinstance(self.user, AnonymousUser):
            print(f"Unauthenticated user tried to connect to {self.group_name}. Closing connection.")
            await self.close()
            return

        try:
            self.product_id = int(self.group_name.split('_')[1])
            self.chat_room = await self.get_chat_room(self.product_id)

            # Check is_active flag
            self.read_only = not self.chat_room.is_active

            #print(f"[CHECK] Room is_active: {self.chat_room.is_active}")
            if not self.chat_room.is_active:
                #print(f"[BLOCKED] ChatRoom inactive, closing socket.")
                await self.close()
                return

            #print(f"ChatRoom ID: {self.chat_room.id}, is_active: {self.chat_room.is_active}")

        except (ValueError, IndexError, apps.get_model('chats', 'ChatRoom').DoesNotExist) as e:
            #print(f"Invalid group_name or chat room does not exist. Error: {e}. Closing connection.")
            await self.close()
            return

        # Ensure user is buyer or seller
        if self.user.id not in [self.chat_room.buyer.id, self.chat_room.seller.id]:
            #print(f"User {self.user.id} is not authorized for this chat. Closing connection.")
            await self.close()
            return

        # Join the chat room group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        #print(f"User {self.user.username} connected to {self.group_name}.")

        # Inform frontend of chat status
        await self.send(text_data=json.dumps({
            'type': 'info',
            'read_only': self.read_only,
            'message': 'Chat is inactive. You can read messages but cannot send new ones.' if self.read_only else 'Chat is active.'
        }))

    async def disconnect(self, close_code):
        """
        Handles WebSocket disconnections.
        """
        #print(f"User {self.user.username} disconnected from {self.group_name}.")
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """
        Handles incoming WebSocket messages.
        Prevents sending if chat is inactive.
        """
        if isinstance(self.user, AnonymousUser):
            #print(f"Unauthenticated user tried to send a message. Closing connection.")
            await self.close()
            return

        if self.read_only:
            #print(f"User {self.user.username} tried to send message to inactive chat {self.group_name}.")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Chat is inactive. You cannot send new messages.'
            }))
            return

        try:
            text_data_json = json.loads(text_data)
            message = text_data_json['message']

            saved_message = await self.save_message(message)

            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender': self.user.username,
                    'timestamp': str(saved_message.timestamp)
                }
            )
        except Exception as e:
            #print(f"Error handling received message: {e}")
            await self.close()

    async def chat_message(self, event):
        """
        Sends chat messages to WebSocket clients.
        """
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender': event['sender'],
            'timestamp': event['timestamp']
        }))

    @database_sync_to_async
    def get_chat_room(self, product_id):
        ChatRoom = apps.get_model('chats', 'ChatRoom')

        # Force fresh DB read
        room = ChatRoom.objects.select_related('buyer', 'seller').get(product_id=product_id)
        from django.db import reset_queries
        reset_queries()  # (optional but helps debug)
        return room


    @database_sync_to_async
    def save_message(self, message):
        """
        Saves the message to the database and returns the message instance.
        """
        Message = apps.get_model('chats', 'Message')
        return Message.objects.create(
            chat_room=self.chat_room,
            sender=self.user,
            content=message
        )
