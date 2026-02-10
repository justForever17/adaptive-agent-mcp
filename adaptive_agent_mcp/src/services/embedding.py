
import abc
import asyncio
import httpx
from typing import List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from ..config import config

class EmbeddingProvider(abc.ABC):
    @abc.abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """Embed a single query string."""
        pass

    @abc.abstractmethod
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        pass

class OpenAICompatibleProvider(EmbeddingProvider):
    """
    Generic OpenAI-compatible provider (works for SiliconFlow, DeepSeek, etc.)
    """
    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def embed_query(self, text: str) -> List[float]:
        return (await self.embed_documents([text]))[0]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Check for empty input
        if not texts:
            return []
            
        # Strip newlines as recommended by OpenAI API best practices for embeddings
        texts = [t.replace("\n", " ") for t in texts]
        
        async with httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            timeout=30.0
        ) as client:
            response = await client.post(
                "/embeddings",
                json={
                    "model": self.model,
                    "input": texts,
                    "encoding_format": "float"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # Sort by index to ensure order
            sorted_data = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in sorted_data]

class OllamaProvider(EmbeddingProvider):
    """
    Ollama Provider (Local)
    """
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def embed_query(self, text: str) -> List[float]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=60.0) as client:
            response = await client.post(
                "/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text
                },
            )
            response.raise_for_status()
            return response.json()["embedding"]

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        sem = asyncio.Semaphore(config.embedding_batch_concurrency)
        
        async def _embed_one(text: str) -> List[float]:
            async with sem:
                async with httpx.AsyncClient(base_url=self.base_url, timeout=60.0) as client:
                    response = await client.post(
                        "/api/embeddings",
                        json={"model": self.model, "prompt": text}
                    )
                    response.raise_for_status()
                    return response.json()["embedding"]
        
        return await asyncio.gather(*[_embed_one(t) for t in texts])

class EmbeddingService:
    _instance: Optional[EmbeddingProvider] = None

    @classmethod
    def get_instance(cls) -> EmbeddingProvider:
        if cls._instance:
            return cls._instance
            
        provider_type = config.embedding_provider
        
        if provider_type == "openai_compatible" or provider_type == "siliconflow":
            if not config.embedding_base_url or not config.embedding_api_key:
                raise ValueError("Embedding base_url and api_key are required for openai_compatible provider.")
            
            cls._instance = OpenAICompatibleProvider(
                base_url=config.embedding_base_url,
                api_key=config.embedding_api_key,
                model=config.embedding_model
            )
            
        elif provider_type == "ollama":
            base_url = config.embedding_base_url or "http://localhost:11434"
            cls._instance = OllamaProvider(
                base_url=base_url,
                model=config.embedding_model
            )
            
        else:
            raise ValueError(f"Unsupported embedding provider: {provider_type}")
            
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset cached instance (for config reload or testing)."""
        cls._instance = None
