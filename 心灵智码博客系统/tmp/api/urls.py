from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CustomUserViewSet, PostViewSet, CommentViewSet, CategoryViewSet, TagViewSet,
    ForumViewSet, TopicViewSet, ForumPostViewSet
)

router = DefaultRouter()
router.register(r'users', CustomUserViewSet)
router.register(r'posts', PostViewSet)
router.register(r'comments', CommentViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'tags', TagViewSet)
router.register(r'forums', ForumViewSet)
router.register(r'topics', TopicViewSet)
router.register(r'forum-posts', ForumPostViewSet, basename='forum-post')

urlpatterns = [
    path('', include(router.urls)),
]
