from channels.generic.websocket import AsyncWebsocketConsumer
from django.apps import apps
from channels.db import database_sync_to_async
import json
from django.contrib.auth.models import AnonymousUser


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = self.scope['url_route']['kwargs']['group_name']
        self.user = self.scope['user']

        # Reject if user is not authenticated
        if isinstance(self.user, AnonymousUser):
            await self.close()
            return

        try:
            self.chat_room_id = int(self.group_name.split('_')[1])
            self.chat_room = await self.get_chat_room(self.chat_room_id)

            # Check is_active flag
            self.read_only = not self.chat_room.is_active

            #print(f"[CHECK] Room is_active: {self.chat_room.is_active}")
            if not self.chat_room.is_active:
                #print(f"[BLOCKED] ChatRoom inactive, closing socket.")
                await self.close()
                return
            
        except (ValueError, IndexError, apps.get_model('chats', 'ChatRoom').DoesNotExist) as e:
            #print(f"Invalid group_name or chat room does not exist. Error: {e}. Closing connection.")
            await self.close()
            return
        

        if self.user.id not in [self.chat_room.buyer.id, self.chat_room.seller.id]:
            print("[REJECTED] Unauthorized user.")
            await self.close()
            return
        
        # Join the chat room group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # Inform frontend of chat status
        await self.send(text_data=json.dumps({
            'type': 'info',
            'read_only': self.read_only,
            'message': 'Chat is inactive. You can read messages but cannot send new ones.' if self.read_only else 'Chat is active.'
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

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
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender': event['sender'],
            'timestamp': event['timestamp']
        }))

    @database_sync_to_async
    def get_chat_room(self, chat_room_id):
        ChatRoom = apps.get_model('chats', 'ChatRoom')
        return ChatRoom.objects.select_related('buyer', 'seller').get(id=chat_room_id)

    @database_sync_to_async
    def save_message(self, message):
        Message = apps.get_model('chats', 'Message')
        return Message.objects.create(
            chat_room=self.chat_room,
            sender=self.user,
            content=message
        )
