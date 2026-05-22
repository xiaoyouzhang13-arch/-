import json
import re
import time
from datetime import date, timedelta
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView
from django.http import JsonResponse
from django.db.models import Count, Sum, Q
from django.db import transaction

from .models import Destination, TripPlan, TripDay, TripDayItem, BudgetItem, TravelNote
from .forms import TripPlanForm, TripDayItemForm, BudgetItemForm, TravelNoteForm, DestinationForm
from .utils import generate_itinerary
from .rag import generate_rag_itinerary, sync_travel_knowledge


def _match_destination(title, city_hint=None):
    """Try to match a place name/city to an existing Destination object."""
    if not title:
        return None

    # Exact match on name
    match = Destination.objects.filter(name__iexact=title).first()
    if match:
        return match

    # Partial match on name (contains)
    match = Destination.objects.filter(name__icontains=title).first()
    if match:
        return match

    # Try the other way: title contains destination name
    for dest in Destination.objects.all():
        if dest.name in title:
            return dest

    # If city hint is provided, try to find a destination in that city
    if city_hint:
        match = Destination.objects.filter(city__icontains=city_hint).first()
        if match:
            return match

    return None


# ============================================================
# 景点视图
# ============================================================

class DestinationListView(ListView):
    model = Destination
    template_name = 'travel/destination_list.html'
    context_object_name = 'destinations'
    paginate_by = 12

    def get_queryset(self):
        qs = Destination.objects.all()
        category = self.request.GET.get('category')
        province = self.request.GET.get('province')
        q = self.request.GET.get('q')

        if category:
            qs = qs.filter(category=category)
        if province:
            qs = qs.filter(province=province)
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(city__icontains=q) | Q(province__icontains=q) |
                Q(description__icontains=q)
            )
        return qs.order_by('-is_featured', '-rating', '-visit_count')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['provinces'] = Destination.objects.values_list('province', flat=True).distinct().order_by('province')
        context['active_category'] = self.request.GET.get('category', '')
        context['active_province'] = self.request.GET.get('province', '')
        context['search_query'] = self.request.GET.get('q', '')
        return context


class DestinationDetailView(DetailView):
    model = Destination
    template_name = 'travel/destination_detail.html'
    context_object_name = 'destination'

    def get_object(self):
        obj = super().get_object()
        obj.visit_count += 1
        obj.save(update_fields=['visit_count'])
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        destination = self.object
        context['related_plans'] = TripPlan.objects.filter(
            destination=destination, is_public=True
        ).order_by('-created_at')[:5]
        context['related_notes'] = TravelNote.objects.filter(
            trip_plan__destination=destination, is_published=True
        ).order_by('-created_at')[:5]
        return context


# ============================================================
# 旅行计划视图
# ============================================================

class TripPlanListView(ListView):
    model = TripPlan
    template_name = 'travel/trip_list.html'
    context_object_name = 'trips'
    paginate_by = 10

    def get_queryset(self):
        tab = self.request.GET.get('tab', 'mine')
        if tab == 'public':
            return TripPlan.objects.filter(is_public=True).order_by('-created_at')
        if self.request.user.is_authenticated:
            return TripPlan.objects.filter(user=self.request.user).order_by('-created_at')
        return TripPlan.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = self.request.GET.get('tab', 'mine')
        return context


class TripPlanDetailView(DetailView):
    model = TripPlan
    template_name = 'travel/trip_detail.html'
    context_object_name = 'trip'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        trip = self.object
        context['days'] = trip.days.all().prefetch_related('items__destination')
        context['budget_items'] = trip.budget_items.all()
        context['budget_total_planned'] = sum(b.planned_amount for b in trip.budget_items.all())
        context['budget_total_actual'] = sum(
            b.actual_amount for b in trip.budget_items.all() if b.actual_amount
        )
        context['has_map_data'] = any(
            item.destination and item.destination.latitude and item.destination.longitude
            for day in context['days'] for item in day.items.all()
        )
        return context


