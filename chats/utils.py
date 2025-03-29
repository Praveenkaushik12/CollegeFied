from django.apps import apps

def create_chat_room(product, buyer, seller):
    """
    Creates a chat room for the given product, buyer, and seller.
    """
    ChatRoom = apps.get_model('chats', 'ChatRoom')
    chat_room, created = ChatRoom.objects.get_or_create(
        product=product,
        buyer=buyer,
        seller=seller,
    )
    return chat_room

def delete_chat_room(product, buyer, seller):
    """
    Deletes the chat room for the given product, buyer, and seller.
    """
    ChatRoom = apps.get_model('chats', 'ChatRoom')
    try:
        chat_room = ChatRoom.objects.get(
            product=product,
            buyer=buyer,
            seller=seller,
        )
        chat_room.delete()
    except ChatRoom.DoesNotExist:
        pass  # No chat room exists, nothing to delete