from django.db import models
from django.conf import settings
from django.utils import timezone


class Destination(models.Model):
    CATEGORY_CHOICES = (
        ('nature', '自然风光'),
        ('culture', '人文历史'),
        ('food', '美食购物'),
        ('leisure', '休闲娱乐'),
        ('outdoor', '户外探险'),
    )

    name = models.CharField(max_length=200, verbose_name='景点名称')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='URL标识')
    city = models.CharField(max_length=100, verbose_name='所在城市')
    province = models.CharField(max_length=100, verbose_name='所在省份')
    country = models.CharField(max_length=100, default='中国', verbose_name='国家')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, verbose_name='分类')
    description = models.TextField(verbose_name='景点介绍')
    image = models.ImageField(upload_to='destination_images/', blank=True, null=True, verbose_name='景点图片')
    latitude = models.FloatField(null=True, blank=True, verbose_name='纬度')
    longitude = models.FloatField(null=True, blank=True, verbose_name='经度')
    rating = models.FloatField(default=0, verbose_name='评分')
    visit_count = models.PositiveIntegerField(default=0, verbose_name='访问热度')
    best_season = models.CharField(max_length=100, default='全年', verbose_name='最佳季节')
    recommended_days = models.PositiveIntegerField(default=1, verbose_name='建议游玩天数')
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='门票价格')
    opening_hours = models.CharField(max_length=200, default='全天', verbose_name='开放时间')
    tips = models.TextField(blank=True, verbose_name='旅游贴士')
    is_featured = models.BooleanField(default=False, verbose_name='精选推荐')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    def __str__(self):
        return f'{self.name}（{self.city}）'


class TripPlan(models.Model):
    STATUS_CHOICES = (
        ('planning', '规划中'),
        ('ongoing', '进行中'),
        ('completed', '已完成'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='trip_plans',
        verbose_name='创建者'
    )
    title = models.CharField(max_length=200, verbose_name='计划标题')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='URL标识')
    destination = models.ForeignKey(
        Destination,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trip_plans',
        verbose_name='主要目的地'
    )
    description = models.TextField(blank=True, verbose_name='计划描述')
    start_date = models.DateField(verbose_name='开始日期')
    end_date = models.DateField(verbose_name='结束日期')
    budget_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='总预算')
    preferences = models.CharField(max_length=200, blank=True, verbose_name='旅行偏好')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning', verbose_name='状态')
    is_public = models.BooleanField(default=False, verbose_name='公开分享')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    def __str__(self):
        return self.title

    @property
    def days_count(self):
        return (self.end_date - self.start_date).days + 1


class TripDay(models.Model):
    trip_plan = models.ForeignKey(
        TripPlan,
        on_delete=models.CASCADE,
        related_name='days',
        verbose_name='所属计划'
    )
    day_number = models.PositiveIntegerField(verbose_name='第几天')
    date = models.DateField(verbose_name='日期')
    notes = models.TextField(blank=True, verbose_name='当天备注')

    class Meta:
        ordering = ['day_number']

    def __str__(self):
        return f'{self.trip_plan.title} - 第{self.day_number}天'


class TripDayItem(models.Model):
    TRANSPORT_CHOICES = (
        ('walk', '步行'),
        ('bus', '公交'),
        ('metro', '地铁'),
        ('taxi', '打车'),
        ('drive', '自驾'),
    )

    trip_day = models.ForeignKey(
        TripDay,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='所属天'
    )
    destination = models.ForeignKey(
        Destination,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='day_items',
        verbose_name='关联景点'
    )
    title = models.CharField(max_length=200, verbose_name='活动名称')
    description = models.TextField(blank=True, verbose_name='活动描述')
    start_time = models.TimeField(null=True, blank=True, verbose_name='开始时间')
    end_time = models.TimeField(null=True, blank=True, verbose_name='结束时间')
    transportation = models.CharField(max_length=50, choices=TRANSPORT_CHOICES, default='walk', verbose_name='交通方式')
    order = models.PositiveIntegerField(default=0, verbose_name='排序')
    notes = models.TextField(blank=True, verbose_name='备注')

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.title}（{self.trip_day}）'


class BudgetItem(models.Model):
    CATEGORY_CHOICES = (
        ('transport', '交通'),
        ('accommodation', '住宿'),
        ('dining', '餐饮'),
        ('tickets', '门票'),
        ('shopping', '购物'),
        ('other', '其他'),
    )

    trip_plan = models.ForeignKey(
        TripPlan,
        on_delete=models.CASCADE,
        related_name='budget_items',
        verbose_name='所属计划'
    )
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, verbose_name='类别')
    planned_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='预算金额')
    actual_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='实际花费')
    notes = models.CharField(max_length=200, blank=True, verbose_name='备注')

    def __str__(self):
        return f'{self.get_category_display()} - 预算: {self.planned_amount}'


class TravelNote(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='travel_notes',
        verbose_name='作者'
    )
    trip_plan = models.ForeignKey(
        TripPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notes',
        verbose_name='关联旅行计划'
    )
    title = models.CharField(max_length=200, verbose_name='标题')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='URL标识')
    content = models.TextField(verbose_name='正文')
    cover_image = models.ImageField(upload_to='travel_notes/', blank=True, null=True, verbose_name='封面图')
    is_published = models.BooleanField(default=False, verbose_name='已发布')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    def __str__(self):
        return self.title