@login_required
def create_trip(request):
    if request.method == 'POST':
        form = TripPlanForm(request.POST)
        if form.is_valid():
            trip = form.save(commit=False)
            trip.user = request.user
            trip.save()

            # 自动创建每日行程
            days_count = trip.days_count
            for i in range(days_count):
                TripDay.objects.create(
                    trip_plan=trip,
                    day_number=i + 1,
                    date=trip.start_date + timedelta(days=i)
                )

            # 自动创建默认预算分类
            default_categories = ['transport', 'accommodation', 'dining', 'tickets', 'shopping', 'other']
            for cat in default_categories:
                BudgetItem.objects.create(trip_plan=trip, category=cat, planned_amount=0)

            messages.success(request, '旅行计划创建成功！')
            return redirect('trip_detail', slug=trip.slug)
        else:
            messages.error(request, '请检查表单中的错误并重新提交。')
    else:
        form = TripPlanForm()

    destinations = Destination.objects.all().order_by('name')
    return render(request, 'travel/trip_form.html', {
        'form': form,
        'destinations': destinations,
        'is_create': True,
    })


@login_required
def create_trip_from_ai(request):
    """从 AI 生成的行程数据创建完整的旅行计划"""
    if request.method != 'POST':
        return redirect('create_trip')

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': '无效的JSON数据'}, status=400)

    try:
        title = data.get('title', '').strip()
        slug_base = data.get('slug', '').strip()
        budget = data.get('budget', '3000')
        preferences = data.get('preferences', '')
        destination_id = data.get('destination_id')
        start_date_str = data.get('start_date', '')
        end_date_str = data.get('end_date', '')
        ai_days = data.get('days', [])

        if not title or not slug_base:
            return JsonResponse({'error': '标题和URL标识不能为空'}, status=400)
        if not start_date_str or not end_date_str:
            return JsonResponse({'error': '日期不能为空'}, status=400)

        try:
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
        except (ValueError, TypeError):
            return JsonResponse({'error': '日期格式不正确'}, status=400)

        # Ensure unique slug
        slug = slug_base
        counter = 1
        while TripPlan.objects.filter(slug=slug).exists():
            slug = f'{slug_base}-{counter}'
            counter += 1

        destination = None
        if destination_id:
            try:
                destination = Destination.objects.get(id=destination_id)
            except Destination.DoesNotExist:
                pass

        trip = TripPlan.objects.create(
            user=request.user,
            title=title,
            slug=slug,
            destination=destination,
            budget_total=budget,
            preferences=preferences,
            start_date=start_date,
            end_date=end_date,
            is_public=False,
        )

        # Create default budget categories
        default_categories = ['transport', 'accommodation', 'dining', 'tickets', 'shopping', 'other']
        for cat in default_categories:
            BudgetItem.objects.create(trip_plan=trip, category=cat, planned_amount=0)

        # Create trip days and items from AI data
        for i, day_data in enumerate(ai_days):
            day_num = int(day_data.get('day', i + 1))
            trip_day = TripDay.objects.create(
                trip_plan=trip,
                day_number=day_num,
                date=trip.start_date + timedelta(days=day_num - 1)
            )

            items = day_data.get('items', [])
            city_hint = trip.destination.city if trip.destination else title
            for order, item in enumerate(items):
                item_title = item.get('title', '活动')
                matched_dest = _match_destination(item_title, city_hint)
                TripDayItem.objects.create(
                    trip_day=trip_day,
                    destination=matched_dest,
                    title=item_title,
                    description=item.get('description', ''),
                    start_time=item.get('start_time') or None,
                    end_time=item.get('end_time') or None,
                    transportation=item.get('transportation', 'walk'),
                    order=order + 1,
                    notes=item.get('notes', ''),
                )

        messages.success(request, 'AI 旅行计划创建成功！')
        return JsonResponse({'success': True, 'redirect': reverse('trip_detail', kwargs={'slug': trip.slug})})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'服务器错误: {str(e)}'}, status=500)


