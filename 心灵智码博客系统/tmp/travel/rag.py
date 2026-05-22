"""RAG (Retrieval-Augmented Generation) pipeline for travel planning."""

import chromadb
import numpy as np
from sentence_transformers import SentenceTransformer
from django.conf import settings
import os

# Reuse the same model pattern as search_app
_model = None
_model_error = None


def _get_model():
    global _model, _model_error
    if _model is not None:
        return _model
    if _model_error is not None:
        raise RuntimeError(f"向量模型不可用: {_model_error}")
    try:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
        return _model
    except Exception as e:
        _model_error = str(e)
        raise RuntimeError(f"向量模型加载失败: {_model_error}")


def _get_collection():
    client = chromadb.PersistentClient(
        path=os.path.join(settings.BASE_DIR, 'vector_db')
    )
    return client.get_or_create_collection(
        name='travel_knowledge',
        metadata={"hnsw:space": "cosine"}
    )


def text_to_vector(text):
    if not text or not text.strip():
        raise ValueError("输入文本不能为空")
    model = _get_model()
    vector = model.encode(text)
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm
    return vector.tolist()


def sync_travel_knowledge():
    """Index all Destination and TravelNote data into the vector DB."""
    from travel.models import Destination, TravelNote

    client = chromadb.PersistentClient(
        path=os.path.join(settings.BASE_DIR, 'vector_db')
    )
    try:
        client.delete_collection(name='travel_knowledge')
    except Exception:
        pass
    collection = client.create_collection(
        name='travel_knowledge',
        metadata={"hnsw:space": "cosine"}
    )

    ids = []
    embeddings = []
    metadatas = []
    documents = []

    # Index destinations
    for dest in Destination.objects.all():
        text = (
            f"景点名称：{dest.name}。"
            f"所在城市：{dest.city}，{dest.province}。"
            f"分类：{dest.get_category_display()}。"
            f"简介：{dest.description[:300]}。"
            f"最佳季节：{dest.best_season}。"
            f"建议游玩：{dest.recommended_days}天。"
            f"门票：{dest.ticket_price}元。"
            f"开放时间：{dest.opening_hours}。"
            f"旅游贴士：{dest.tips[:200] if dest.tips else '暂无'}。"
        )
        try:
            vector = text_to_vector(text)
            ids.append(f'dest_{dest.id}')
            embeddings.append(vector)
            metadatas.append({
                'type': 'destination',
                'id': dest.id,
                'name': dest.name,
                'city': dest.city,
                'category': dest.category,
            })
            documents.append(text)
        except Exception as e:
            print(f"索引景点 {dest.name} 失败: {e}")

    # Index travel notes
    for note in TravelNote.objects.filter(is_published=True).select_related('trip_plan__destination'):
        trip_dest = note.trip_plan.destination.name if note.trip_plan and note.trip_plan.destination else '未知'
        text = (
            f"游记标题：{note.title}。"
            f"目的地：{trip_dest}。"
            f"游记内容：{note.content[:500]}。"
        )
        try:
            vector = text_to_vector(text)
            ids.append(f'note_{note.id}')
            embeddings.append(vector)
            metadatas.append({
                'type': 'travel_note',
                'id': note.id,
                'title': note.title,
                'author': note.user.username,
            })
            documents.append(text)
        except Exception as e:
            print(f"索引游记 {note.title} 失败: {e}")

    if ids:
        collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)

    return len(ids)


def search_travel_knowledge(query, top_k=5):
    """Search the travel knowledge base for relevant destinations and notes."""
    if not query or not query.strip():
        return []

    query_vector = text_to_vector(query)
    collection = _get_collection()

    try:
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            include=['metadatas', 'documents', 'distances']
        )
    except Exception:
        return []

    search_results = []
    for i in range(len(results['ids'][0])):
        similarity = 1 - results['distances'][0][i]
        search_results.append({
            'metadata': results['metadatas'][0][i],
            'content': results['documents'][0][i],
            'similarity': round(similarity, 4),
        })

    return search_results


def generate_rag_itinerary(destination_name, days, budget, preferences):
    """Generate itinerary using RAG: retrieve relevant knowledge first, then call LLM."""
    from .utils import call_deepseek_api, parse_itinerary_response

    # Step 1: Search for relevant knowledge
    query = f"{destination_name} {preferences} 旅游 景点 行程"
    knowledge_results = search_travel_knowledge(query, top_k=8)

    # Build context from retrieved knowledge
    context_parts = []
    for r in knowledge_results:
        if r['similarity'] > 0.3:  # Only use reasonably relevant results
            context_parts.append(r['content'])

    knowledge_context = '\n\n'.join(context_parts) if context_parts else '暂无相关知识库信息。'

    # Step 2: Build enhanced prompt with retrieved context
    prompt = f"""你是一个专业的旅游规划师。请根据以下知识库信息和用户需求生成详细的{days}天旅行行程：

【旅游知识库】：
{knowledge_context}

【用户需求】：
- 目的地：{destination_name}
- 天数：{days}天
- 预算：{budget}元
- 偏好：{preferences}

请严格按照以下格式输出每一天的行程（每条一行）：
第1天：
时间：08:00-09:00 | 活动：XXX | 交通：步行 | 备注：XXX
...

要求：
1. 每天安排3-5个活动，优先使用知识库中的真实景点
2. 时间合理衔接，考虑开放时间和用餐
3. 交通方式：步行、公交、地铁、打车、自驾
4. 总花费不超出预算
5. 知识库中如果有相关贴士，请参考使用"""

    response = call_deepseek_api(prompt, max_tokens=3000)
    if not response:
        return None
    return parse_itinerary_response(response, days)


def generate_travel_tips(destination_name, days, budget):
    """Generate accommodation, dining, and transport tips for a trip."""
    from .utils import call_deepseek_api
    from .rag import search_travel_knowledge

    # Search for relevant knowledge
    knowledge_results = search_travel_knowledge(f'{destination_name} 住宿 餐饮 交通', top_k=5)
    knowledge_parts = []
    for r in knowledge_results:
        if r['similarity'] > 0.3:
            knowledge_parts.append(r['content'])
    knowledge_context = '\n'.join(knowledge_parts[:3]) if knowledge_parts else '暂无相关知识库信息。'

    prompt = f"""你是一个专业的旅行顾问。请根据以下信息为{destination_name}的{days}天旅行（预算{budget}元）提供实用的住宿、餐饮和交通建议：

【参考知识库】：
{knowledge_context}

请分三类输出，每类2-3条具体建议（不要泛泛而谈）：

住宿建议：
- 推荐区域：XXX，原因：XXX，预算范围：XXX元/晚
- ...

餐饮建议：
- 推荐美食：XXX，推荐店铺类型：XXX，人均消费：XXX元
- ...

交通建议：
- 主要交通方式：XXX，单日交通预算：XXX元
- ...

要求：建议要具体、可执行，结合目的地实际情况。"""

    response = call_deepseek_api(prompt, max_tokens=800)
    if not response:
        return None
    return response