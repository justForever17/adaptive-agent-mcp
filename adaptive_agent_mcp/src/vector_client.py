"""
VectorClient - 通用向量 API 客户端

支持:
- OpenAI 兼容的 Embedding API (ModelScope, SiliconFlow, DeepSeek, etc.)
- Cohere/Jina 兼容的 Rerank API
"""

import httpx
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from .config import config


@dataclass
class EmbeddingResult:
    """Embedding 结果"""
    embeddings: List[List[float]]
    model: str
    usage: Dict[str, int]


@dataclass
class RerankResult:
    """Rerank 结果"""
    results: List[Dict[str, Any]]  # [{index, relevance_score, document?}]
    model: str


class VectorClient:
    """
    通用向量 API 客户端
    
    使用方式:
        client = VectorClient()
        
        # Embedding
        embeddings = client.embed(["Hello world", "你好世界"])
        
        # Rerank
        results = client.rerank("什么是 Python", ["Python 是一种编程语言", "Java 也是编程语言"])
    """
    
    def __init__(
        self,
        embedding_base_url: Optional[str] = None,
        embedding_api_key: Optional[str] = None,
        embedding_model: Optional[str] = None,
        rerank_base_url: Optional[str] = None,
        rerank_api_key: Optional[str] = None,
        rerank_model: Optional[str] = None,
    ):
        # Embedding 配置
        self.embedding_base_url = embedding_base_url or config.embedding_base_url
        self.embedding_api_key = embedding_api_key or config.embedding_api_key
        self.embedding_model = embedding_model or config.embedding_model
        
        # Rerank 配置
        self.rerank_base_url = rerank_base_url or config.rerank_base_url
        self.rerank_api_key = rerank_api_key or config.rerank_api_key
        self.rerank_model = rerank_model or config.rerank_model
        
        # HTTP 客户端
        self._client: Optional[httpx.Client] = None
    
    @property
    def client(self) -> httpx.Client:
        """懒加载 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.Client(timeout=30.0)
        return self._client
    
    @property
    def embedding_available(self) -> bool:
        """检查 Embedding API 是否已配置"""
        return bool(self.embedding_base_url and self.embedding_api_key)
    
    @property
    def rerank_available(self) -> bool:
        """检查 Rerank API 是否已配置"""
        return bool(self.rerank_base_url and self.rerank_api_key)
    
    def embed(self, texts: List[str]) -> EmbeddingResult:
        """
        获取文本的向量表示 (OpenAI 兼容格式)
        
        Args:
            texts: 要转换的文本列表
            
        Returns:
            EmbeddingResult 包含向量列表和使用信息
            
        Raises:
            ValueError: 如果 API 未配置
            httpx.HTTPError: 如果 API 请求失败
        """
        if not self.embedding_available:
            raise ValueError(
                "Embedding API 未配置。请设置环境变量:\n"
                "  ADAPTIVE_EMBEDDING_BASE_URL\n"
                "  ADAPTIVE_EMBEDDING_API_KEY"
            )
        
        url = f"{self.embedding_base_url.rstrip('/')}/embeddings"
        
        response = self.client.post(
            url,
            headers={
                "Authorization": f"Bearer {self.embedding_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.embedding_model,
                "input": texts,
                "encoding_format": "float"
            }
        )
        response.raise_for_status()
        data = response.json()
        
        # 解析 OpenAI 格式响应
        embeddings = [item["embedding"] for item in data["data"]]
        
        return EmbeddingResult(
            embeddings=embeddings,
            model=data.get("model", self.embedding_model),
            usage=data.get("usage", {})
        )
    
    def rerank(
        self, 
        query: str, 
        documents: List[str], 
        top_n: Optional[int] = None,
        return_documents: bool = False
    ) -> RerankResult:
        """
        对文档进行重排序 (Cohere 兼容格式)
        
        Args:
            query: 查询文本
            documents: 待排序的文档列表
            top_n: 返回前 N 个结果，默认返回全部
            return_documents: 是否在结果中包含原始文档
            
        Returns:
            RerankResult 包含排序后的结果列表
            
        Raises:
            ValueError: 如果 API 未配置
            httpx.HTTPError: 如果 API 请求失败
        """
        if not self.rerank_available:
            raise ValueError(
                "Rerank API 未配置。请设置环境变量:\n"
                "  ADAPTIVE_RERANK_BASE_URL\n"
                "  ADAPTIVE_RERANK_API_KEY"
            )
        
        url = f"{self.rerank_base_url.rstrip('/')}/rerank"
        
        payload = {
            "model": self.rerank_model,
            "query": query,
            "documents": documents,
            "return_documents": return_documents
        }
        if top_n is not None:
            payload["top_n"] = top_n
        
        response = self.client.post(
            url,
            headers={
                "Authorization": f"Bearer {self.rerank_api_key}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        
        return RerankResult(
            results=data.get("results", []),
            model=data.get("model", self.rerank_model)
        )
    
    def embed_single(self, text: str) -> List[float]:
        """单个文本的向量化 (便捷方法)"""
        result = self.embed([text])
        return result.embeddings[0]
    
    def close(self):
        """关闭 HTTP 客户端"""
        if self._client:
            self._client.close()
            self._client = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


# 全局客户端实例 (懒加载)
_vector_client: Optional[VectorClient] = None


def get_vector_client() -> VectorClient:
    """获取全局 VectorClient 实例"""
    global _vector_client
    if _vector_client is None:
        _vector_client = VectorClient()
    return _vector_client
