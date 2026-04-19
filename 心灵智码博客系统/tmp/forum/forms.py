from django import forms
from .models import Forum, Topic, Post


class ForumForm(forms.ModelForm):
    class Meta:
        model = Forum
        fields = ('name', 'slug', 'description')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '输入板块名称'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'URL-friendly slug'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': '输入板块描述'}),
        }


class TopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = ('title', 'slug', 'content')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '输入话题标题'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'URL-friendly slug'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 10, 'placeholder': '输入话题内容'}),
        }


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('content',)
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': '输入回复内容'}),
        }
