from datetime import datetime, timedelta
from pathlib import Path
from ...server import mcp
from ..config import config
from ..storage import StorageValidation
from ..memory_parser import MemoryParser

@mcp.tool()
def initialize_session() -> str:
    """
    🔴 **必须首先调用** - 每次对话开始时调用此工具初始化会话。
    
    ## 返回内容
    1. **系统时间**: 真实的当前日期时间 (防止时间幻觉)
    2. **用户画像**: 用户的偏好和习惯 (按 Scope 分区显示)
    3. **近期上下文**: 最近 2 天的日志摘要
    
    ## Agent 工作流指南
    
    ### 读取记忆 (何时查询)
    - 用户问"之前讨论过...", "上次...", "我们说过..." → 先调用 `query_memory_headers`
    - 用户问"我的偏好是...", "我喜欢什么..." → 已在 initialize_session 返回
    - 需要特定文件内容 → 调用 `read_memory_content`
    
    ### 搜索记忆 (何时搜索)
    - 用户问"有没有提到过 X", "关于 Y 的记录" → 调用 `search_memory_content`
    - 需要查找错误码、特定技术术语 → 调用 `search_memory_content`
    
    ### 写入记忆 (何时保存)
    - 用户说"记住", "保存", "别忘了" → 调用 `update_preference` 或 `append_daily_log`
    - 用户表达偏好"我喜欢...", "以后都用..." → 调用 `update_preference`
    - 任务完成时 → 主动记录进度到 `append_daily_log`
    - 解决问题后 → 记录解决方案
    
    ## Scope 使用指南 (语义理解驱动)
    
    请根据**对话意图**自动选择合适的 Scope，无需用户明确说明：
    
    | 对话意图 | 应使用的 Scope | 判断依据 |
    |---------|---------------|---------|
    | 闲聊、情感交流、日常对话 | `app:chat` | 非任务导向、轻松氛围 |
    | 写代码、调试、技术讨论 | `app:coding` | 涉及代码/技术 |
    | 写文档、翻译、文案创作 | `app:writing` | 内容创作类 |
    | 在某个项目中工作 | `project:{项目名}` | 从工作目录推断 |
    | 无法判断 | `global` | 回退到全局 |
    
    **查询偏好时**：根据当前对话意图，优先使用对应 scope 的偏好。
    **写入偏好时**：根据用户表达的上下文，推断应保存到哪个 scope。
    
    **重要**: 不确定是否需要记录时，宁可多记录也不要遗漏！
    """
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    
    # 1. 加载用户偏好 (使用新的解析器)
    try:
        memory = MemoryParser().load()
        preferences_display = memory.format_for_display()
        scopes_available = memory.get_all_scopes()
    except Exception as e:
        preferences_display = f"Error loading preferences: {e}"
        scopes_available = ["global"]

    # 2. 检测当前工作目录 (用于推断 project scope)
    try:
        cwd = Path.cwd()
        if (cwd / ".git").exists():
            detected_scope = f"project:{cwd.name}"
        else:
            detected_scope = "global"
    except Exception:
        cwd = Path(".")
        detected_scope = "global"

    # 3. 获取最近日志 (Last 2 days)
    recent_logs = []
    for i in range(2):
        date_check = now - timedelta(days=i)
        log_path = StorageValidation.get_daily_log_path(date_check)
        if log_path.exists():
            log_content = log_path.read_text(encoding="utf-8")
            # 限制长度，只显示摘要
            if len(log_content) > 500:
                log_content = log_content[:500] + "\n...(truncated)"
            recent_logs.append(f"### Log: {date_check.strftime('%Y-%m-%d')}\n{log_content}")
    
    recent_context = "\n\n".join(recent_logs) if recent_logs else "No recent logs found."

    return f"""# Session Initialized
**System Time**: {today_str}
**Current Working Directory**: {cwd}
**Detected Scope**: {detected_scope}
**Available Scopes**: {', '.join(scopes_available)}

---

## Scope 使用指南

根据对话**意图**自动选择偏好：
- 闲聊/情感交流 → 使用 `[app:chat]` 区块的偏好
- 代码/技术任务 → 使用 `[app:coding]` 区块的偏好
- 当前工作目录有 .git → 使用 `[project:{{dir_name}}]` 区块
- 无法判断 → 使用 `[global]` 区块

---

## User Preferences (按 Scope 分区)

{preferences_display}

---

## Recent Context (Last 48h)

{recent_context}
"""
