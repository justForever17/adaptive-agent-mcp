from typing import List, Optional, Any, Dict
from datetime import datetime
import json
import uuid
from ...server import mcp
from ..config import config
from ..storage import StorageValidation
from ..indexer import indexer
from ..memory_parser import MemoryParser
from ..lock_manager import LockManager

@mcp.tool()
def update_preference(
    key: str,
    value: str,
    scope: str = "global"
) -> str:
    """
    **智能更新用户偏好** - 自动覆盖同 key 的旧值，保持格式整洁。
    
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
    
    ## 常用 key 值
    - `communication_style`: 交流风格 (如 "年轻女性、卖萌撒娇" 或 "专业严谨")
    - `use_kaomoji`: 是否使用颜文字 (true/false)
    - `language`: 语言偏好 (zh-CN, en-US)
    - `code_style`: 代码风格偏好
    - `css_framework`: CSS 框架偏好
    
    ## 示例
    ```python
    # 闲聊时要卖萌
    update_preference("communication_style", "年轻女性、卖萌撒娇", "app:chat")
    
    # 写代码时要严谨
    update_preference("communication_style", "专业严谨", "app:coding")
    
    # 全局使用颜文字
    update_preference("use_kaomoji", "true", "global")
    ```
    """
    try:
        memory = MemoryParser().load()
        memory.set(key, value, scope)
        saved_path = memory.save()
        return f"✓ 已保存偏好 `{key}` = `{value}` 到 [{scope}] (文件: {saved_path})"
    except Exception as e:
        return f"Error updating preference: {e}"


@mcp.tool()
def append_daily_log(
    content: Optional[str] = None, 
    atomic_fact: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
    scope: Optional[str] = None
) -> str:
    """
    **写入记忆** - 当需要保存信息时调用此工具。
    
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
    
    **注意**: 不要询问日期，系统自动记录时间戳。
    """
    now = datetime.now()
    
    # 1. Handle Daily Log (Ephemeral)
    if content:
        log_path = StorageValidation.get_daily_log_path(now)
        # Create header if new file
        if not log_path.exists() or log_path.stat().st_size == 0:
            header_tags = str(tags) if tags else "[]"
            header = f"---\ntype: daily_log\ndate: \"{now.strftime('%Y-%m-%d')}\"\ntags: {header_tags}\n---\n\n"
            StorageValidation.append_to_file(log_path, header)
            
        time_str = now.strftime("%H:%M")
        entry = f"### {time_str}\n{content}"
        StorageValidation.append_to_file(log_path, entry)
        # Trigger Re-index
        indexer.build_index()
        return f"Appended log to {log_path}"

    # 2. Handle Knowledge Graph (Atomic Fact)
    if atomic_fact:
        # Validate atomic_fact structure
        fact_content = atomic_fact.get("fact")
        if not fact_content or not isinstance(fact_content, str):
            return "Error: atomic_fact must contain a non-empty 'fact' string field."
        
        category = atomic_fact.get("category", "general")
        
        # 对于 user_preference，使用新的 MemoryParser
        if category == "user_preference":
            try:
                memory = MemoryParser().load()
                # 尝试从 fact 中提取 key-value
                # 格式可能是 "用户喜欢使用 Tailwind CSS" → key=css_preference, value=Tailwind CSS
                # 或者直接作为 note 存储
                effective_scope = scope or "global"
                
                # 简单的 key 推断逻辑
                if "喜欢" in fact_content or "偏好" in fact_content:
                    key = "preference_note"
                elif "风格" in fact_content:
                    key = "style_note"
                else:
                    key = "user_note"
                
                # 添加时间戳使 key 唯一
                key = f"{key}_{now.strftime('%H%M%S')}"
                memory.set(key, fact_content, effective_scope)
                memory.save()
                return f"Updated User Preference in MEMORY.md [{effective_scope}]"
            except Exception as e:
                return f"Error updating preference: {e}"
        
        else: # Domain Knowledge
            target_dir = config.storage_path / "knowledge" / "areas" / "general"
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / "items.json"
            
            # 使用锁保护知识库读写
            with LockManager.knowledge_lock():
                # Load existing items
                items = []
                if target_file.exists():
                    try:
                        items = json.loads(target_file.read_text(encoding="utf-8"))
                    except Exception:
                        items = []
                
                # Knowledge Evolution Logic
                supersedes_id = atomic_fact.get("supersedes_id") or atomic_fact.get("supersededBy")
                
                # Generate ID if missing
                if "id" not in atomic_fact:
                    atomic_fact["id"] = f"fact-{uuid.uuid4().hex[:8]}"
                
                atomic_fact["timestamp"] = now.isoformat()
                atomic_fact["status"] = "active"
                atomic_fact["scope"] = scope or "global"  # Default to global
                
                if supersedes_id:
                    # Mark old item as superseded
                    updated_count = 0
                    for item in items:
                        if item.get("id") == supersedes_id and item.get("status") == "active":
                            item["status"] = "superseded"
                            item["supersededBy"] = atomic_fact["id"]
                            updated_count += 1
                    if updated_count == 0:
                        return f"Warning: Could not find active fact with ID {supersedes_id} to supersede."
                
                items.append(atomic_fact)
                
                target_file.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
            
            return f"Added Atomic Fact {atomic_fact['id']} (scope: {atomic_fact['scope']}) to {target_file}"

    return "No content or fact provided."


