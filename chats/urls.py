from django.urls import path
from . import views

urlpatterns = [
    # path('chatrooms/', views.ChatRoomListCreateView.as_view(), name='chatroom-list-create'),
    # path('chatrooms/<int:room_id>/messages/', views.MessageListCreateView.as_view(), name='message-list-create'),
    path('<str:group_name>/', views.index),
    path('manage-chat/<int:pk>/', views.ChatRoomManagementView.as_view(), name='manage-chat'),
]