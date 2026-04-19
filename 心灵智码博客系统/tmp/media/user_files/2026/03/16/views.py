from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from .forms import CustomUserCreationForm, ProfileUpdateForm, CustomAuthenticationForm
from .models import CustomUser


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, 'Login successful!')
                return redirect('home')
    else:
        form = CustomAuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


def user_logout(request):
    logout(request)
    messages.success(request, 'Logout successful!')
    return redirect('home')


@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})


@login_required
def user_list(request):
    """显示用户列表（仅admin用户可见）"""
    if not request.user.is_superuser:
        messages.error(request, '您没有权限访问此页面！')
        return redirect('home')
    
    users = CustomUser.objects.all()
    return render(request, 'accounts/user_list.html', {'users': users})


@login_required
def delete_user(request, user_id):
    """删除用户账号（仅admin用户可操作）"""
    if not request.user.is_superuser:
        messages.error(request, '您没有权限执行此操作！')
        return redirect('home')
    
    user = get_object_or_404(CustomUser, id=user_id)
    
    # 防止admin删除自己
    if user == request.user:
        messages.error(request, '不能删除自己的账号！')
        return redirect('user_list')
    
    if request.method == 'POST':
        user.delete()
        messages.success(request, '用户账号删除成功！')
        return redirect('user_list')
    
    return render(request, 'accounts/delete_user.html', {'user': user})
