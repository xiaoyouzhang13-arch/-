from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class AIChatMessage(models.Model):
    """AI聊天消息模型"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_chat_messages', null=True, blank=True)
    user_query = models.TextField()
    ai_response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_public = models.BooleanField(default=False)  # 是否公开显示

    def __str__(self):
        return f"Message from {self.user.username if self.user else 'Guest'} at {self.created_at}"


class AITopic(models.Model):
    """AI生成的话题模型"""
    title = models.CharField(max_length=200)
    content = models.TextField()
    generated_at = models.DateTimeField(auto_now_add=True)
    is_featured = models.BooleanField(default=False)  # 是否为精选话题
    view_count = models.IntegerField(default=0)  # 查看次数

    def __str__(self):
        return self.title
