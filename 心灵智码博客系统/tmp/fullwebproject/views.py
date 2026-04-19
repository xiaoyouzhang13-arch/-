from django.shortcuts import render
from ai_assistant.models import AITopic


def home(request):
    # 获取精选话题
    topics = AITopic.objects.filter(is_featured=True).order_by('-generated_at')[:5]
    return render(request, 'home.html', {'topics': topics})
