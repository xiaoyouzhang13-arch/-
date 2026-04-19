import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fullwebproject.settings')
django.setup()

from search_app.models import Document

# 检查文档数量
print('文档总数:', Document.objects.count())
print('最近10篇文档:')
for doc in Document.objects.order_by('-id')[:10]:
    print(f'{doc.id}: {doc.title}')
