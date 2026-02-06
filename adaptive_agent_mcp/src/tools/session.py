from datetime import datetime, timedelta
from ...server import mcp
from ..config import config
from ..storage import StorageValidation

@mcp.tool()
def initialize_session() -> str:
    """
    🔴 **必须首先调用** - 每次对话开始时调用此工具初始化会话。
    
    ## 返回内容
    1. **系统时间**: 真实的当前日期时间 (防止时间幻觉)
    2. **用户画像**: 用户的偏好和习惯 (来自 MEMORY.md)
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
    - 用户说"记住", "保存", "别忘了" → 调用 `append_daily_log`
    - 用户表达偏好"我喜欢...", "以后都用..." → 调用 `append_daily_log`
    - 任务完成时 → 主动记录进度
    - 解决问题后 → 记录解决方案
    
    **重要**: 不确定是否需要记录时，宁可多记录也不要遗漏！
    """
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    
    # 1. Load User Information (Implicit Knowledge)
    memory_file = config.storage_path / "MEMORY.md"
    user_knowledge = memory_file.read_text(encoding="utf-8") if memory_file.exists() else "No user profile found."

    # 2. Get Recent Logs (Last 2 days)
    recent_logs = []
    for i in range(2):
        date_check = now - timedelta(days=i)
        log_path = StorageValidation.get_daily_log_path(date_check)
        if log_path.exists():
            log_content = log_path.read_text(encoding="utf-8")
            recent_logs.append(f"### Log: {date_check.strftime('%Y-%m-%d')}\n{log_content}")
    
    recent_context = "\n\n".join(recent_logs) if recent_logs else "No recent logs found."

    return f"""
# Session Initialized
**System Time**: {today_str}

## [User Profile & Implicit Knowledge]
{user_knowledge}

## [Recent Context (Last 48h)]
{recent_context}
"""
