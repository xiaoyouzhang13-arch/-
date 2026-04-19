from django import forms
from .models import Post, Comment, Category, Tag


class PostForm(forms.ModelForm):
    category = forms.ModelChoiceField(queryset=Category.objects.all(), required=False, empty_label='请选择分类（可选）')
    tags = forms.ModelMultipleChoiceField(queryset=Tag.objects.all(), required=False, widget=forms.SelectMultiple)
    content = forms.CharField(widget=forms.Textarea(attrs={'rows': 10}))
    
    class Meta:
        model = Post
        fields = ('title', 'slug', 'content', 'excerpt', 'category', 'tags', 'featured_image', 'is_published')


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('content', 'parent')


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ('name', 'slug', 'description')


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ('name', 'slug')
