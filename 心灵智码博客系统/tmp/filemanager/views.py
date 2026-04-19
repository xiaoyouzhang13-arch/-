from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse
from .models import UserFile
from .forms import FileUploadForm
import os

@login_required
def file_list(request):
    """显示用户上传的文件列表"""
    files = UserFile.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'filemanager/file_list.html', {'files': files})

@login_required
def upload_file(request):
    """上传文件"""
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            user_file = form.save(commit=False)
            user_file.user = request.user
            user_file.save()
            messages.success(request, '文件上传成功！')
            return redirect('file_list')
    else:
        form = FileUploadForm()
    return render(request, 'filemanager/upload_file.html', {'form': form})

@login_required
def delete_file(request, pk):
    """删除文件"""
    user_file = get_object_or_404(UserFile, pk=pk, user=request.user)
    if request.method == 'POST':
        # 删除实际文件
        if user_file.file:
            if os.path.exists(user_file.file.path):
                os.remove(user_file.file.path)
        # 删除数据库记录
        user_file.delete()
        messages.success(request, '文件删除成功！')
        return redirect('file_list')
    return render(request, 'filemanager/delete_file.html', {'file': user_file})

@login_required
def file_detail(request, pk):
    """查看文件详情"""
    user_file = get_object_or_404(UserFile, pk=pk, user=request.user)
    return render(request, 'filemanager/file_detail.html', {'file': user_file})


@login_required
def download_file(request, pk):
    """下载文件"""
    user_file = get_object_or_404(UserFile, pk=pk, user=request.user)
    return FileResponse(open(user_file.file.path, 'rb'), as_attachment=True, filename=user_file.name)
