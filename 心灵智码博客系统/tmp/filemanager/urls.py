from django.urls import path
from .views import file_list, upload_file, delete_file, file_detail, download_file

urlpatterns = [
    path('', file_list, name='file_list'),
    path('upload/', upload_file, name='upload_file'),
    path('delete/<int:pk>/', delete_file, name='delete_file'),
    path('detail/<int:pk>/', file_detail, name='file_detail'),
    path('download/<int:pk>/', download_file, name='download_file'),
]
