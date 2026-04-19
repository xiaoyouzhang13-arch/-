from sentence_transformers import SentenceTransformer
import chromadb
import numpy as np
from django.conf import settings
import os


class VectorSearch:
    def __init__(self):
        """初始化向量搜索工具"""
        self.model = None
        self.model_load_error = None
        # 初始化Chroma DB
        self.chroma_client = chromadb.PersistentClient(
            path=os.path.join(settings.BASE_DIR, 'vector_db')
        )
        # 获取或创建集合
        self.collection = self.chroma_client.get_or_create_collection(
            name='documents',
            metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
        )

    def _ensure_model(self):
        """按需加载模型，避免在服务启动时因网络问题崩溃。"""
        if self.model is not None:
            return self.model
        if self.model_load_error is not None:
            raise RuntimeError(f"向量模型不可用: {self.model_load_error}")
        try:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            return self.model
        except Exception as e:
            self.model_load_error = str(e)
            raise RuntimeError(f"向量模型加载失败: {self.model_load_error}")
    
    def text_to_vector(self, text):
        """
        将文本转换为向量
        :param text: 输入文本
        :return: 归一化后的向量
        """
        if not text or not text.strip():
            raise ValueError("输入文本不能为空")
        
        model = self._ensure_model()
        # 生成向量
        vector = model.encode(text)
        
        # 向量归一化（提高相似度计算准确性）
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        return vector.tolist()
    
    def sync_documents(self):
        """
        同步数据库中的文档到向量库
        支持全量同步
        """
        from search_app.models import Document
        
        # 重新创建集合（清空现有数据）
        self.chroma_client.delete_collection(name='documents')
        self.collection = self.chroma_client.create_collection(
            name='documents',
            metadata={"hnsw:space": "cosine"}
        )
        
        # 获取所有文档
        documents = Document.objects.all()
        
        # 准备批量数据
        ids = []
        embeddings = []
        metadatas = []
        documents_text = []
        
        for doc in documents:
            # 组合标题和内容作为向量输入
            combined_text = f"{doc.title} {doc.content}"
            try:
                # 生成向量
                vector = self.text_to_vector(combined_text)
                
                # 添加到批量数据
                ids.append(str(doc.id))
                embeddings.append(vector)
                metadatas.append({
                    'id': doc.id,
                    'title': doc.title,
                    'created_at': doc.created_at.isoformat()
                })
                documents_text.append(combined_text)
            except Exception as e:
                print(f"处理文档 {doc.id} 时出错: {e}")
                continue
        
        # 批量添加到向量库
        if ids:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents_text
            )
        
        return len(ids)
    
    def search(self, query, top_k=5):
        """
        向量搜索
        :param query: 搜索查询文本
        :param top_k: 返回结果数量
        :return: 搜索结果列表
        """
        if not query or not query.strip():
            raise ValueError("搜索查询不能为空")
        
        # 生成查询向量
        query_vector = self.text_to_vector(query)
        
        # 搜索向量库
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            include=['metadatas', 'documents', 'distances']
        )
        
        # 处理结果
        search_results = []
        for i in range(len(results['ids'][0])):
            # 余弦距离转换为相似度分数（1 - 距离）
            similarity_score = 1 - results['distances'][0][i]
            
            search_results.append({
                'id': results['metadatas'][0][i]['id'],
                'title': results['metadatas'][0][i]['title'],
                'created_at': results['metadatas'][0][i]['created_at'],
                'similarity': round(similarity_score, 4)
            })
        
        return search_results


# 创建全局实例
vector_search = VectorSearch()
