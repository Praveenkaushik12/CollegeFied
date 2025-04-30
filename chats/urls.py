from django.urls import path
from .views import ChatRoomListView,MessageListView


urlpatterns = [
    path('message/<int:pk>/',MessageListView.as_view(),name='get-message'),
    path('chats/',ChatRoomListView.as_view(),name='get-active-chats')
]