@login_required
def trip_tips_view(request, slug):
    """AJAX: 获取住宿/餐饮/交通建议"""
    trip = get_object_or_404(TripPlan, slug=slug)
    dest_name = trip.destination.name if trip.destination else trip.title

    from .rag import generate_travel_tips
    tips = generate_travel_tips(dest_name, trip.days_count, str(trip.budget_total))

    if not tips:
        return JsonResponse({'error': '生成失败'}, status=500)

    # Convert markdown-ish text to HTML paragraphs
    tips_html = '<p>' + tips.replace('\n\n', '</p><p>').replace('\n', '<br>') + '</p>'
    return JsonResponse({'tips_html': tips_html})


@login_required
def toggle_public(request, slug):
    """切换旅行计划的公开/私有状态"""
    trip = get_object_or_404(TripPlan, slug=slug)
    if not (request.user.is_superuser or trip.user == request.user):
        messages.error(request, '您没有权限！')
        return redirect('trip_detail', slug=slug)

    if request.method == 'POST':
        trip.is_public = not trip.is_public
        trip.save(update_fields=['is_public'])
        if trip.is_public:
            messages.success(request, '已公开为模板，其他人可以查看和克隆！')
        else:
            messages.success(request, '已取消公开。')

    return redirect('trip_detail', slug=slug)


@login_required
def update_trip(request, slug):
    trip = get_object_or_404(TripPlan, slug=slug)
    if not (request.user.is_superuser or trip.user == request.user):
        messages.error(request, '您没有权限编辑此计划！')
        return redirect('trip_detail', slug=slug)

    if request.method == 'POST':
        form = TripPlanForm(request.POST, instance=trip)
        if form.is_valid():
            form.save()
            messages.success(request, '旅行计划更新成功！')
            return redirect('trip_detail', slug=trip.slug)
        else:
            messages.error(request, '请检查表单中的错误并重新提交。')
    else:
        form = TripPlanForm(instance=trip)

    destinations = Destination.objects.all().order_by('name')
    return render(request, 'travel/trip_form.html', {
        'form': form,
        'destinations': destinations,
        'is_create': False,
        'trip': trip,
    })


@login_required
def delete_trip(request, slug):
    trip = get_object_or_404(TripPlan, slug=slug)
    if not (request.user.is_superuser or trip.user == request.user):
        messages.error(request, '您没有权限删除此计划！')
        return redirect('trip_detail', slug=slug)

    if request.method == 'POST':
        trip.delete()
        messages.success(request, '旅行计划已删除！')
        return redirect('trip_list')

    return render(request, 'travel/trip_confirm_delete.html', {'trip': trip})


# ============================================================
# 行程项目管理
# ============================================================

@login_required
def add_day_item(request, trip_slug, day_id):
    trip = get_object_or_404(TripPlan, slug=trip_slug)
    if not (request.user.is_superuser or trip.user == request.user):
        messages.error(request, '您没有权限！')
        return redirect('trip_detail', slug=trip_slug)

    day = get_object_or_404(TripDay, id=day_id, trip_plan=trip)

    if request.method == 'POST':
        form = TripDayItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.trip_day = day
            item.order = day.items.count() + 1
            item.save()
            messages.success(request, '行程项目添加成功！')
            return redirect('trip_detail', slug=trip_slug)
    else:
        form = TripDayItemForm()

    return render(request, 'travel/trip_day_item_form.html', {
        'form': form, 'trip': trip, 'day': day,
    })


@login_required
def delete_day_item(request, item_id):
    item = get_object_or_404(TripDayItem, id=item_id)
    trip = item.trip_day.trip_plan
    if not (request.user.is_superuser or trip.user == request.user):
        messages.error(request, '您没有权限！')
        return redirect('trip_detail', slug=trip.slug)

    if request.method == 'POST':
        item.delete()
        messages.success(request, '行程项目已删除！')
    return redirect('trip_detail', slug=trip.slug)


# ============================================================
# AI 行程生成
# ============================================================

