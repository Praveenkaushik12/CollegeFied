from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatViewSet, MessageViewSet, SendMessageView, RetrieveMessagesView, PollNewMessagesView

# ✅ Router for ViewSets
router = DefaultRouter()
router.register(r'chats', ChatViewSet, basename='chat')
router.register(r'messages', MessageViewSet, basename='message')

urlpatterns = [
    path('', include(router.urls)),  # Includes all viewset routes

    # ✅ Custom API endpoints
    path('<int:product_request_id>/send/', SendMessageView.as_view(), name='send_message'),
    path('<int:product_request_id>/messages/', RetrieveMessagesView.as_view(), name='retrieve_messages'),
    path('<int:product_request_id>/poll/', PollNewMessagesView.as_view(), name='poll_messages'),
]
