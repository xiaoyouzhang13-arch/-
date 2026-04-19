from django.contrib import admin
from .models import Friendship, Message, Notification
from django.contrib.auth import get_user_model

User = get_user_model()


class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('title', 'message', 'user__username')
    
    def send_to_all_users(self, request, queryset):
        """给所有用户发送通知"""
        # 获取所有用户
        users = User.objects.all()
        # 为每个用户创建通知
        for user in users:
            # 复制第一个选中的通知内容
            if queryset.exists():
                notification = queryset.first()
                Notification.objects.create(
                    user=user,
                    title=notification.title,
                    message=notification.message,
                    link=notification.link
                )
        self.message_user(request, f'已成功发送通知给 {users.count()} 个用户')
    
    send_to_all_users.short_description = '发送给所有用户'
    
    actions = [send_to_all_users]


admin.site.register(Friendship)
admin.site.register(Message)
admin.site.register(Notification, NotificationAdmin)
