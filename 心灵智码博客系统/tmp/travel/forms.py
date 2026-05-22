from django import forms
from .models import TripPlan, TripDay, TripDayItem, BudgetItem, TravelNote, Destination


class TripPlanForm(forms.ModelForm):
    class Meta:
        model = TripPlan
        fields = ('title', 'slug', 'destination', 'description', 'start_date', 'end_date',
                  'budget_total', 'preferences', 'is_public')
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class TripDayForm(forms.ModelForm):
    class Meta:
        model = TripDay
        fields = ('day_number', 'date', 'notes')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }


class TripDayItemForm(forms.ModelForm):
    class Meta:
        model = TripDayItem
        fields = ('destination', 'title', 'description', 'start_time', 'end_time',
                  'transportation', 'order', 'notes')
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }


class BudgetItemForm(forms.ModelForm):
    class Meta:
        model = BudgetItem
        fields = ('category', 'planned_amount', 'actual_amount', 'notes')


class TravelNoteForm(forms.ModelForm):
    class Meta:
        model = TravelNote
        fields = ('title', 'slug', 'content', 'cover_image', 'trip_plan')
        widgets = {
            'content': forms.Textarea(attrs={'rows': 15}),
        }


class DestinationForm(forms.ModelForm):
    class Meta:
        model = Destination
        fields = ('name', 'slug', 'city', 'province', 'country', 'category',
                  'description', 'image', 'latitude', 'longitude', 'best_season',
                  'recommended_days', 'ticket_price', 'opening_hours', 'tips', 'is_featured')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'tips': forms.Textarea(attrs={'rows': 3}),
        }
