from django import forms
from .models import UserFile

class FileUploadForm(forms.ModelForm):
    """文件上传表单"""
    class Meta:
        model = UserFile
        fields = ('file', 'name', 'description')
        widgets = {
            'file': forms.ClearableFileInput(attrs={'multiple': False}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
