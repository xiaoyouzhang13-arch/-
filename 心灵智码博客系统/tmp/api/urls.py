from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CustomUserViewSet, PostViewSet, CommentViewSet, CategoryViewSet, TagViewSet,
    ForumViewSet, TopicViewSet, ForumPostViewSet,
    DestinationViewSet, TripPlanViewSet, TravelNoteViewSet,
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
router.register(r'destinations', DestinationViewSet)
router.register(r'trips', TripPlanViewSet)
router.register(r'travel-notes', TravelNoteViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
