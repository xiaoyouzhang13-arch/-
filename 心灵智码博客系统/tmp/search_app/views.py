from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
import json
from search_app.models import Document
from search_app.vector_search import vector_search


@csrf_exempt
def add_document(request):
    """
    添加测试文档接口
    POST请求
    """
    if request.method == 'POST':
        try:
            # 解析请求数据
            data = json.loads(request.body)
            title = data.get('title')
            content = data.get('content')
            
            # 验证输入
            if not title or not content:
                return JsonResponse({
                    'code': 400,
                    'message': '标题和内容不能为空'
                }, status=400)
            
            # 创建文档
            document = Document.objects.create(
                title=title,
                content=content
            )
            
            # 重新同步到向量库
            vector_search.sync_documents()
            
            return JsonResponse({
                'code': 200,
                'message': '文档添加成功',
                'data': {
                    'id': document.id,
                    'title': document.title,
                    'content': document.content,
                    'created_at': document.created_at.isoformat()
                }
            })
        except json.JSONDecodeError:
            return JsonResponse({
                'code': 400,
                'message': '无效的JSON格式'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'code': 500,
                'message': f'服务器内部错误: {str(e)}'
            }, status=500)
    else:
        return JsonResponse({
            'code': 405,
            'message': '只支持POST请求'
        }, status=405)


@csrf_exempt
def vector_search_view(request):
    """
    向量搜索接口
    POST请求
    """
    if request.method == 'POST':
        try:
            # 解析请求数据
            data = json.loads(request.body)
            query = data.get('query')
            top_k = data.get('top_k', 5)
            
            # 验证输入
            if not query:
                return JsonResponse({
                    'code': 400,
                    'message': '搜索查询不能为空'
                }, status=400)
            
            # 执行搜索
            results = vector_search.search(query, top_k)
            
            return JsonResponse({
                'code': 200,
                'message': '搜索成功',
                'data': {
                    'query': query,
                    'results': results
                }
            })
        except json.JSONDecodeError:
            return JsonResponse({
                'code': 400,
                'message': '无效的JSON格式'
            }, status=400)
        except ValueError as e:
            return JsonResponse({
                'code': 400,
                'message': str(e)
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'code': 500,
                'message': f'服务器内部错误: {str(e)}'
            }, status=500)
    else:
        return JsonResponse({
            'code': 405,
            'message': '只支持POST请求'
        }, status=405)


def sync_documents(request):
    """
    手动同步文档到向量库接口
    GET请求
    """
    if request.method == 'GET':
        try:
            # 执行同步
            count = vector_search.sync_documents()
            
            return JsonResponse({
                'code': 200,
                'message': f'文档同步成功，共同步 {count} 个文档'
            })
        except Exception as e:
            return JsonResponse({
                'code': 500,
                'message': f'服务器内部错误: {str(e)}'
            }, status=500)
    else:
        return JsonResponse({
            'code': 405,
            'message': '只支持GET请求'
        }, status=405)


def search_page(request):
    """
    搜索页面视图
    """
    return render(request, 'search_app/search.html')
