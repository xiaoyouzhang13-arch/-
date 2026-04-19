#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
创建管理员用户（如果还没有）并创建一篇说明如何使用博客的文章
"""

import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fullwebproject.settings')
django.setup()

from django.contrib.auth import get_user_model
from blog.models import Post, Category, Tag
from django.utils import timezone

User = get_user_model()

def create_admin_user():
    """创建管理员用户"""
    try:
        admin = User.objects.get(username='admin')
        print("管理员用户已存在")
    except User.DoesNotExist:
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        print("管理员用户创建成功")
    return admin

def create_blog_guide():
    """创建博客使用指南文章"""
    # 创建管理员用户
    admin = create_admin_user()
    
    # 创建或获取分类
    category, created = Category.objects.get_or_create(
        name='指南',
        slug='guide'
    )
    
    # 创建或获取标签
    tags = []
    tag_slugs = {
        '使用指南': 'guide',
        'Markdown': 'markdown',
        '博客': 'blog'
    }
    for tag_name in ['使用指南', 'Markdown', '博客']:
        tag, created = Tag.objects.get_or_create(
            name=tag_name,
            slug=tag_slugs[tag_name]
        )
        tags.append(tag)
    
    # 创建博客文章
    content = """# 博客使用指南

## 1. 如何创建博客文章

1. 登录到管理后台（/admin/）
2. 点击左侧菜单栏中的 "Posts" -> "Add Post"
3. 填写标题、内容等信息
4. 选择分类和标签
5. 上传特色图片（可选）
6. 勾选 "Is published" 选项以发布文章
7. 点击 "Save" 按钮保存

## 2. Markdown 编辑指南

### 2.1 基本语法

- **标题**：使用 `#` 符号，例如 `# 一级标题`、`## 二级标题`
- **粗体**：使用 `**粗体文本**`
- **斜体**：使用 `*斜体文本*`
- **列表**：使用 `-` 或 `*` 符号，例如：
  - 项目1
  - 项目2
  - 项目3
- **链接**：使用 `[链接文本](链接地址)`
- **图片**：使用 `![图片描述](图片地址)`

### 2.2 代码块

支持多种编程语言的代码高亮，例如：

```python
# Python代码示例
def hello():
    print("Hello, World!")
```

```javascript
// JavaScript代码示例
function hello() {
    console.log("Hello, World!");
}
```

```cpp
// C++代码示例
#include <iostream>
using namespace std;

int main() {
    cout << "Hello, World!" << endl;
    return 0;
}
```

```java
// Java代码示例
public class Hello {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
```

### 2.3 表格

| 姓名 | 年龄 | 职业 |
|------|------|------|
| 张三 | 25   | 工程师 |
| 李四 | 30   | 设计师 |

## 3. 其他功能

- **标签管理**：在管理后台可以创建和管理标签
- **分类管理**：在管理后台可以创建和管理分类
- **评论功能**：读者可以对文章发表评论和回复

## 4. 代码复制功能

在文章页面，每个代码块右上角都有一个 "复制" 按钮，点击即可复制代码内容。
"""
    
    # 检查是否已存在该文章
    try:
        post = Post.objects.get(title='博客使用指南')
        print("博客使用指南文章已存在")
        # 更新标签
        post.tags.clear()
        post.tags.add(*tags)
        print("标签已更新")
    except Post.DoesNotExist:
        post = Post.objects.create(
            title='博客使用指南',
            slug='blog-guide',
            content=content,
            author=admin,
            category=category,
            is_published=True,
            publish_date=timezone.now()
        )
        # 添加标签
        post.tags.add(*tags)
        print("博客使用指南文章创建成功")

if __name__ == '__main__':
    create_blog_guide()
