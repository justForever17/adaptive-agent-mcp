
from typing import List, Optional, Any, Dict
from datetime import datetime
import json
import uuid
import asyncio
import aiofiles
from pathlib import Path

from ...server import mcp
from ..config import config
from ..storage import StorageValidation
from ..indexer import indexer
from ..memory_parser import MemoryParser
from ..lock_manager import LockManager
from ..router import KnowledgeRouter

@mcp.tool()
async def update_preference(
    key: str,
    value: str,
    scope: str = "global"
) -> str:
    """
    [SAVE] **保存用户偏好** - 当用户说"记住"、"以后都..."时调用。
    
    ## 触发时机 (WHEN TO CALL)
    当用户表达**持久性偏好**时调用：
    - "我喜欢...", "以后都用...", "记住我的风格是..."
    - "写代码时要...", "跟我聊天时要..."
    - "这个项目使用..."
    
    ## Scope 参数使用指南 (语义理解驱动)
    
    根据**对话意图**推断 scope，无需用户明确说明：
    
    | 用户在做什么 | 应使用的 scope | 示例 |
    |-------------|---------------|------|
    | 与你闲聊、表达情感偏好 | `app:chat` | "说话甜一点" |
    | 讨论代码、技术规范 | `app:coding` | "代码注释用英文" |
    | 写文档、文案相关 | `app:writing` | "写作风格正式" |
    | 在具体项目中设置规范 | `project:{项目名}` | "这个项目用 React" |
    | 设置通用偏好 | `global` | "我的语言是中文" |
    
    ## 示例
    ```python
    await update_preference("communication_style", "卖萌", "app:chat")
    ```
    """
    try:
        # Async load
        memory = await MemoryParser().load()
        memory.set(key, value, scope)
        # Async save
        saved_path = await memory.save()
        return f"✓ 已保存偏好 `{key}` = `{value}` 到 [{scope}] (文件: {saved_path})"
    except Exception as e:
        return f"Error updating preference: {e}"


