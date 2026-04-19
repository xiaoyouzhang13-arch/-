#!/usr/bin/env python
"""清理消息表中的日志格式内容"""
import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fullwebproject.settings')
django.setup()

from messages_app.models import Message

def cleanup_messages():
    """清理消息表中的日志格式内容"""
    # 获取所有消息
    messages = Message.objects.all()
    print(f"找到 {messages.count()} 条消息记录")
    
    # 清理每条消息
    for msg in messages:
        # 检查content是否是日志格式
        if msg.content and 'Message from' in msg.content and 'to' in msg.content and 'at' in msg.content:
            # 清理content字段
            msg.content = f"[系统消息] 来自 {msg.sender.username} 的消息"
            msg.save()
            print(f"清理了消息 ID {msg.id}: {msg.content}")
    
    print("清理完成！")

if __name__ == '__main__':
    cleanup_messages()
