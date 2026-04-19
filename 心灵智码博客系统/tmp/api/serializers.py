from rest_framework import serializers
from accounts.models import CustomUser
from blog.models import Post, Comment, Category, Tag
from forum.models import Forum, Topic, Post as ForumPost


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'bio', 'avatar', 'phone_number', 'date_of_birth')


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'description')


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class CommentSerializer(serializers.ModelSerializer):
    author = CustomUserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ('id', 'author', 'content', 'parent', 'created_at')


class PostSerializer(serializers.ModelSerializer):
    author = CustomUserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(read_only=True, many=True)
    comments = CommentSerializer(read_only=True, many=True)

    class Meta:
        model = Post
        fields = ('id', 'title', 'slug', 'content', 'excerpt', 'author', 'category', 'tags', 'featured_image', 'publish_date')


class ForumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Forum
        fields = ('id', 'name', 'slug', 'description')


class ForumPostSerializer(serializers.ModelSerializer):
    author = CustomUserSerializer(read_only=True)

    class Meta:
        model = ForumPost
        fields = ('id', 'author', 'content', 'created_at')


class TopicSerializer(serializers.ModelSerializer):
    author = CustomUserSerializer(read_only=True)
    forum = ForumSerializer(read_only=True)
    posts = ForumPostSerializer(read_only=True, many=True)

    class Meta:
        model = Topic
        fields = ('id', 'title', 'slug', 'content', 'author', 'forum', 'is_sticky', 'is_closed', 'views', 'created_at')
