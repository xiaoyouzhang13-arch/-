from django.urls import path
from .views import (
    PostListView, PostDetailView, create_post, update_post, delete_post, add_comment, delete_comment,
    CategoryListView, CategoryDetailView, TagListView, TagDetailView,
    create_category, update_category, create_tag, update_tag, search_posts, my_posts,
    generate_summary_view, generate_reply_view, generate_image_view
)

urlpatterns = [
    path('', PostListView.as_view(), name='post_list'),
    path('my-posts/', my_posts, name='my_posts'),
    path('post/create/', create_post, name='create_post'),
    path('post/<slug:slug>/', PostDetailView.as_view(), name='post_detail'),
    path('post/<slug:slug>/update/', update_post, name='update_post'),
    path('post/<slug:slug>/delete/', delete_post, name='delete_post'),
    path('post/<slug:slug>/comment/', add_comment, name='add_comment'),
    path('comment/<int:comment_id>/delete/', delete_comment, name='delete_comment'),
    path('search/', search_posts, name='search_posts'),
    path('categories/', CategoryListView.as_view(), name='category_list'),
    path('category/create/', create_category, name='create_category'),
    path('category/<str:slug>/', CategoryDetailView.as_view(), name='category_detail'),
    path('category/<str:slug>/update/', update_category, name='update_category'),
    path('tags/', TagListView.as_view(), name='tag_list'),
    path('tag/create/', create_tag, name='create_tag'),
    path('tag/<str:slug>/', TagDetailView.as_view(), name='tag_detail'),
    path('tag/<str:slug>/update/', update_tag, name='update_tag'),
    # AI相关路由
    path('generate-summary/', generate_summary_view, name='generate_summary'),
    path('generate-reply/', generate_reply_view, name='generate_reply'),
    path('generate-image/', generate_image_view, name='generate_image'),
]
