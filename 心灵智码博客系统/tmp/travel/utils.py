import requests
import re
import json
from django.conf import settings


def call_deepseek_api(prompt, max_tokens=2000, temperature=0.7):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {settings.DEEPSEEK_API_KEY}'
    }

    payload = {
        'model': 'deepseek-chat',
        'messages': [
            {
                'role': 'system',
                'content': '你是一个专业的旅游规划师，擅长根据用户的偏好和预算制定详细的旅行计划。请严格按照要求的格式输出行程。'
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
            timeout=60,
            proxies={'http': None, 'https': None}
        )
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"DeepSeek API调用失败: {e}")
        return None


def generate_itinerary(destination_name, days, budget, preferences):
    prompt = f"""你是一个专业的旅游规划师。请根据以下信息生成详细的{days}天旅行行程：

- 目的地：{destination_name}
- 总天数：{days}天
- 总预算：{budget}元
- 旅行偏好：{preferences}

请严格按照以下格式输出每一天的行程（每条一行，不要用markdown标题）：

第1天：
时间：08:00-09:00 | 活动：XXX | 交通：步行 | 备注：XXX
时间：09:00-12:00 | 活动：XXX | 交通：公交 | 备注：XXX
...

第2天：
时间：08:00-09:00 | 活动：XXX | 交通：步行 | 备注：XXX
...

要求：
1. 每天安排3-5个活动
2. 时间要合理衔接
3. 交通方式从以下选择：步行、公交、地铁、打车、自驾
4. 考虑景点开放时间和用餐时间
5. 备注可包含实用信息（如门票价格、注意事项等）
6. 总花费不要超出预算"""
    response = call_deepseek_api(prompt, max_tokens=3000)
    if not response:
        return None
    return parse_itinerary_response(response, days)


def parse_itinerary_response(response, days):
    result = {"days": []}

    # 按"第X天："分割
    day_pattern = re.compile(r'第(\d+)天[：:]')
    day_splits = day_pattern.split(response)

    # 重组：格式为 [前导文本, day_num_1, content_1, day_num_2, content_2, ...]
    current_day = None

    for i in range(1, len(day_splits), 2):
        day_num = int(day_splits[i])
        content = day_splits[i + 1] if i + 1 < len(day_splits) else ""

        items = []
        for line in content.strip().split('\n'):
            line = line.strip()
            if not line or not line.startswith('时间'):
                continue

            item = {}
            parts = [p.strip() for p in line.split('|')]
            for part in parts:
                if '时间' in part:
                    times = part.replace('时间：', '').replace('时间:', '').strip().split('-')
                    if len(times) == 2:
                        item['start_time'] = times[0].strip()
                        item['end_time'] = times[1].strip()
                elif '活动' in part:
                    item['title'] = part.replace('活动：', '').replace('活动:', '').strip()
                elif '交通' in part:
                    transport = part.replace('交通：', '').replace('交通:', '').strip()
                    transport_map = {
                        '步行': 'walk', '公交': 'bus', '地铁': 'metro',
                        '打车': 'taxi', '自驾': 'drive'
                    }
                    item['transportation'] = transport_map.get(transport, 'walk')
                elif '备注' in part:
                    item['notes'] = part.replace('备注：', '').replace('备注:', '').strip()

            if item.get('title'):
                item.setdefault('start_time', '09:00')
                item.setdefault('end_time', '12:00')
                item.setdefault('transportation', 'walk')
                item.setdefault('notes', '')
                items.append(item)

        result['days'].append({
            'day': day_num,
            'items': items
        })

    return result if result['days'] else None
