from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.core.paginator import Paginator

from .models import Forum, Topic, Post
from .forms import ForumForm, TopicForm, PostForm


class ForumListView(ListView):
    model = Forum
    template_name = 'forum/forum_list.html'
    context_object_name = 'forums'


class ForumDetailView(DetailView):
    model = Forum
    template_name = 'forum/forum_detail.html'
    context_object_name = 'forum'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        topics = self.object.topics.order_by('-is_sticky', '-updated_at')
        paginator = Paginator(topics, 20)
        page = self.request.GET.get('page')
        page_obj = paginator.get_page(page)
        context['topics'] = page_obj
        context['page_obj'] = page_obj
        return context


class TopicDetailView(DetailView):
    model = Topic
    template_name = 'forum/topic_detail.html'
    context_object_name = 'topic'
    slug_field = 'slug'
    slug_url_kwarg = 'topic_slug'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.views += 1
        self.object.save()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['posts'] = self.object.posts.order_by('created_at')
        context['post_form'] = PostForm()
        context['forum'] = self.object.forum
        return context


@login_required
def create_forum(request):
    if not request.user.is_superuser:
        messages.error(request, '您没有权限创建板块！')
        return redirect('forum_list')
    
    if request.method == 'POST':
        form = ForumForm(request.POST)
        if form.is_valid():
            forum = form.save()
            messages.success(request, '板块创建成功！')
            return redirect('forum_detail', slug=forum.slug)
    else:
        form = ForumForm()
    return render(request, 'forum/forum_form.html', {'form': form})


@login_required
def update_forum(request, slug):
    if not request.user.is_superuser:
        messages.error(request, '您没有权限更新板块！')
        return redirect('forum_list')
    
    forum = get_object_or_404(Forum, slug=slug)
    if request.method == 'POST':
        form = ForumForm(request.POST, instance=forum)
        if form.is_valid():
            form.save()
            messages.success(request, '板块更新成功！')
            return redirect('forum_detail', slug=forum.slug)
    else:
        form = ForumForm(instance=forum)
    return render(request, 'forum/forum_form.html', {'form': form, 'forum': forum})


@login_required
def create_topic(request, forum_slug):
    forum = get_object_or_404(Forum, slug=forum_slug)
    if request.method == 'POST':
        form = TopicForm(request.POST)
        if form.is_valid():
            topic = form.save(commit=False)
            topic.author = request.user
            topic.forum = forum
            topic.save()
            # Create the first post for the topic
            post = Post.objects.create(
                content=topic.content,
                author=request.user,
                topic=topic
            )
            messages.success(request, 'Topic created successfully!')
            return redirect('topic_detail', forum_slug=forum.slug, topic_slug=topic.slug)
    else:
        form = TopicForm(initial={'forum': forum})
    return render(request, 'forum/topic_form.html', {'form': form, 'forum': forum})


@login_required
def create_post(request, forum_slug, topic_slug):
    topic = get_object_or_404(Topic, slug=topic_slug)
    if topic.is_closed:
        messages.error(request, 'This topic is closed. You cannot add posts.')
        return redirect('topic_detail', forum_slug=forum_slug, topic_slug=topic_slug)
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.topic = topic
            post.save()
            topic.updated_at = post.created_at
            topic.save()
            messages.success(request, 'Post added successfully!')
    return redirect('topic_detail', forum_slug=forum_slug, topic_slug=topic_slug)
