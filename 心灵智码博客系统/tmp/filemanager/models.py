from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class UserFile(models.Model):
    """用户上传的文件模型"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='user_files/%Y/%m/%d/')
    name = models.CharField(max_length=255, blank=True, help_text='文件名称（可选）')
    description = models.TextField(blank=True, help_text='文件描述（可选）')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_type = models.CharField(max_length=50, blank=True, help_text='文件类型')
    size = models.BigIntegerField(blank=True, null=True, help_text='文件大小（字节）')
    
    def __str__(self):
        return self.name or self.file.name.split('/')[-1]
    
    def save(self, *args, **kwargs):
        # 自动设置文件类型
        if not self.file_type and self.file:
            ext = self.file.name.split('.')[-1].lower()
            if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                self.file_type = 'image'
            elif ext in ['pdf', 'doc', 'docx', 'txt', 'md']:
                self.file_type = 'document'
            elif ext in ['zip', 'rar', '7z']:
                self.file_type = 'archive'
            else:
                self.file_type = 'other'
        
        # 自动设置文件大小
        if self.file and not self.size:
            self.size = self.file.size
        
        # 自动设置文件名
        if not self.name and self.file:
            self.name = self.file.name.split('/')[-1]
        
        super().save(*args, **kwargs)