@login_required
def generate_itinerary_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': '仅支持POST请求'}, status=400)

    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'error': '仅支持AJAX请求'}, status=400)

    try:
        data = json.loads(request.body)
        destination_name = data.get('destination', '')
        days = int(data.get('days', 3))
        budget = data.get('budget', '3000')
        preferences = data.get('preferences', '经典景点,美食')

        if not destination_name:
            return JsonResponse({'error': '请输入目的地'}, status=400)

        # Try RAG first, fall back to plain generation
        result = generate_rag_itinerary(destination_name, days, budget, preferences)
        if result is None:
            result = generate_itinerary(destination_name, days, budget, preferences)

        if result is None:
            return JsonResponse({'error': 'AI行程生成失败，请稍后重试'}, status=500)

        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': f'生成失败: {str(e)}'}, status=500)


@login_required
def generate_itinerary_page(request):
    """AI 智能规划页面：GET 显示表单，POST 调用 AI 并展示结果"""
    result = None
    error = None
    form_data = {}

    if request.method == 'POST':
        destination_name = request.POST.get('destination', '').strip()
        days_str = request.POST.get('days', '3')
        budget = request.POST.get('budget', '3000')
        preferences = request.POST.get('preferences', '经典景点,美食')

        form_data = {
            'destination': destination_name,
            'days': days_str,
            'budget': budget,
            'preferences': preferences,
        }

        if not destination_name:
            error = '请输入目的地'
        else:
            try:
                days = int(days_str)
                result = generate_rag_itinerary(destination_name, days, budget, preferences)
                if result is None:
                    result = generate_itinerary(destination_name, days, budget, preferences)
                if result is None:
                    error = 'AI 行程生成失败，请稍后重试'
            except ValueError:
                error = '天数必须是数字'

    return render(request, 'travel/generate_itinerary.html', {
        'result': result,
        'error': error,
        'form_data': form_data,
    })


# ============================================================
# 多轮对话规划
# ============================================================

@login_required
def chat_plan_page(request):
    """多轮对话式旅行规划页面"""
    return render(request, 'travel/chat_plan.html')


@login_required
def chat_plan_message(request):
    """处理对话消息，调用 RAG + AI 回复"""
    if request.method != 'POST' or request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'error': '无效的请求'}, status=400)

    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        history = data.get('history', [])
    except json.JSONDecodeError:
        return JsonResponse({'error': '无效的JSON'}, status=400)

    if not user_message:
        return JsonResponse({'error': '消息不能为空'}, status=400)

    # RAG: search for relevant travel knowledge
    from .rag import search_travel_knowledge
    knowledge_results = search_travel_knowledge(user_message, top_k=5)
    knowledge_parts = []
    for r in knowledge_results:
        if r['similarity'] > 0.3:
            knowledge_parts.append(r['content'])
    knowledge_context = '\n'.join(knowledge_parts[:3]) if knowledge_parts else '暂无相关知识库信息。'

    # Build conversation history prompt
    history_text = ''
    for h in history[-6:]:  # Keep last 6 messages for context
        role = '用户' if h['role'] == 'user' else '助手'
        # Truncate long messages
        content = h['content'][:500]
        history_text += f'{role}：{content}\n'

    # Build system prompt
    system_prompt = f"""你是一个专业的旅游规划助手，正在和用户进行对话，帮助规划旅行行程。

【旅游知识库参考信息】：
{knowledge_context}

【对话历史】：
{history_text}

请根据用户的最新消息，给出有帮助的回复。要求：
1. 语气友好、专业，像真正的旅行顾问
2. 如果用户提供了目的地/天数/预算等信息，可以开始提供具体的行程建议
3. 如果信息不完整，可以引导用户补充（目的地、天数、预算、偏好等）
4. 回复简洁，每次聚焦1-2个要点
5. 可以适当推荐知识库中的景点
6. 使用简单的HTML格式（<p>分段，<ul><li>列表）让回复更易读"""

    try:
        from .utils import call_deepseek_api
        messages_payload = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_message}
        ]
        ai_response = call_deepseek_api(
            prompt=system_prompt + '\n\n用户：' + user_message,
            max_tokens=800,
            temperature=0.7
        )

        if not ai_response:
            return JsonResponse({'error': 'AI 回复失败'}, status=500)

        # Format simple markdown to HTML
        reply_html = ai_response.replace('\n\n', '</p><p>').replace('\n', '<br>')
        reply_html = '<p>' + reply_html + '</p>'
        # Fix double paragraphs
        reply_html = reply_html.replace('</p><p></p><p>', '</p><p>')

        return JsonResponse({
            'reply': reply_html,
            'reply_text': ai_response,
        })

    except Exception as e:
        return JsonResponse({'error': f'AI 调用失败: {str(e)}'}, status=500)


