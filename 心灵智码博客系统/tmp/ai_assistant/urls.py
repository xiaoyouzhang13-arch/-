from django.urls import path
from .views import ai_chat_view, generate_topic_view, get_featured_topics

urlpatterns = [
    path('chat/', ai_chat_view, name='ai_chat'),
    path('generate-topic/', generate_topic_view, name='generate_topic'),
    path('featured-topics/', get_featured_topics, name='get_featured_topics'),
]
