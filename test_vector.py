
import asyncio
import os
from adaptive_agent_mcp.src.indexer import indexer
from adaptive_agent_mcp.src.vector_store import get_vector_store
from adaptive_agent_mcp.src.services.embedding import EmbeddingService
from adaptive_agent_mcp.src.config import config

async def test_vector_pipeline():
    print("Testing Vector Intelligence Pipeline...")
    
    # 1. Check Embedding Config
    print(f"Provider: {config.embedding_provider}")
    try:
        service = EmbeddingService.get_instance()
        print("EmbeddingService initialized successfully.")
    except ValueError as e:
        print(f"EmbeddingService skipped: {e}")
        print("Test will proceed without vector generation.")
        return

    # 2. Run Indexer
    print("Running Indexer.build_index()...")
    await indexer.build_index(force_full=True)
    
    # 3. Check VectorStore
    store = get_vector_store()
    count = store.count()
    print(f"VectorStore Document Count: {count}")
    
    if count > 0:
        # 4. Try semantic search
        query = "测试"
        print(f"Running semantic search for: {query}")
        emb = await service.embed_query(query)
        results = store.search(emb, limit=3)
        print(f"Found {len(results)} results.")
        for res in results:
            print(f" - [{res.score:.4f}] {res.content[:50]}...")
            
    else:
        print("VectorStore is empty. (Maybe no content or embedding failed safely)")

if __name__ == "__main__":
    asyncio.run(test_vector_pipeline())
