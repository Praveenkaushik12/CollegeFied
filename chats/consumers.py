from channels.generic.websocket import AsyncWebsocketConsumer
from django.apps import apps
from channels.db import database_sync_to_async
import json
from django.contrib.auth.models import AnonymousUser

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """
        Handles WebSocket connection requests.
        Ensures that only the buyer and seller of a specific product can connect to the chat room.
        """
        # Extract the group_name from the WebSocket URL
        self.group_name = self.scope['url_route']['kwargs']['group_name']
        self.user = self.scope['user']

        # Reject connection if the user is not authenticated
        if isinstance(self.user, AnonymousUser):
            print(f"Unauthenticated user tried to connect to {self.group_name}. Closing connection.")
            await self.close()
            return

        # Fetch the ChatRoom model
        ChatRoom = apps.get_model('chats', 'ChatRoom')

        try:
            # Extract the product_id from the group_name (e.g., "chat_90" -> 90)
            self.product_id = int(self.group_name.split('_')[1])
            
            # Fetch the chat room for the specific product
            self.chat_room = await self.get_chat_room(self.product_id)
        except (ChatRoom.DoesNotExist, IndexError, ValueError) as e:
            print(f"Invalid group_name or chat room does not exist. Error: {e}. Closing connection.")
            await self.close()
            return

        # Ensure the connecting user is either the buyer or seller of the product
        if self.user.id not in [self.chat_room.buyer.id, self.chat_room.seller.id]:
            print(f"User {self.user.id} is not authorized for this chat. Closing connection.")
            await self.close()
            return

        # Join the chat room group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        print(f"User {self.user.username} successfully connected to {self.group_name}.")

    async def disconnect(self, close_code):
        """
        Handles WebSocket disconnections.
        """
        print(f"User {self.user.username} disconnected from {self.group_name}.")
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """
        Handles incoming WebSocket messages.
        """
        # Ensure the user is authenticated before processing the message
        if isinstance(self.user, AnonymousUser):
            print(f"Unauthenticated user tried to send a message. Closing connection.")
            await self.close()
            return

        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Save the message to the database
        await self.save_message(message)

        # Broadcast the message to the chat room group
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': self.user.username,
                'timestamp': str(await self.get_last_message_timestamp())  # Get the timestamp of the saved message
            }
        )

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
        """
        Retrieves the chat room for the specific product.
        """
        ChatRoom = apps.get_model('chats', 'ChatRoom')
        return ChatRoom.objects.select_related('buyer', 'seller').get(product_id=product_id)

    @database_sync_to_async
    def save_message(self, message):
        """
        Saves the message to the database.
        """
        Message = apps.get_model('chats', 'Message')
        Message.objects.create(
            chat_room=self.chat_room,
            sender=self.user,
            content=message
        )

    @database_sync_to_async
    def get_last_message_timestamp(self):
        """
        Retrieves the timestamp of the last message in the chat room.
        """
        Message = apps.get_model('chats', 'Message')
        last_message = Message.objects.filter(chat_room=self.chat_room).last()
        return last_message.timestamp if last_message else None