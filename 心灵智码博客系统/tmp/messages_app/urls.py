from django.urls import path
from . import views

urlpatterns = [
    # 好友功能
    path('friend/request/send/<user_id>/', views.send_friend_request, name='send_friend_request'),
    path('friend/requests/', views.friend_requests, name='friend_requests'),
    path('friend/request/handle/<request_id>/<action>/', views.handle_friend_request, name='handle_friend_request'),
    path('friends/', views.friends_list, name='friends_list'),
    
    # 消息中心
    path('', views.message_center, name='message_center'),
    path('conversation/<user_id>/', views.conversation, name='conversation'),
    path('delete/<message_id>/', views.delete_message, name='delete_message'),
    path('download/<message_id>/', views.download_message_file, name='download_message_file'),
]