@mcp.tool()
async def append_daily_log(
    content: Optional[str] = None, 
    atomic_fact: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
    scope: Optional[str] = None
) -> str:
    """
    [SAVE] **写入记忆** - 当用户要求保存信息或任务完成时调用。
    
    ## 触发时机 (WHEN TO CALL)
    当用户说出以下关键词时，**必须**调用此工具：
    - "记住", "保存", "记录", "别忘了", "以后都这样"
    - "我喜欢...", "我不喜欢...", "我习惯..."
    - "这个项目用...", "这个仓库的规范是..."
    - 任务完成时主动记录进度
    - 解决问题后记录解决方案
    
    ## 参数使用指南
    
    ### 1. 每日笔记 (短期/临时)
    用于任务进度、临时想法、错误记录：
    ```
    append_daily_log(content="完成了用户认证模块的重构")
    ```
    
    ### 2. 领域知识 (长期)
    用于技术规范、API 用法、最佳实践：
    ```
    append_daily_log(atomic_fact={
        "fact": "Next.js 15 使用 App Router 作为默认路由",
        "category": "domain_knowledge"
    })
    ```
    
    ### 3. 用户偏好 (永久) - 推荐使用 update_preference
    对于用户偏好，**优先使用 `update_preference` 工具**，它会智能覆盖旧值。
    如果仍要使用此工具：
    ```
    append_daily_log(atomic_fact={
        "fact": "用户喜欢使用 Tailwind CSS",
        "category": "user_preference"
    })
    ```
    
    ### 4. Scope 参数 (语义理解驱动)
    
    根据**对话意图**推断 scope：
    
    | 用户在做什么 | 应使用的 scope |
    |-------------|---------------|
    | 与你闲聊、表达情感偏好 | app:chat |
    | 讨论代码、技术规范 | app:coding |
    | 在具体项目中设置规范 | project:{项目名} |
    | 设置通用偏好 | global |
    
    ### 5. 原子化记录原则 (CRITICAL: Atomic Logging)
    
    对于长内容 (>800字)，**必须**使用 Markdown 二级或三级标题 (`##`, `###`) 将内容拆分为逻辑独立的段落。
    
    - ❌ **禁止**: 写入一大坨无结构的纯文本流水账。
    - ✅ **要求**:
      ```markdown
      ## 用户认证模块重构
      完成了...
      
      ## API 接口变更
      修改了...
      ```
    - **原理**: 系统会根据标题自动进行语义切分(Semantic Chunking)，确保检索精度。
    
    **注意**: 不要询问日期，系统自动记录时间戳。
    """
    now = datetime.now()
    
    # 1. Handle Daily Log (Ephemeral)
    if content:
        log_path = StorageValidation.get_daily_log_path(now)
        # Create header if new file - check size/existence synchronously (fast enough) or async
        # For simplicity in 9.1, keep check sync-ish or rely on append validation
        # But we need atomic write.
        
        # Async Append
        if not log_path.exists() or log_path.stat().st_size == 0:
            header_tags = str(tags) if tags else "[]"
            header = f"---\ntype: daily_log\ndate: \"{now.strftime('%Y-%m-%d')}\"\ntags: {header_tags}\n---\n\n"
            await StorageValidation.async_append_to_file(log_path, header)
            
        time_str = now.strftime("%H:%M")
        entry = f"### {time_str}\n{content}"
        await StorageValidation.async_append_to_file(log_path, entry)
        
        # Trigger Re-index (Background Task)
        asyncio.create_task(indexer.build_index())
        return f"Appended log to {log_path}"

    # 2. Handle Knowledge Graph (Atomic Fact)
    if atomic_fact:
        fact_content = atomic_fact.get("fact")
        if not fact_content or not isinstance(fact_content, str):
            return "Error: atomic_fact must contain a non-empty 'fact' string field."
        
        category = atomic_fact.get("category", "general")
        effective_scope = scope or "global"
        
        # A. User Preference -> MEMORY.md
        if category == "user_preference":
            try:
                memory = await MemoryParser().load()
                
                if "喜欢" in fact_content or "偏好" in fact_content:
                    key = "preference_note"
                elif "风格" in fact_content:
                    key = "style_note"
                else:
                    key = "user_note"
                
                key = f"{key}_{now.strftime('%H%M%S')}"
                memory.set(key, fact_content, effective_scope)
                await memory.save()
                return f"Updated User Preference in MEMORY.md [{effective_scope}]"
            except Exception as e:
                return f"Error updating preference: {e}"
        
        # B. Domain Knowledge -> Router -> Partitioned File
        else:
            # Determine target file based on True Partitioning
            target_file = KnowledgeRouter.get_target_file(effective_scope, category)
            if not target_file.parent.exists():
                target_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 使用锁保护知识库读写 (Future: atomic db transaction)
            async with LockManager.async_knowledge_lock():
                items = []
                if target_file.exists():
                    try:
                        async with aiofiles.open(target_file, mode='r', encoding='utf-8') as f:
                            content = await f.read()
                            items = json.loads(content)
                    except Exception:
                        items = []
                
                # Logic: Supersedes
                supersedes_id = atomic_fact.get("supersedes_id") or atomic_fact.get("supersededBy")
                
                if "id" not in atomic_fact:
                    atomic_fact["id"] = f"fact-{uuid.uuid4().hex[:8]}"
                
                atomic_fact["timestamp"] = now.isoformat()
                atomic_fact["status"] = "active"
                atomic_fact["scope"] = effective_scope
                
                if supersedes_id:
                    # In partitioned world, the old fact might be in ANOTHER file.
                    # This is complex. For v0.6.0, we assume same file or search all.
                    # Implementing simple same-file check first.
                    updated_count = 0
                    for item in items:
                        if item.get("id") == supersedes_id and item.get("status") == "active":
                            item["status"] = "superseded"
                            item["supersededBy"] = atomic_fact["id"]
                            updated_count += 1
                    
                    if updated_count == 0:
                        # Fallback: Warning, cross-partition superseding not fully supported in simple mode
                        pass 

                items.append(atomic_fact)
                
                async with aiofiles.open(target_file, mode='w', encoding='utf-8') as f:
                     await f.write(json.dumps(items, indent=2, ensure_ascii=False))
            
            return f"Added Atomic Fact {atomic_fact['id']} to {target_file}"

    return "No content or fact provided."




