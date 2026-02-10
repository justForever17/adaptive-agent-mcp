
import abc
import httpx
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from ..config import config
import logging

logger = logging.getLogger("adaptive-agent-mcp")

class RerankingResult:
    def __init__(self, index: int, relevance_score: float, document: Optional[Dict] = None):
        self.index = index
        self.relevance_score = relevance_score
        self.document = document

class RerankProvider(abc.ABC):
    @abc.abstractmethod
    async def rerank(self, query: str, documents: List[str], top_n: int = 10) -> List[RerankingResult]:
        """
        Rerank a list of documents based on the query.
        Returns a list of RerankingResult, sorted by relevance score (descending).
        """
        pass

class CohereCompatibleRerankProvider(RerankProvider):
    """
    Generic Cohere-compatible Rerank provider.
    Works for Cohere, SiliconFlow (BGE), Jina, etc.
    """
    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def rerank(self, query: str, documents: List[str], top_n: int = 10) -> List[RerankingResult]:
        if not documents:
            return []
            
        async with httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}", 
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            timeout=30.0
        ) as client:
            payload = {
                "model": self.model,
                "query": query,
                "documents": documents,
                "top_n": top_n,
                "return_documents": False 
            }
            
            # Different providers might have different payload structures, 
            # but Cohere/BGE usually follow this standard.
            response = await client.post("/rerank", json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Access 'results' field
            # Expected format: {"results": [{"index": 0, "relevance_score": 0.9}, ...]}
            results_data = data.get("results", [])
            
            reranked_results = []
            for item in results_data:
                reranked_results.append(RerankingResult(
                    index=item["index"],
                    relevance_score=item["relevance_score"]
                ))
            
            return reranked_results

class RerankService:
    _instance: Optional[RerankProvider] = None

    @classmethod
    def get_instance(cls) -> Optional[RerankProvider]:
        if cls._instance:
            return cls._instance
            
        provider_type = config.rerank_provider
        
        # Check if configured
        if not config.rerank_api_key:
            return None
            
        if provider_type == "cohere_compatible" or provider_type == "siliconflow":
            base_url = config.rerank_base_url
            if not base_url:
                # Default for real Cohere? Or SiliconFlow?
                # Better to require base_url for "compatible" modes to avoid confusion
                # But if provider is "cohere" (native), we could use default.
                # Here we assume compatible means explicit URL.
                return None
                
            cls._instance = CohereCompatibleRerankProvider(
                base_url=base_url,
                api_key=config.rerank_api_key,
                model=config.rerank_model
            )
        else:
            logger.warning(f"Unsupported rerank provider: {provider_type}")
            return None
            
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset cached instance."""
        cls._instance = None
