from django import template
import os

register = template.Library()

@register.filter

def basename(value):
    """提取文件名"""
    return os.path.basename(value)