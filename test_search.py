
import asyncio
import json
from adaptive_agent_mcp.src.tools.memory import append_daily_log, query_knowledge, delete_knowledge
from adaptive_agent_mcp.src.router import KnowledgeRouter

async def test_search():
    print("Testing Search Logic (Fallback)...")
    
    # 1. Add Unique Fact
    unique_id = "test-search-fact-123"
    keyword = "SuperUniqueKeyword777"
    fact = {
        "id": unique_id,
        "fact": f"This is a fact with {keyword} for testing search.",
        "category": "domain_knowledge",
        "scope": "project:test-search"
    }
    
    print(f"Adding fact {unique_id}...")
    await append_daily_log(atomic_fact=fact, scope="project:test-search")
    
    # 2. Search with Query (Global/Fallback)
    # Should search all partitions and find it
    print(f"Searching for '{keyword}'...")
    results = await query_knowledge(query=keyword)
    print(f"Results:\n{results}")
    
    if keyword in results and unique_id in results:
        print("✓ Fallback Search Found the Item!")
    else:
        print("✗ Fallback Search FAILED to find item.")
        
    # 3. Clean up
    print("Cleaning up...")
    await delete_knowledge(id=unique_id, reason="Test Cleanup")
    print("Done.")

if __name__ == "__main__":
    asyncio.run(test_search())
