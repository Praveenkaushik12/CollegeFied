from rest_framework import serializers
from .models import ChatRoom, Message

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'sender', 'content', 'timestamp']
    
class ChatRoomSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    buyer_uname = serializers.SerializerMethodField()
    seller_uname = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()
    group_name= serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ['id', 'buyer','buyer_uname', 'seller','seller_uname','product','product_name','group_name','created_at', 'is_active','messages']

    def get_buyer_uname(self,obj):
        return obj.buyer.username if obj.buyer else None

    def get_seller_uname(self,obj):
        return obj.seller.username if obj.seller else None
    
    def get_product_name(self,obj):
        return obj.product.title if obj.product else None

    def get_group_name(self, obj):
        if obj.is_active:
            return f"chat_{obj.product.id}"
        return None

