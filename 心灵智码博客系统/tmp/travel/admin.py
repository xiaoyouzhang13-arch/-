from django.contrib import admin
from .models import Destination, TripPlan, TripDay, TripDayItem, BudgetItem, TravelNote


@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'province', 'category', 'rating', 'is_featured')
    list_filter = ('category', 'province', 'is_featured')
    search_fields = ('name', 'city', 'province', 'description')
    prepopulated_fields = {'slug': ('name',)}


class TripDayItemInline(admin.TabularInline):
    model = TripDayItem
    extra = 0


class TripDayInline(admin.TabularInline):
    model = TripDay
    extra = 0
    show_change_link = True


class BudgetItemInline(admin.TabularInline):
    model = BudgetItem
    extra = 0


@admin.register(TripPlan)
class TripPlanAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'destination', 'start_date', 'end_date', 'status', 'is_public')
    list_filter = ('status', 'is_public')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [TripDayInline, BudgetItemInline]


@admin.register(TripDay)
class TripDayAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'trip_plan', 'day_number', 'date')
    inlines = [TripDayItemInline]


@admin.register(TripDayItem)
class TripDayItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'trip_day', 'start_time', 'end_time', 'transportation', 'order')


@admin.register(BudgetItem)
class BudgetItemAdmin(admin.ModelAdmin):
    list_display = ('trip_plan', 'category', 'planned_amount', 'actual_amount')
    list_filter = ('category',)


@admin.register(TravelNote)
class TravelNoteAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'trip_plan', 'is_published', 'created_at')
    list_filter = ('is_published',)
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
