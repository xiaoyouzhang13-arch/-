from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from .models import AIChatMessage, AITopic
from .utils import generate_ai_response, generate_topic


def ai_chat_view(request):
    """AI聊天视图"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        query = request.POST.get('query', '')
        if query:
            # 生成AI回答
            response = generate_ai_response(query)
            
            # 保存聊天记录
            user = request.user if request.user.is_authenticated else None
            AIChatMessage.objects.create(
                user=user,
                user_query=query,
                ai_response=response
            )
            
            return JsonResponse({'response': response})
        return JsonResponse({'error': '问题不能为空'}, status=400)
    return JsonResponse({'error': '无效的请求'}, status=400)


def generate_topic_view(request):
    """生成话题视图"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # 生成新话题
        title, content = generate_topic()
        
        # 保存话题
        topic = AITopic.objects.create(
            title=title,
            content=content,
            is_featured=True
        )
        
        return JsonResponse({'title': title, 'content': content, 'id': topic.id})
    return JsonResponse({'error': '无效的请求'}, status=400)

def get_featured_topics(request):
    """获取精选话题视图"""
    topics = AITopic.objects.filter(is_featured=True).order_by('-generated_at')[:5]
    topics_data = []
    for topic in topics:
        topics_data.append({
            'id': topic.id,
            'title': topic.title,
            'content': topic.content,
            'generated_at': topic.generated_at.strftime('%Y-%m-%d %H:%M')
        })
    return JsonResponse({'topics': topics_data})
