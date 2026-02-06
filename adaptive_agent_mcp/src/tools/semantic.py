"""
语义搜索工具 - 整合 VectorClient + VectorStore 的完整 RAG 管道
"""

from typing import List, Optional, Dict, Any
from ...server import mcp
from ..config import config
from ..vector_client import VectorClient, get_vector_client
from ..vector_store import VectorStore, get_vector_store, SearchResult


@mcp.tool()
def semantic_search(
    query: str,
    top_k: int = 10,
    use_rerank: bool = True,
    rerank_top_n: int = 5
) -> str:
    """
    **语义搜索** - 使用向量相似度在记忆库中查找语义相关的内容。
    
    ## 使用场景
    当关键词搜索无法满足需求时：
    - "查找与 React 状态管理相关的笔记" (能匹配到 Redux, Zustand 等)
    - "之前讨论过的性能优化方案" (能匹配到 lazy loading, code splitting 等)
    - "用户提到过的设计偏好" (能匹配到 暗色主题, 简洁风格 等)
    
    ## 参数说明
    - `query`: 自然语言查询
    - `top_k`: 初步召回数量，默认 10
    - `use_rerank`: 是否使用 Rerank 精排，默认 True (需要配置 Rerank API)
    - `rerank_top_n`: 精排后返回的结果数，默认 5
    
    ## 工作流程
    1. 将查询转换为向量 (Embedding API)
    2. 在向量库中执行 KNN 搜索
    3. (可选) 使用 Rerank API 对结果精排
    4. 返回最相关的文档
    
    ## 前置条件
    需要配置环境变量:
    - `ADAPTIVE_EMBEDDING_BASE_URL` + `ADAPTIVE_EMBEDDING_API_KEY`
    - (可选) `ADAPTIVE_RERANK_BASE_URL` + `ADAPTIVE_RERANK_API_KEY`
    
    ## 返回格式
    每个结果包含：相关性分数、文档ID、内容摘要
    """
    client = get_vector_client()
    store = get_vector_store()
    
    # 检查向量服务是否可用
    if not client.embedding_available:
        return (
            "❌ 语义搜索不可用：Embedding API 未配置。\n\n"
            "请设置环境变量:\n"
            "  ADAPTIVE_EMBEDDING_BASE_URL=https://api-inference.modelscope.cn/v1\n"
            "  ADAPTIVE_EMBEDDING_API_KEY=your-api-key\n\n"
            "可使用 `search_memory_content` 进行关键词搜索作为替代。"
        )
    
    if not store.available:
        return (
            "❌ 向量数据库不可用：sqlite-vec 未安装或加载失败。\n"
            "请运行: pip install sqlite-vec"
        )
    
    try:
        # Step 1: 向量化查询
        query_embedding = client.embed_single(query)
        
        # Step 2: KNN 搜索
        results = store.search(query_embedding, top_k=top_k)
        
        if not results:
            return "未找到相关内容。请尝试不同的查询词，或使用 `search_memory_content` 进行关键词搜索。"
        
        # Step 3: (可选) Rerank 精排
        if use_rerank and client.rerank_available and len(results) > rerank_top_n:
            documents = [r.content for r in results]
            rerank_result = client.rerank(query, documents, top_n=rerank_top_n)
            
            # 重新排序结果
            reranked_results = []
            for item in rerank_result.results:
                idx = item["index"]
                original = results[idx]
                reranked_results.append(SearchResult(
                    id=original.id,
                    content=original.content,
                    metadata=original.metadata,
                    distance=original.distance,
                    score=item["relevance_score"]
                ))
            results = reranked_results
        
        # 格式化输出
        output = [f"🔍 找到 {len(results)} 条相关结果:\n"]
        
        for i, r in enumerate(results, 1):
            # 截断长内容
            content_preview = r.content[:200] + "..." if len(r.content) > 200 else r.content
            source = r.metadata.get("source", "unknown")
            
            output.append(
                f"**[{i}]** (分数: {r.score:.3f})\n"
                f"📄 ID: {r.id}\n"
                f"📁 来源: {source}\n"
                f"```\n{content_preview}\n```\n"
            )
        
        return "\n".join(output)
        
    except Exception as e:
        return f"❌ 语义搜索失败: {str(e)}"