@login_required
def chat_plan_finalize(request):
    """从对话记录生成完整行程并创建 TripPlan"""
    if request.method != 'POST':
        return JsonResponse({'error': '无效的请求'}, status=400)

    try:
        data = json.loads(request.body)
        history = data.get('history', [])
    except json.JSONDecodeError:
        return JsonResponse({'error': '无效的JSON'}, status=400)

    if not history:
        return JsonResponse({'error': '对话记录为空'}, status=400)

    # Build full conversation text for analysis
    conversation_text = ''
    for h in history:
        role = '用户' if h['role'] == 'user' else '助手'
        conversation_text += f'{role}：{h["content"]}\n'

    # Call AI to extract trip info and generate itinerary
    prompt = f"""基于以下对话记录，提取旅行信息并生成详细的旅行计划：

【对话记录】：
{conversation_text}

请：
1. 首先从对话中提取：目的地、天数、预算、偏好
2. 如果没有明确提到的信息，使用合理默认值
3. 按标准格式生成每日行程

输出格式：
DEST: <目的地>
DAYS: <天数>
BUDGET: <预算>
PREF: <偏好>

第1天：
时间：08:00-09:00 | 活动：XXX | 交通：步行 | 备注：XXX
...

请从对话中准确提取，没有的信息填'未指定'。"""

    try:
        from .utils import call_deepseek_api, parse_itinerary_response
        from .rag import search_travel_knowledge

        # Also add RAG context
        user_keywords = ' '.join([h['content'] for h in history if h['role'] == 'user'])
        rag_results = search_travel_knowledge(user_keywords, top_k=5)
        rag_parts = []
        for r in rag_results:
            if r['similarity'] > 0.3:
                rag_parts.append(r['content'])

        if rag_parts:
            prompt = prompt.replace('【对话记录】：', f'【知识库参考】：\n{" ".join(rag_parts[:3])}\n\n【对话记录】：')

        response = call_deepseek_api(prompt, max_tokens=3000)
        if not response:
            return JsonResponse({'error': 'AI 生成失败'}, status=500)

        # Parse extracted info
        dest_match = re.search(r'DEST:\s*(.+)', response)
        days_match = re.search(r'DAYS:\s*(\d+)', response)
        budget_match = re.search(r'BUDGET:\s*(\d+)', response)
        pref_match = re.search(r'PREF:\s*(.+)', response)

        destination_name = dest_match.group(1).strip() if dest_match else '未指定'
        days = int(days_match.group(1)) if days_match else 3
        budget = budget_match.group(1) if budget_match else '3000'
        preferences = pref_match.group(1).strip() if pref_match else '经典景点,美食'

        # Parse itinerary
        result = parse_itinerary_response(response, days)
        if not result:
            return JsonResponse({'error': '行程生成失败'}, status=500)

        # Create trip from AI data
        from datetime import date, timedelta
        title = f'{destination_name}{days}天旅行计划'
        slug_base = 'chat-trip-' + str(int(time.time()))
        start_date = date.today()
        end_date = start_date + timedelta(days=days - 1)

        # Ensure unique slug
        slug = slug_base
        counter = 1
        while TripPlan.objects.filter(slug=slug).exists():
            slug = f'{slug_base}-{counter}'
            counter += 1

        trip = TripPlan.objects.create(
            user=request.user,
            title=title,
            slug=slug,
            budget_total=budget,
            preferences=preferences,
            start_date=start_date,
            end_date=end_date,
            is_public=False,
        )

        # Create default budgets
        for cat in ['transport', 'accommodation', 'dining', 'tickets', 'shopping', 'other']:
            BudgetItem.objects.create(trip_plan=trip, category=cat, planned_amount=0)

        # Create days and items from AI result
        city_hint = destination_name
        for day_data in result['days']:
            day_num = int(day_data['day'])
            trip_day = TripDay.objects.create(
                trip_plan=trip,
                day_number=day_num,
                date=start_date + timedelta(days=day_num - 1)
            )
            for i, item in enumerate(day_data.get('items', [])):
                item_title = item.get('title', '活动')
                matched_dest = _match_destination(item_title, city_hint)
                TripDayItem.objects.create(
                    trip_day=trip_day,
                    destination=matched_dest,
                    title=item_title,
                    description=item.get('description', ''),
                    start_time=item.get('start_time') or None,
                    end_time=item.get('end_time') or None,
                    transportation=item.get('transportation', 'walk'),
                    order=i + 1,
                    notes=item.get('notes', ''),
                )

        messages.success(request, 'AI 旅行计划创建成功！')
        return JsonResponse({'success': True, 'redirect': reverse('trip_detail', kwargs={'slug': trip.slug})})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'生成失败: {str(e)}'}, status=500)
