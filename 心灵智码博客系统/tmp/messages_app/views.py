from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.http import FileResponse
import os
from django.conf import settings
from django.db import models

from .models import Message, Friendship, Notification
from .forms import MessageForm


@login_required
def send_friend_request(request, user_id):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    receiver = get_object_or_404(User, id=user_id)
    
    # 检查是否已经存在好友请求
    existing_request = Friendship.objects.filter(sender=request.user, receiver=receiver).first()
    if existing_request:
        messages.error(request, '您已经向该用户发送了好友请求！')
        return redirect('user_list')
    
    # 检查是否已经是好友
    existing_friendship = Friendship.objects.filter(
        (models.Q(sender=request.user, receiver=receiver) | models.Q(sender=receiver, receiver=request.user)),
        status='accepted'
    ).first()
    if existing_friendship:
        messages.error(request, '您已经是该用户的好友！')
        return redirect('user_list')
    
    # 创建好友请求
    Friendship.objects.create(sender=request.user, receiver=receiver)
    messages.success(request, '好友请求发送成功！')
    return redirect('user_list')


@login_required
def handle_friend_request(request, request_id, action):
    friendship = get_object_or_404(Friendship, id=request_id, receiver=request.user, status='pending')
    
    if action == 'accept':
        friendship.status = 'accepted'
        friendship.save()
        messages.success(request, '好友请求已接受！')
    elif action == 'reject':
        friendship.status = 'rejected'
        friendship.save()
        messages.success(request, '好友请求已拒绝！')
    
    return redirect('friend_requests')


@login_required
def friend_requests(request):
    received_requests = Friendship.objects.filter(receiver=request.user, status='pending')
    sent_requests = Friendship.objects.filter(sender=request.user, status='pending')
    return render(request, 'messages_app/friend_requests.html', {
        'received_requests': received_requests,
        'sent_requests': sent_requests
    })


@login_required
def friends_list(request):
    # 获取所有已接受的好友关系
    friendships = Friendship.objects.filter(
        ((models.Q(sender=request.user) | models.Q(receiver=request.user))),
        status='accepted'
    )
    
    # 提取好友用户
    friends = []
    for friendship in friendships:
        if friendship.sender == request.user:
            friends.append(friendship.receiver)
        else:
            friends.append(friendship.sender)
    
    return render(request, 'messages_app/friends_list.html', {'friends': friends})


@login_required
def conversation(request, user_id):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    friend = get_object_or_404(User, id=user_id)
    
    # 检查是否是好友
    is_friend = Friendship.objects.filter(
        ((models.Q(sender=request.user, receiver=friend) | models.Q(sender=friend, receiver=request.user))),
        status='accepted'
    ).exists()
    
    if not is_friend:
        messages.error(request, '您只能与好友发送消息！')
        return redirect('friends_list')
    
    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            message.recipient = friend
            message.save()
            return redirect('conversation', user_id=user_id)
    else:
        form = MessageForm()
    
    # 获取与该用户的所有消息
    chat_messages = Message.objects.filter(
        ((models.Q(sender=request.user, recipient=friend) | models.Q(sender=friend, recipient=request.user)))
    ).order_by('created_at')
    
    # 标记收到的消息为已读并处理文件名
    import os
    for msg in chat_messages:
        if msg.recipient == request.user and not msg.is_read:
            msg.is_read = True
            msg.save()
        # 添加文件名属性
        if msg.file:
            msg.file_name = os.path.basename(msg.file.name)
        else:
            msg.file_name = None
    
    # 获取所有好友及其最新消息
    friendships = Friendship.objects.filter(
        ((models.Q(sender=request.user) | models.Q(receiver=request.user))),
        status='accepted'
    )
    
    # 提取好友用户
    friends = []
    for friendship in friendships:
        if friendship.sender == request.user:
            friends.append(friendship.receiver)
        else:
            friends.append(friendship.sender)
    
    # 获取每个好友的最新消息
    friend_messages = []
    for f in friends:
        last_message = Message.objects.filter(
            ((models.Q(sender=request.user, recipient=f) | models.Q(sender=f, recipient=request.user)))
        ).order_by('-created_at').first()
        if last_message:
            unread_count = Message.objects.filter(
                sender=f, recipient=request.user, is_read=False
            ).count()
            friend_messages.append({
                'friend': f,
                'last_message': last_message,
                'unread_count': unread_count
            })
    
    # 按最新消息时间排序
    friend_messages.sort(key=lambda x: x['last_message'].created_at, reverse=True)
    
    return render(request, 'messages_app/conversation.html', {
        'friend': friend,
        'form': form,
        'chat_messages': chat_messages,
        'friend_messages': friend_messages
    })


@login_required
def message_center(request):
    # 获取用户的系统通知
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # 标记所有通知为已读
    if request.GET.get('mark_read'):
        notifications.filter(is_read=False).update(is_read=True)
    
    # 统计未读通知数量
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    return render(request, 'messages_app/message_center.html', {
        'notifications': notifications,
        'unread_count': unread_count
    })


@login_required
def download_message_file(request, message_id):
    message = get_object_or_404(Message, id=message_id)
    # 确保用户只能下载自己的消息文件
    if message.recipient != request.user and message.sender != request.user:
        messages.error(request, '您无权下载此文件！')
        return redirect('message_center')
    
    if message.file:
        file_path = os.path.join(settings.MEDIA_ROOT, message.file.name)
        if os.path.exists(file_path):
            return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=os.path.basename(message.file.name))
    
    messages.error(request, '文件不存在！')
    return redirect('message_center')


@login_required
def delete_message(request, message_id):
    message = get_object_or_404(Message, id=message_id)
    # 确保用户只能删除自己的消息
    if message.recipient != request.user and message.sender != request.user:
        messages.error(request, '您无权删除此消息！')
        return redirect('message_center')
    message.delete()
    messages.success(request, '消息已删除！')
    return redirect('message_center')