@mcp.tool()
def index_document(
    doc_id: str,
    content: str,
    source: str = "manual",
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    **索引文档** - 将文档添加到向量数据库，供语义搜索使用。
    
    ## 使用场景
    - 手动索引重要的代码片段或笔记
    - 批量导入外部知识库
    - 重建向量索引
    
    ## 参数说明
    - `doc_id`: 文档唯一标识符
    - `content`: 文档内容
    - `source`: 来源标识，如 "daily_log", "knowledge", "manual"
    - `metadata`: 附加元数据 (JSON 格式)
    
    ## 前置条件
    需要配置 Embedding API 环境变量。
    """
    client = get_vector_client()
    store = get_vector_store()
    
    if not client.embedding_available:
        return "❌ Embedding API 未配置，无法索引文档。"
    
    if not store.available:
        return "❌ 向量数据库不可用。"
    
    try:
        # 生成向量
        embedding = client.embed_single(content)
        
        # 存储到向量库
        full_metadata = metadata or {}
        full_metadata["source"] = source
        
        store.add(doc_id, content, embedding, full_metadata)
        
        return f"✅ 已索引文档 `{doc_id}` (维度: {len(embedding)}, 来源: {source})"
        
    except Exception as e:
        return f"❌ 索引失败: {str(e)}"


@mcp.tool()
def get_vector_stats() -> str:
    """
    **向量库状态** - 查看向量数据库的统计信息。
    
    返回:
    - 文档总数
    - 数据库路径
    - 配置状态
    """
    client = get_vector_client()
    store = get_vector_store()
    
    stats = []
    stats.append("📊 **向量系统状态**\n")
    
    # Embedding 状态
    if client.embedding_available:
        stats.append(f"✅ Embedding API: 已配置 ({client.embedding_model})")
    else:
        stats.append("❌ Embedding API: 未配置")
    
    # Rerank 状态
    if client.rerank_available:
        stats.append(f"✅ Rerank API: 已配置 ({client.rerank_model})")
    else:
        stats.append("⚠️  Rerank API: 未配置 (可选)")
    
    # 向量库状态
    if store.available:
        stats.append(f"✅ 向量数据库: sqlite-vec")
        stats.append(f"   路径: {store.db_path}")
        stats.append(f"   文档数: {store.count()}")
        stats.append(f"   维度: {store.dimension}")
    else:
        stats.append("❌ 向量数据库: 不可用")
    
    return "\n".join(stats)


@mcp.tool()
def fulltext_search(query: str, limit: int = 20) -> str:
    """
    **全文搜索 (SQLite FTS5)** - 使用 BM25 排名在记忆库中搜索关键词。
    
    ## 使用场景
    当需要精确匹配关键词时：
    - "搜索所有包含 'CORS' 的笔记"
    - "查找提到 'useEffect' 的代码"
    - "有没有关于 'Docker' 的记录"
    
    ## 与 semantic_search 的区别
    - `semantic_search`: 语义搜索，能理解同义词 (如 "Web框架" 匹配 "Next.js")
    - `fulltext_search`: 关键词搜索，精确匹配文本 (无需 API，本地执行)
    
    ## 参数说明
    - `query`: 搜索关键词，支持 FTS5 语法 (如 "react OR vue", "react NOT vue")
    - `limit`: 最大返回数量，默认 20
    
    ## 返回格式
    每个结果包含：BM25 排名分数、文档ID、匹配片段高亮
    
    ## 特点
    - 无需 API 配置，纯本地执行
    - 支持中英文分词 (unicode61 tokenizer)
    - 使用 BM25 算法排名
    """
    store = get_vector_store()
    
    try:
        results = store.fulltext_search(query, limit=limit)
        
        if not results:
            return f"未找到包含 '{query}' 的内容。"
        
        output = [f"🔍 找到 {len(results)} 条匹配 '{query}' 的结果:\n"]
        
        for i, r in enumerate(results, 1):
            # snippet 已经高亮了匹配部分
            snippet = r.snippet.replace(">>>>", "**").replace("<<<<", "**")
            source = r.metadata.get("source", "unknown")
            
            output.append(
                f"**[{i}]** (BM25: {abs(r.rank):.2f})\n"
                f"📄 ID: {r.id}\n"
                f"📁 来源: {source}\n"
                f"```\n{snippet}\n```\n"
            )
        
        return "\n".join(output)
        
    except Exception as e:
        return f"❌ 全文搜索失败: {str(e)}"
