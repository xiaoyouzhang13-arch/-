from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Count, Q

from messages_app.models import Friendship

from .models import Post, Comment, Category, Tag
from .forms import PostForm, CommentForm, CategoryForm, TagForm
from .utils import generate_post_summary, generate_comment_reply, generate_image_from_excerpt, attach_ai_image_to_post


class PostListView(ListView):
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        feed = self.request.GET.get('feed', 'recommend')
        queryset = Post.objects.filter(is_published=True).annotate(
            comment_count=Count(
                'comments',
                filter=Q(comments__is_approved=True, comments__parent__isnull=True),
                distinct=True
            )
        )

        if feed == 'latest':
            return queryset.order_by('-publish_date')

        if feed == 'following':
            if not self.request.user.is_authenticated:
                return queryset.none()
            following_ids = Friendship.objects.filter(
                sender=self.request.user,
                status='accepted'
            ).values_list('receiver_id', flat=True)
            return queryset.filter(author_id__in=following_ids).order_by('-publish_date')

        return queryset.order_by('-comment_count', '-publish_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_feed'] = self.request.GET.get('feed', 'recommend')
        context['categories'] = Category.objects.all()
        context['all_tags'] = Tag.objects.annotate(post_count=Count('posts')).order_by('-post_count')[:15]
        return context


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/post_detail.html'
    context_object_name = 'post'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comments'] = self.object.comments.filter(is_approved=True, parent__isnull=True)
        context['comment_form'] = CommentForm()
        context['comment_count'] = self.object.comments.filter(is_approved=True, parent__isnull=True).count()
        context['related_posts'] = Post.objects.filter(
            is_published=True
        ).filter(
            Q(category=self.object.category) | Q(tags__in=self.object.tags.all())
        ).exclude(
            id=self.object.id
        ).distinct().order_by('-publish_date')[:5]
        return context


@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            ai_image_url = request.POST.get('ai_image_url', '').strip()
            # 确保is_published字段被正确保存
            post.is_published = form.cleaned_data.get('is_published', False)
            # 用户未手动上传图片时，尝试使用AI配图
            if not request.FILES.get('featured_image') and ai_image_url:
                attach_ai_image_to_post(post, ai_image_url)
            post.save()
            # 保存多对多关系（标签）
            form.save_m2m()
            messages.success(request, 'Post created successfully!')
            return redirect('post_detail', slug=post.slug)
    else:
        form = PostForm()
    return render(request, 'blog/post_form.html', {'form': form})


@login_required
def update_post(request, slug):
    post = get_object_or_404(Post, slug=slug)
    if not (request.user.is_superuser or post.author == request.user):
        messages.error(request, 'You can only update your own posts!')
        return redirect('post_detail', slug=slug)
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            ai_image_url = request.POST.get('ai_image_url', '').strip()
            # 确保is_published字段被正确保存
            post = form.save(commit=False)
            post.is_published = form.cleaned_data.get('is_published', False)
            # 用户未手动上传图片时，尝试使用AI配图
            if not request.FILES.get('featured_image') and ai_image_url:
                attach_ai_image_to_post(post, ai_image_url)
            post.save()
            # 保存多对多关系（标签）
            form.save_m2m()
            messages.success(request, 'Post updated successfully!')
            return redirect('post_detail', slug=post.slug)
    else:
        form = PostForm(instance=post)
    return render(request, 'blog/post_form.html', {'form': form})


@login_required
def delete_post(request, slug):
    post = get_object_or_404(Post, slug=slug)
    if not (request.user.is_superuser or post.author == request.user):
        messages.error(request, 'You can only delete your own posts!')
        return redirect('post_detail', slug=slug)
    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Post deleted successfully!')
        return redirect('post_list')
    return render(request, 'blog/post_confirm_delete.html', {'post': post})


@login_required
def add_comment(request, slug):
    post = get_object_or_404(Post, slug=slug)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            messages.success(request, '评论添加成功！')
    return redirect('post_detail', slug=slug)


@login_required
def delete_comment(request, comment_id):
    """删除评论（admin用户可以删除任何评论，普通用户只能删除自己的评论）"""
    comment = get_object_or_404(Comment, id=comment_id)
    post_slug = comment.post.slug
    
    # 检查权限：admin用户或评论作者可以删除评论
    if not (request.user.is_superuser or comment.author == request.user):
        messages.error(request, '您没有权限删除此评论！')
        return redirect('post_detail', slug=post_slug)
    
    if request.method == 'POST':
        comment.delete()
        messages.success(request, '评论删除成功！')
    return redirect('post_detail', slug=post_slug)