@mcp.tool()
def query_knowledge(
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
    target_file = config.storage_path / "knowledge" / "areas" / "general" / "items.json"
    
    if not target_file.exists():
        return "No knowledge base found."
    
    try:
        items = json.loads(target_file.read_text(encoding="utf-8"))
    except Exception:
        return "Error reading knowledge base."
    
    # Filter by status
    active_items = [i for i in items if i.get("status") == "active"]
    
    # Filter by scope
    if scope:
        if scope == "global":
            active_items = [i for i in active_items if i.get("scope", "global") == "global"]
        else:
            # Include global + specific scope
            active_items = [i for i in active_items if i.get("scope", "global") in ["global", scope]]
    
    # Filter by category
    if category:
        active_items = [i for i in active_items if i.get("category") == category]
    
    total_count = len(active_items)
    
    if not active_items:
        return "No matching knowledge found."
    
    # Apply pagination
    paginated_items = active_items[offset:offset + limit]
    
    # Format output
    output = []
    for item in paginated_items:
        scope_tag = f"[{item.get('scope', 'global')}]" if item.get('scope') != 'global' else ""
        output.append(f"- {scope_tag} {item.get('fact')} (id: {item.get('id')})")
    
    # Add pagination info
    showing_end = min(offset + limit, total_count)
    output.append(f"\n--- 显示 {offset + 1}-{showing_end} / {total_count} 条 ---")
    
    return "\n".join(output)

@mcp.tool()
def get_period_context(period: str, date: Optional[str] = None) -> str:
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
    else:
        return "Error: Period must be 'week' or 'month'"
    
    # Build index with summaries
    index_parts = []
    index_parts.append(f"# {period.upper()} 概览")
    index_parts.append(f"**时间范围**: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
    index_parts.append("")
    
    file_paths = []
    current = start_date
    while current <= end_date:
        log_path = StorageValidation.get_daily_log_path(current)
        if log_path.exists():
            content = log_path.read_text(encoding="utf-8")
            
            # Count entries (### HH:MM headers)
            entry_count = len(re.findall(r'^### \d{2}:\d{2}', content, re.MULTILINE))
            
            # Extract first 100 chars of actual content (skip YAML header)
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
def archive_period(summary_content: str, period: str) -> str:
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
    path = config.storage_path / "memory" / f"{period}_summary_{now.strftime('%Y-%m-%d')}.md"
    path.write_text(summary_content, encoding="utf-8")
    return f"Archived {period} summary to {path}"

