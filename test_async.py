
import asyncio
from pathlib import Path
from adaptive_agent_mcp.src.memory_parser import MemoryParser
from adaptive_agent_mcp.src.storage import StorageValidation
from adaptive_agent_mcp.src.router import KnowledgeRouter
from adaptive_agent_mcp.src.config import config

async def test_memory_parser():
    print("Testing MemoryParser...")
    parser = await MemoryParser().load()
    parser.set("test_key", "test_value", "app:test")
    saved_path = await parser.save()
    print(f"Saved memory to {saved_path}")
    
    # Reload to verify
    parser2 = await MemoryParser().load()
    val = parser2.get("test_key", "app:test")
    print(f"Retrieved value: {val}")
    assert val == "test_value"

async def test_storage_async_append():
    print("\nTesting StorageValidation.async_append_to_file...")
    test_file = config.storage_path / "test_async.log"
    if test_file.exists():
        test_file.unlink()
        
    await StorageValidation.async_append_to_file(test_file, "Line 1")
    await StorageValidation.async_append_to_file(test_file, "Line 2")
    
    content = test_file.read_text(encoding="utf-8")
    print(f"File content:\n{content}")
    assert "Line 1\n\nLine 2" in content or "Line 1\nLine 2" in content

async def test_router():
    print("\nTesting KnowledgeRouter...")
    p1 = KnowledgeRouter.get_target_file("project:alpha")
    print(f"project:alpha -> {p1}")
    assert "projects" in str(p1) and "alpha" in str(p1)
    
    p2 = KnowledgeRouter.get_target_file("app:coding")
    print(f"app:coding -> {p2}")
    assert "coding" in str(p2)

async def main():
    try:
        await test_memory_parser()
        await test_storage_async_append()
        await test_router()
        print("\nAll Async Foundation tests passed!")
    except Exception as e:
        print(f"\nTest Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