@login_required
def create_category(request):
    if not request.user.is_superuser:
        messages.error(request, '您没有权限创建分类！')
        return redirect('category_list')
    
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, '分类创建成功！')
            return redirect('category_detail', slug=category.slug)
    else:
        form = CategoryForm()
    return render(request, 'blog/category_form.html', {'form': form})


@login_required
def update_category(request, slug):
    if not request.user.is_superuser:
        messages.error(request, '您没有权限更新分类！')
        return redirect('category_list')
    
    category = get_object_or_404(Category, slug=slug)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, '分类更新成功！')
            return redirect('category_detail', slug=category.slug)
    else:
        form = CategoryForm(instance=category)
    return render(request, 'blog/category_form.html', {'form': form, 'category': category})


@login_required
def create_tag(request):
    if not request.user.is_superuser:
        messages.error(request, '您没有权限创建标签！')
        return redirect('tag_list')
    
    if request.method == 'POST':
        form = TagForm(request.POST)
        if form.is_valid():
            tag = form.save()
            messages.success(request, '标签创建成功！')
            return redirect('tag_detail', slug=tag.slug)
    else:
        form = TagForm()
    return render(request, 'blog/tag_form.html', {'form': form})


@login_required
def update_tag(request, slug):
    if not request.user.is_superuser:
        messages.error(request, '您没有权限更新标签！')
        return redirect('tag_list')
    
    tag = get_object_or_404(Tag, slug=slug)
    if request.method == 'POST':
        form = TagForm(request.POST, instance=tag)
        if form.is_valid():
            form.save()
            messages.success(request, '标签更新成功！')
            return redirect('tag_detail', slug=tag.slug)
    else:
        form = TagForm(instance=tag)
    return render(request, 'blog/tag_form.html', {'form': form, 'tag': tag})


def search_posts(request):
    query = request.GET.get('q')
    if query:
        posts = Post.objects.filter(
            is_published=True,
            title__icontains=query
        ) | Post.objects.filter(
            is_published=True,
            content__icontains=query
        ) | Post.objects.filter(
            is_published=True,
            tags__name__icontains=query
        )
        posts = posts.distinct()
    else:
        posts = Post.objects.none()
    return render(request, 'blog/search_results.html', {'posts': posts, 'query': query})


@login_required
def my_posts(request):
    """显示当前登录用户的博客文章"""
    posts = Post.objects.filter(author=request.user).order_by('-publish_date')
    return render(request, 'blog/my_posts.html', {'posts': posts})


class CategoryListView(ListView):
    model = Category
    template_name = 'blog/category_list.html'
    context_object_name = 'categories'


class CategoryDetailView(DetailView):
    model = Category
    template_name = 'blog/category_detail.html'
    context_object_name = 'category'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['posts'] = self.object.posts.filter(is_published=True).order_by('-publish_date')
        return context


class TagListView(ListView):
    model = Tag
    template_name = 'blog/tag_list.html'
    context_object_name = 'tags'


class TagDetailView(DetailView):
    model = Tag
    template_name = 'blog/tag_detail.html'
    context_object_name = 'tag'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['posts'] = self.object.posts.filter(is_published=True).order_by('-publish_date')
        return context


@login_required
def generate_summary_view(request):
    """
    生成博客文章摘要的AJAX视图
    """
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        content = request.POST.get('content', '')
        if content:
            summary = generate_post_summary(content)
            return JsonResponse({'summary': summary})
        return JsonResponse({'error': '内容不能为空'}, status=400)
    return JsonResponse({'error': '无效的请求'}, status=400)


@login_required
def generate_reply_view(request):
    """
    生成评论回复的AJAX视图
    """
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        comment = request.POST.get('comment', '')
        post_id = request.POST.get('post_id', '')
        
        if comment and post_id:
            try:
                post = Post.objects.get(id=post_id)
                reply = generate_comment_reply(comment, post.content)
                return JsonResponse({'reply': reply})
            except Post.DoesNotExist:
                return JsonResponse({'error': '文章不存在'}, status=404)
        return JsonResponse({'error': '评论内容和文章ID不能为空'}, status=400)
    return JsonResponse({'error': '无效的请求'}, status=400)


@login_required
def generate_image_view(request):
    """
    根据摘要生成博客配图的AJAX视图
    """
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        excerpt = request.POST.get('excerpt', '')
        if not excerpt:
            return JsonResponse({'error': '摘要不能为空'}, status=400)
        try:
            result = generate_image_from_excerpt(excerpt)
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({'error': f'生成图片失败: {e}'}, status=500)
    return JsonResponse({'error': '无效的请求'}, status=400)
