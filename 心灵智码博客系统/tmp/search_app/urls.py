from django.urls import path
from search_app import views

urlpatterns = [
    path('add-document/', views.add_document, name='add_document'),
    path('search/', views.vector_search_view, name='vector_search'),
    path('sync-documents/', views.sync_documents, name='sync_documents'),
    path('page/', views.search_page, name='search_page'),
]