@mcp.tool()
async def query_knowledge(
    query: Optional[str] = None,
    scope: Optional[str] = None, 
    category: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
) -> str:
    """
    **知识库查询** - 从知识图谱中检索已保存的知识条目。
    
    ## 使用场景
    - 用户问 "我的偏好是什么？"（查询 user_preference）
    - 用户问 "之前记录的技术规范有哪些？"（查询 domain_knowledge）
    - 在特定项目中工作时，查询该项目的专属配置
    
    ## 参数说明
    
    ### scope (作用域过滤)
    - `None`: 返回全局知识 + 当前项目的知识
    - `'global'`: 仅返回全局知识
    - `'project:my-app'`: 仅返回该项目的专属知识 + 全局知识
    
    ### category (分类过滤)
    - `'domain_knowledge'`: 技术规范、API 用法、最佳实践
    - `'user_preference'`: 用户偏好、习惯、风格
    - `None`: 返回所有分类
    
    ### limit (分页)
    - 最大返回数量，默认 20
    
    ### offset (分页)
    - 跳过前 N 条结果，默认 0
    
    ## 返回格式
    每条知识显示：作用域标签（如有）、知识内容、ID
    
    ## 与 append_daily_log 的关系
    - `append_daily_log` 写入知识
    - `query_knowledge` 读取知识
    """
    from ..vector_store import get_vector_store
    from ..services.embedding import EmbeddingService
    from ..indexer import indexer
    
    # Lazy deferred indexing (avoids circular import with server.py)
    if not getattr(indexer, '_has_run_initial', False):
        try:
            await indexer.build_index()
            indexer._has_run_initial = True
        except Exception:
            pass
    
    # --- Mode 1: Search (Hybrid) ---
    if query:
        store = get_vector_store()
        results = []
        
        # A. Hybrid Search if available
        if store.available: # and store.count() > 0? No, rely on try-catch or count check.
             try:
                # 1. Vector Search
                service = EmbeddingService.get_instance()
                query_vec = await service.embed_query(query)
                vec_results = await store.async_search(query_vec, top_k=config.search_top_k)
                
                # 2. FTS Search
                fts_results = await store.async_fulltext_search(query, limit=config.search_top_k)
                
                # 3. RRF Fusion
                # Map id -> score
                rrf_scores = {}
                k = config.rrf_k
                
                # Process Vector
                for rank, res in enumerate(vec_results):
                    # Filter first
                    meta = res.metadata
                    if scope and scope != "global" and meta.get("scope") not in ["global", scope]:
                        continue
                    if category and meta.get("category") != category:
                        continue
                        
                    rrf_scores[res.id] = rrf_scores.get(res.id, 0) + (1 / (k + rank + 1))
                    
                # Process FTS
                for rank, res in enumerate(fts_results):
                    meta = res.metadata
                    if scope and scope != "global" and meta.get("scope") not in ["global", scope]:
                        continue
                    if category and meta.get("category") != category:
                         continue
                         
                    rrf_scores[res.id] = rrf_scores.get(res.id, 0) + (1 / (k + rank + 1))
                
                # Sort
                sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
                
                # Retrieve content? The search results have content.
                # Need a map to lookup content/metadata
                content_map = {r.id: r for r in vec_results + fts_results}
                
                final_results = []
                for doc_id in sorted_ids:
                    res = content_map[doc_id]
                    # Format
                    snippet = getattr(res, 'snippet', None)
                    if snippet:
                         text = f"{res.content[:80]}... (Match: {snippet})"
                    else:
                         text = res.content[:200]
                    
                    final_results.append({
                        "id": doc_id,
                        "content": text,
                        "metadata": res.metadata,
                        "score": rrf_scores[doc_id]
                    })
                    
                results = final_results
                
                # --- 4. Reranking (Phase 12) ---
                try:
                    from ..services.rerank import RerankService
                    reranker = RerankService.get_instance()
                    
                    if reranker and results:
                        # Extract content
                        docs_content = [item['content'] for item in results]
                        # Call API
                        reranked = await reranker.rerank(query, docs_content, top_n=len(results))
                        
                        # Re-order
                        new_results = []
                        for rr in reranked:
                            if rr.index < len(results):
                                item = results[rr.index]
                                item['score'] = rr.relevance_score
                                item['reranked'] = True
                                new_results.append(item)
                        
                        if new_results:
                            results = new_results
                except Exception as e:
                    # Fallback to RRF, just log warning
                    import logging
                    logging.getLogger("adaptive-agent-mcp").warning(f"Reranking failed: {e}")
                
             except Exception as e:
                # Log error and fall back?
                # If Embedding fails, fall back to pure FTS? or text scan?
                # Fallback to Text Scan via Search
                pass
        
        # B. Return hybrid results if found, otherwise fall through to Browse Mode
        
        if results:
             output = []
             for item in results[:limit]:
                 meta = item["metadata"]
                 s = meta.get('scope', 'global')
                 scope_tag = f"[{s}]" if s != 'global' else ""
                 output.append(f"- {scope_tag} {item['content']} (id: {item['id']})")
             
             return "\n".join(output)
        
        # Hybrid Search empty or unavailable → fall through to Browse Mode with query substring filter

    # --- Mode 2: Browse (Legacy/Filter) ---
    
    # Identify files to search
    files_to_search = []
    
    if query and not scope:
        # If searching (fallback) without scope, search ALL partitions
        files_to_search = KnowledgeRouter.get_all_partition_files()
    else:
        # Default behavior: Global + Scope
        files_to_search.append(KnowledgeRouter.get_target_file("global"))
        
        if scope:
            if scope != "global":
                specific_file = KnowledgeRouter.get_target_file(scope)
                if specific_file not in files_to_search:
                    files_to_search.append(specific_file)
                if scope.startswith("project:"):
                     coding_file = KnowledgeRouter.get_target_file("app:coding")
                     if coding_file not in files_to_search:
                         files_to_search.append(coding_file)

    all_items = []
    
    # Parallel partition read via asyncio.gather
    async def _read_partition(p: Path) -> list:
        if not p.exists():
            return []
        try:
            async with aiofiles.open(p, mode='r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except Exception:
            return []
    
    partition_results = await asyncio.gather(*[_read_partition(p) for p in files_to_search])
    for items in partition_results:
        all_items.extend(items)

    # Filter
    active_items = [i for i in all_items if i.get("status") == "active"]
    
    if category:
        active_items = [i for i in active_items if i.get("category") == category]
    
    if query:
        # Fallback substring search
        q_lower = query.lower()
        active_items = [i for i in active_items if q_lower in i.get("fact", "").lower()]

    # Deduplicate
    seen_ids = set()
    unique_items = []
    for item in active_items:
        if item["id"] not in seen_ids:
            unique_items.append(item)
            seen_ids.add(item["id"])
            
    total_count = len(unique_items)
    if not unique_items:
        return "No matching knowledge found."
        
    paginated_items = unique_items[offset:offset + limit]
    
    output = []
    for item in paginated_items:
        s = item.get('scope', 'global')
        scope_tag = f"[{s}]" if s != 'global' else ""
        output.append(f"- {scope_tag} {item.get('fact')} (id: {item.get('id')})")
    
    showing_end = min(offset + limit, total_count)
    output.append(f"\n--- 显示 {offset + 1}-{showing_end} / {total_count} 条 ---")
    
    return "\n".join(output)


@mcp.tool()
async def get_period_context(period: str, date: Optional[str] = None) -> str:
    """
    **周期索引** - 获取指定时间段的日志摘要和文件索引，用于生成周报/月报。
    
    ## 使用场景
    当用户说：
    - "帮我写一份周报"
    - "总结一下这个月做了什么"
    - "回顾上周的工作"
    
    ## 工作流程
    1. 调用 `get_period_context(period='week')` 获取索引
    2. 阅读摘要，了解每天的概况
    3. 如需详细内容，调用 `read_memory_content` 按需加载
    4. 撰写总结报告
    5. 调用 `archive_period` 保存总结
    
    ## 参数说明
    - `period`: 时间周期，`'week'` 或 `'month'`
    - `date`: 可选，指定日期 (格式 YYYY-MM-DD)，默认为今天
    
    ## 返回格式
    返回简短摘要 + 文件路径索引，不返回完整内容：
    ```
    📅 2026-02-03 | 3 entries | path/to/file.md
       摘要: 完成了用户认证模块...
    ```
    
    ## 按需加载
    对于需要详细了解的日期，使用返回的文件路径调用 `read_memory_content`
    """
    from datetime import timedelta
    import re
    
    # Date calc logic (CPU bound, keep sync or wrap? It's fast)
    target_date = datetime.now()
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        except Exception:
            return f"Error: Invalid date format {date}. Use YYYY-MM-DD"
    
    start_date = target_date
    end_date = target_date
    
    if period == "week":
        start_date = target_date - timedelta(days=target_date.weekday())
        end_date = start_date + timedelta(days=6)
    elif period == "month":
        start_date = target_date.replace(day=1)
        if start_date.month == 12:
            next_month = start_date.replace(year=start_date.year+1, month=1)
        else:
            next_month = start_date.replace(month=start_date.month+1)
        end_date = next_month - timedelta(days=1)
    
    index_parts = []
    index_parts.append(f"# {period.upper()} 概览")
    index_parts.append(f"**时间范围**: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
    index_parts.append("")
    
    file_paths = []
    current = start_date
    while current <= end_date:
        log_path = StorageValidation.get_daily_log_path(current)
        if log_path.exists():
            # Async Read
            async with aiofiles.open(log_path, mode='r', encoding='utf-8') as f:
                content = await f.read()
            
            entry_count = len(re.findall(r'^### \d{2}:\d{2}', content, re.MULTILINE))
            content_body = re.sub(r'^---.*?---\s*', '', content, flags=re.DOTALL)
            summary = content_body.strip()[:100].replace('\n', ' ')
            if len(content_body) > 100:
                summary += "..."
            
            index_parts.append(f"📅 **{current.strftime('%Y-%m-%d')}** | {entry_count} entries")
            index_parts.append(f"   📄 `{log_path}`")
            index_parts.append(f"   摘要: {summary}")
            index_parts.append("")
            file_paths.append(str(log_path))
        
        current += timedelta(days=1)
    
    if not file_paths:
        return "No logs found for this period."
    
    index_parts.append("---")
    index_parts.append(f"**共 {len(file_paths)} 个日志文件**")
    index_parts.append("如需详细内容，请调用 `read_memory_content` 并传入上述文件路径。")
    
    return "\n".join(index_parts)



@mcp.tool()
async def archive_period(
    summary_content: str,
    period: str
) -> str:
    """
    **保存周期总结** - 将撰写好的周报/月报保存到永久文件。
    
    ## 使用场景
    在使用 `get_period_context` 获取数据并撰写总结后，调用此工具保存。
    
    ## 工作流程
    1. `get_period_context(period='week')` - 获取原始数据
    2. 阅读数据，撰写精炼总结
    3. `archive_period(summary_content='...', period='week')` - 保存
    
    ## 参数说明
    - `summary_content`: 你撰写的总结内容 (Markdown 格式)
    - `period`: 时间周期，`'week'` 或 `'month'`
    
    ## 保存位置
    文件保存到: `memory/{period}_summary_{date}.md`
    
    ## 总结建议格式
    ```markdown
    # 周报 2026-02-06
    
    ## 完成事项
    - 事项 1
    - 事项 2
    
    ## 遇到的问题
    - 问题及解决方案
    
    ## 下周计划
    - 待办事项
    ```
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    filename = f"{period}_summary_{date_str}.md"
    
    # Save to memory root
    target_path = config.storage_path / "memory" / filename
    
    header = f"---\ntype: period_summary\nperiod: {period}\ndate: {date_str}\n---\n\n"
    full_content = header + summary_content
    
    await StorageValidation.async_append_to_file(target_path, full_content)
    
    # Trigger re-index
    asyncio.create_task(indexer.build_index())
    
    return f"✓ Saved {period} summary to {target_path}"


async def _log_audit(action: str, target_id: str, details: Dict[str, Any] = None):
    """
    Log an audit event to memory/audit.log
    """
    now = datetime.now()
    log_path = config.storage_path / "memory" / "audit.log"
    
    entry = {
        "timestamp": now.isoformat(),
        "action": action,
        "target_id": target_id,
        "details": details or {}
    }
    
    # Async append
    await StorageValidation.async_append_to_file(log_path, json.dumps(entry, ensure_ascii=False) + "\n")


@mcp.tool()
async def delete_knowledge(
    id: str,
    reason: Optional[str] = None
) -> str:
    """
    [DANGER] **删除知识** - 物理删除指定的知识条目。
    
    ## 使用场景
    - 用户明确要求删除某条错误或过时的信息
    - 清理被标记为 [DEPRECATED] 且不再需要的条目
    - 隐私数据清除
    
    ## 参数
    - `id`: 知识条目的唯一 ID (如 "fact-12345678")
    - `reason`: (可选) 删除原因，仅用于日志记录
    
    ## 注意
    - 此操作不可逆！
    - 删除后会触发索引重建（如适用）
    """
    # Search ALL partitions
    all_files = KnowledgeRouter.get_all_partition_files()
    
    target_file = None
    target_item = None
    
    # Scan files
    for p in all_files:
        try:
            async with aiofiles.open(p, mode='r', encoding='utf-8') as f:
                content = await f.read()
                items = json.loads(content)
        except Exception:
            continue
            
        for item in items:
            if item.get("id") == id:
                if item.get("status") == "deleted":
                     return f"Item '{id}' is already deleted."
                target_file = p
                target_item = item
                break
        
        if target_file:
            break
            
    if not target_file:
        return f"Error: Knowledge item with ID '{id}' not found."
        
    async with LockManager.async_knowledge_lock():
        # Re-read for safety
        try:
            async with aiofiles.open(target_file, mode='r', encoding='utf-8') as f:
                 content = await f.read()
                 items = json.loads(content)
        except Exception:
             return "Error re-reading file."
             
        # Find index again
        idx = -1
        for i, item in enumerate(items):
            if item.get("id") == id:
                idx = i
                break
        
        if idx == -1:
            return "Error: Item disappeared."
            
        # Soft Delete
        items[idx]["status"] = "deleted"
        items[idx]["deletedAt"] = datetime.now().isoformat()
        if reason:
            items[idx]["deleteReason"] = reason
            
        async with aiofiles.open(target_file, mode='w', encoding='utf-8') as f:
            await f.write(json.dumps(items, indent=2, ensure_ascii=False))
            
    # Audit Log
    await _log_audit("delete_knowledge", id, {"reason": reason, "file": str(target_file)})
            
    return f"✓ Successfully deleted '{id}' (Soft Delete) from {target_file.name}"

