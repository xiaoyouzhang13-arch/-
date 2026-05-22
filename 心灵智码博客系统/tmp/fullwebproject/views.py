from django.shortcuts import render
from blog.models import Post
from travel.models import TripPlan, Destination


def home(request):
    posts = Post.objects.filter(is_published=True).select_related('author', 'category').prefetch_related('tags').order_by('-publish_date')
    recent_posts = posts[:6]
    recent_trips = TripPlan.objects.filter(is_public=True).select_related('user', 'destination').order_by('-created_at')[:6]
    featured_destinations = Destination.objects.filter(is_featured=True).order_by('-rating')[:4]
    return render(request, 'home.html', {
        'recent_posts': recent_posts,
        'recent_trips': recent_trips,
        'featured_destinations': featured_destinations,
    })
