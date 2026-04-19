# Django文本向量搜索功能

## 功能说明

本模块实现了基于sentence-transformers和Chroma DB的工业级文本向量搜索功能，支持中文/英文文本的语义相似度搜索。

## 技术栈

- 文本嵌入模型：sentence-transformers/all-MiniLM-L6-v2
- 向量数据库：Chroma DB（嵌入式部署）
- 相似度计算：余弦相似度
- API接口：RESTful API

## 安装依赖

```bash
python -m pip install sentence-transformers chromadb
```

## 数据库迁移

```bash
python manage.py makemigrations search_app
python manage.py migrate
```

## API接口

### 1. 添加测试文档

**URL**: `/search/add-document/`
**方法**: POST
**请求体**:
```json
{
  "title": "测试文档标题",
  "content": "测试文档内容，包含需要搜索的文本"
}
```
**响应**:
```json
{
  "code": 200,
  "message": "文档添加成功",
  "data": {
    "id": 1,
    "title": "测试文档标题",
    "content": "测试文档内容，包含需要搜索的文本",
    "created_at": "2026-03-20T10:00:00Z"
  }
}
```

### 2. 向量搜索

**URL**: `/search/search/`
**方法**: POST
**请求体**:
```json
{
  "query": "搜索查询文本",
  "top_k": 5
}
```
**响应**:
```json
{
  "code": 200,
  "message": "搜索成功",
  "data": {
    "query": "搜索查询文本",
    "results": [
      {
        "id": 1,
        "title": "测试文档标题",
        "created_at": "2026-03-20T10:00:00Z",
        "similarity": 0.95
      }
    ]
  }
}
```

### 3. 手动同步文档到向量库

**URL**: `/search/sync-documents/`
**方法**: GET
**响应**:
```json
{
  "code": 200,
  "message": "文档同步成功，共同步 5 个文档"
}
```

## 测试示例

### 添加测试文档

```bash
curl -X POST http://127.0.0.1:8000/search/add-document/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Python编程入门",
    "content": "Python是一种简单易学的编程语言，广泛应用于Web开发、数据分析、人工智能等领域。"
  }'
```

### 执行向量搜索

```bash
curl -X POST http://127.0.0.1:8000/search/search/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "学习编程语言",
    "top_k": 3
  }'
```

## 工业级优化建议

1. **异步同步**：对于大量文档，使用异步任务（如Celery）进行向量库同步
2. **模型升级**：根据需求选择更适合的嵌入模型，如多语言模型
3. **向量数据库替换**：对于大规模应用，可考虑使用Milvus、Pinecone等专业向量数据库
4. **缓存机制**：对频繁的搜索查询结果进行缓存
5. **批量处理**：优化向量生成和存储的批量处理能力
6. **监控告警**：添加向量搜索性能监控和异常告警

## 常见问题

1. **向量生成失败**：检查输入文本是否为空或格式异常
2. **搜索结果为空**：确保向量库已同步，且查询文本与文档内容相关
3. **性能问题**：对于大量文档，考虑使用更高效的向量数据库和模型
4. **内存使用**：all-MiniLM-L6-v2模型较小，但仍需注意内存使用情况
