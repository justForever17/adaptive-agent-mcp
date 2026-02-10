
import asyncio
import json
from pathlib import Path
from adaptive_agent_mcp.src.tools.memory import append_daily_log, delete_knowledge
from adaptive_agent_mcp.src.config import config
from adaptive_agent_mcp.src.router import KnowledgeRouter

async def test_soft_delete():
    print("Testing Soft Delete & Audit Log...")
    
    # 1. Add a dummy fact
    fact_id = "test-delete-fact-v1"
    fact = {
        "id": fact_id,
        "fact": "This is a test fact for deletion",
        "category": "domain_knowledge"
    }
    
    print(f"Adding fact {fact_id}...")
    await append_daily_log(atomic_fact=fact, scope="global")
    
    # Verify it exists and is active
    target_file = KnowledgeRouter.get_target_file("global")
    content = target_file.read_text(encoding="utf-8")
    items = json.loads(content)
    item = next((i for i in items if i["id"] == fact_id), None)
    assert item is not None
    assert item["status"] == "active"
    print("Fact added successfully.")
    
    # 2. Delete it
    print(f"Deleting fact {fact_id}...")
    result = await delete_knowledge(id=fact_id, reason="Testing soft delete")
    print(f"Delete Result: {result}")
    
    # 3. Verify Soft Delete
    content = target_file.read_text(encoding="utf-8")
    items = json.loads(content)
    item = next((i for i in items if i["id"] == fact_id), None)
    assert item is not None
    assert item["status"] == "deleted"
    assert "deletedAt" in item
    assert item["deleteReason"] == "Testing soft delete"
    print("Soft delete verified.")
    
    # 4. Verify Audit Log
    audit_log = config.storage_path / "memory" / "audit.log"
    assert audit_log.exists()
    audit_content = audit_log.read_text(encoding="utf-8")
    print(f"Audit Log Content (Tail):\n{audit_content[-200:]}")
    
    last_line = audit_content.strip().split('\n')[-1]
    log_entry = json.loads(last_line)
    assert log_entry["action"] == "delete_knowledge"
    assert log_entry["target_id"] == fact_id
    assert log_entry["details"]["reason"] == "Testing soft delete"
    print("Audit log verified.")

async def main():
    try:
        await test_soft_delete()
        print("\nAll Data Safety tests passed!")
    except Exception as e:
        print(f"\nTest Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