# ============================================================
# 预算管理
# ============================================================

@login_required
def trip_budget_view(request, slug):
    trip = get_object_or_404(TripPlan, slug=slug)
    if not (request.user.is_superuser or trip.user == request.user):
        messages.error(request, '您没有权限！')
        return redirect('trip_detail', slug=slug)

    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        if item_id:
            item = get_object_or_404(BudgetItem, id=item_id, trip_plan=trip)
            form = BudgetItemForm(request.POST, instance=item)
        else:
            form = BudgetItemForm(request.POST)

        if form.is_valid():
            budget_item = form.save(commit=False)
            budget_item.trip_plan = trip
            budget_item.save()
            messages.success(request, '预算已更新！')
            return redirect('trip_budget', slug=slug)

    budget_items = trip.budget_items.all()
    budget_form = BudgetItemForm()

    # 饼图数据
    categories = []
    planned_data = []
    actual_data = []
    for item in budget_items:
        categories.append(item.get_category_display())
        planned_data.append(float(item.planned_amount))
        actual_data.append(float(item.actual_amount) if item.actual_amount else 0)

    return render(request, 'travel/trip_budget.html', {
        'trip': trip,
        'budget_items': budget_items,
        'budget_form': budget_form,
        'chart_categories': json.dumps(categories),
        'chart_planned': json.dumps(planned_data),
        'chart_actual': json.dumps(actual_data),
    })


# ============================================================
# 地图视图
# ============================================================

@login_required
def trip_map_view(request, slug):
    trip = get_object_or_404(TripPlan, slug=slug)
    days = trip.days.all().prefetch_related('items__destination')

    markers = []
    for day in days:
        for item in day.items.all():
            if item.destination and item.destination.latitude and item.destination.longitude:
                markers.append({
                    'day': day.day_number,
                    'title': item.title,
                    'dest_name': item.destination.name,
                    'lat': item.destination.latitude,
                    'lng': item.destination.longitude,
                    'transport': item.get_transportation_display(),
                    'time': f'{item.start_time}-{item.end_time}' if item.start_time else '',
                })

    return render(request, 'travel/trip_map.html', {
        'trip': trip,
        'markers': json.dumps(markers),
        'amap_js_key': getattr(settings, 'AMAP_JS_API_KEY', ''),
    })


# ============================================================
# 模板市场 + 克隆
# ============================================================

def public_trip_templates(request):
    trips = TripPlan.objects.filter(is_public=True).order_by('-created_at')
    return render(request, 'travel/trip_templates.html', {'trips': trips})


