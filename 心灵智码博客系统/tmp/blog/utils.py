import requests
from django.conf import settings
from django.core.files.base import ContentFile
from urllib.parse import quote
import uuid


def call_deepseek_api(prompt, max_tokens=500, temperature=0.7):
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
                'content': '你是一个专业的博客助手，擅长生成博客文章摘要和评论回复。'
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
        return ""


def generate_post_summary(content, max_length=200):
    """
    生成博客文章摘要
    
    Args:
        content: 文章内容
        max_length: 摘要最大长度
    
    Returns:
        生成的摘要
    """
    prompt = f"请为以下博客文章生成一个简洁的摘要，长度控制在{max_length}字左右：\n\n{content[:1000]}..."
    summary = call_deepseek_api(prompt)
    
    # 确保摘要长度不超过限制
    if len(summary) > max_length:
        summary = summary[:max_length].rsplit('，', 1)[0] + '...'
    
    return summary


def generate_comment_reply(comment, post_content):
    """
    生成评论回复
    
    Args:
        comment: 评论内容
        post_content: 文章内容
    
    Returns:
        生成的回复内容
    """
    prompt = f"针对以下博客文章的评论，生成一个友好、专业的回复：\n\n文章内容：{post_content[:500]}...\n\n评论：{comment}\n\n回复："
    return call_deepseek_api(prompt)


def generate_image_from_excerpt(excerpt):
    """
    根据摘要生成图片URL（使用公开图像生成接口）

    Args:
        excerpt: 文章摘要

    Returns:
        dict: {'image_url': str, 'prompt': str}
    """
    if not excerpt or not excerpt.strip():
        raise ValueError("摘要不能为空")

    prompt = (
        "请根据以下博客摘要生成一张有助于理解内容的写实插图，"
        "画面清晰、构图简洁、无文字水印："
        f"{excerpt.strip()[:300]}"
    )
    image_url = f"https://image.pollinations.ai/prompt/{quote(prompt)}?width=1024&height=576&nologo=true"
    return {"image_url": image_url, "prompt": prompt}


def attach_ai_image_to_post(post, image_url):
    """
    下载AI生成图片并保存到Post.featured_image
    """
    if not image_url:
        return False

    try:
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"下载AI图片失败: {e}")
        return False

    filename = f"ai_{post.slug}_{uuid.uuid4().hex[:8]}.jpg"
    post.featured_image.save(filename, ContentFile(response.content), save=False)
    return True
