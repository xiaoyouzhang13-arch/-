import requests
from django.conf import settings


def call_deepseek_api(prompt, max_tokens=1000, temperature=0.7):
    """
    调用DeepSeek API生成内容
    
    Args:
        prompt: 提示词
        max_tokens: 最大生成token数
        temperature: 生成温度
    
    Returns:
        生成的内容字符串
    """
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {settings.DEEPSEEK_API_KEY}'
    }
    
    payload = {
        'model': 'deepseek-chat',
        'messages': [
            {
                'role': 'system',
                'content': '你是一个专业的社区助手，擅长回答关于博客平台的问题，以及生成有趣的话题引导用户讨论。'
            },
            {
                'role': 'user',
                'content': prompt
            }
        ],
        'max_tokens': max_tokens,
        'temperature': temperature
    }
    
    try:
        response = requests.post(
            settings.DEEPSEEK_API_URL,
            headers=headers,
            json=payload,
            timeout=30,
            proxies={'http': None, 'https': None}
        )
        
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"DeepSeek API调用失败: {e}")
        return "抱歉，我暂时无法回答这个问题，请稍后再试。"


def generate_ai_response(query):
    """
    生成AI对用户问题的回答
    
    Args:
        query: 用户的问题
    
    Returns:
        AI生成的回答
    """
    prompt = f"请回答以下关于博客平台的问题，回答要专业、友好、简洁：\n\n问题：{query}\n\n回答："
    return call_deepseek_api(prompt)


def generate_topic():
    """
    生成互动话题
    
    Returns:
        生成的话题标题和内容
    """
    prompt = "请为Django博客社区生成一个有趣的互动话题，话题要与Django、博客开发、社区建设相关，能够带动用户讨论。请先给出话题标题，然后提供话题内容，内容要具体、有启发性。"
    response = call_deepseek_api(prompt)
    
    # 解析生成的内容，提取标题和内容
    lines = response.split('\n')
    title = ""
    content = ""
    
    for line in lines:
        line = line.strip()
        if line.startswith('标题：') or line.startswith('Topic:'):
            title = line.split('：')[1].strip() if '：' in line else line.split(':')[1].strip()
        elif line.startswith('内容：') or line.startswith('Content:'):
            content = line.split('：')[1].strip() if '：' in line else line.split(':')[1].strip()
        elif title and not content:
            content += line + '\n'
    
    if not title:
        title = "关于Django博客的讨论"
    if not content:
        content = "分享你使用Django开发博客的经验和技巧。"
    
    return title, content