@login_required
def clone_trip(request, slug):
    original = get_object_or_404(TripPlan, slug=slug, is_public=True)

    # 克隆计划
    import time
    new_trip = TripPlan.objects.create(
        user=request.user,
        title=f'{original.title}（副本）',
        slug=f'{original.slug}-copy-{request.user.id}-{int(time.time())}',
        destination=original.destination,
        description=original.description,
        start_date=original.start_date,
        end_date=original.end_date,
        budget_total=original.budget_total,
        preferences=original.preferences,
        is_public=False,
    )

    # 克隆行程天数
    for day in original.days.all():
        new_day = TripDay.objects.create(
            trip_plan=new_trip,
            day_number=day.day_number,
            date=day.date,
            notes=day.notes,
        )
        # 克隆行程项目
        for item in day.items.all():
            TripDayItem.objects.create(
                trip_day=new_day,
                destination=item.destination,
                title=item.title,
                description=item.description,
                start_time=item.start_time,
                end_time=item.end_time,
                transportation=item.transportation,
                order=item.order,
                notes=item.notes,
            )

    # 克隆预算
    for budget in original.budget_items.all():
        BudgetItem.objects.create(
            trip_plan=new_trip,
            category=budget.category,
            planned_amount=budget.planned_amount,
            actual_amount=None,
            notes=budget.notes,
        )

    messages.success(request, '行程模板克隆成功！您可以自由编辑此计划。')
    return redirect('trip_detail', slug=new_trip.slug)


# ============================================================
# 游记视图
# ============================================================

class TravelNoteListView(ListView):
    model = TravelNote
    template_name = 'travel/travel_note_list.html'
    context_object_name = 'notes'
    paginate_by = 10

    def get_queryset(self):
        return TravelNote.objects.filter(is_published=True).order_by('-created_at')


class TravelNoteDetailView(DetailView):
    model = TravelNote
    template_name = 'travel/travel_note_detail.html'
    context_object_name = 'note'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        import markdown
        context['rendered_content'] = markdown.markdown(
            self.object.content,
            extensions=['codehilite', 'fenced_code', 'tables', 'footnotes']
        )
        return context


@login_required
def publish_travel_note(request, slug):
    trip = get_object_or_404(TripPlan, slug=slug)
    if not (request.user.is_superuser or trip.user == request.user):
        messages.error(request, '您没有权限！')
        return redirect('trip_detail', slug=slug)

    if request.method == 'POST':
        form = TravelNoteForm(request.POST, request.FILES)
        if form.is_valid():
            note = form.save(commit=False)
            note.user = request.user
            note.trip_plan = trip
            note.is_published = True
            note.save()

            # 同步到博客
            _sync_note_to_blog(note, request.user)

            messages.success(request, '游记发布成功，已同步到博客！')
            return redirect('travel_note_detail', slug=note.slug)
    else:
        # 预填充：用行程信息生成游记初稿
        initial_content = _generate_note_draft(trip)
        initial_slug = f'{trip.slug}-note'
        form = TravelNoteForm(initial={
            'title': f'{trip.title} - 游记',
            'slug': initial_slug,
            'content': initial_content,
            'trip_plan': trip,
        })

    return render(request, 'travel/travel_note_form.html', {
        'form': form, 'trip': trip,
    })


def _generate_note_draft(trip):
    """根据旅行计划生成游记草稿"""
    lines = [f'# {trip.title} 游记\n']
    if trip.destination:
        lines.append(f'目的地：{trip.destination.name}\n')
    lines.append(f'时间：{trip.start_date} 至 {trip.end_date}\n')

    for day in trip.days.all():
        lines.append(f'## 第{day.day_number}天（{day.date}）\n')
        if day.notes:
            lines.append(f'{day.notes}\n')
        for item in day.items.all():
            dest_name = item.destination.name if item.destination else ''
            time_str = f'{item.start_time}-{item.end_time}' if item.start_time else ''
            lines.append(f'- {time_str} **{item.title}** {dest_name}\n')
            if item.description:
                lines.append(f'  {item.description}\n')
        lines.append('')

    return '\n'.join(lines)


def _sync_note_to_blog(note, user):
    """将游记同步发布为博客文章"""
    from blog.models import Post, Category
    travel_category, _ = Category.objects.get_or_create(
        slug='travel',
        defaults={'name': '旅游', 'description': '旅行游记和攻略'}
    )
    Post.objects.create(
        title=note.title,
        slug=note.slug,
        content=note.content,
        excerpt=note.content[:200] if len(note.content) > 200 else note.content,
        author=user,
        category=travel_category,
        featured_image=note.cover_image,
        is_published=True,
    )
