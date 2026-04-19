from django.urls import path
from .views import (
    ForumListView, ForumDetailView, TopicDetailView, create_forum, update_forum, create_topic, create_post
)

urlpatterns = [
    path('', ForumListView.as_view(), name='forum_list'),
    path('create/', create_forum, name='create_forum'),
    path('<slug:slug>/', ForumDetailView.as_view(), name='forum_detail'),
    path('<slug:slug>/update/', update_forum, name='update_forum'),
    path('<slug:forum_slug>/topic/create/', create_topic, name='create_topic'),
    path('<slug:forum_slug>/topic/<slug:topic_slug>/', TopicDetailView.as_view(), name='topic_detail'),
    path('<slug:forum_slug>/topic/<slug:topic_slug>/post/create/', create_post, name='create_post'),
]
