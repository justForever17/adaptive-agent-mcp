from pathlib import Path
from datetime import datetime
import yaml
import shutil
from .config import config

# v2.0 格式模板，支持 Scope 分区
MEMORY_TEMPLATE = """---
type: user_preferences
version: "2.0"
last_updated: "{date}"
---

[global]
# 全局偏好 - 适用于所有场景
language: zh-CN

[app:chat]
# 聊天场景偏好 - Agent 判断为闲聊时使用
communication_style: 友好、热情

[app:coding]
# 编程场景偏好 - Agent 判断为技术任务时使用
communication_style: 专业、严谨
"""

class StorageValidation:
    @staticmethod
    def initialize_storage():
        """Ensure the storage directory structure exists."""
        root = config.storage_path
        if not root.exists():
            print(f"Initializing memory storage at: {root}")
            root.mkdir(parents=True, exist_ok=True)
        
        # Create standard subdirectories
        (root / "memory").mkdir(exist_ok=True)
        (root / "knowledge").mkdir(exist_ok=True)
        (root / ".index").mkdir(exist_ok=True)
        
        # Create default MEMORY.md if missing
        memory_file = root / "MEMORY.md"
        if not memory_file.exists():
            current_date = datetime.now().strftime("%Y-%m-%d")
            content = MEMORY_TEMPLATE.format(date=current_date)
            memory_file.write_text(content, encoding="utf-8")

    @staticmethod
    def get_daily_log_path(date: datetime) -> Path:
        """Get the path for a daily log file: memory/YYYY/MM_month/week_WW/YYYY-MM-DD.md"""
        year = date.strftime("%Y")
        month_name = date.strftime("%m_%B").lower()
        week_num = date.isocalendar()[1]
        week_str = f"week_{week_num:02d}"
        filename = date.strftime("%Y-%m-%d.md")
        
        # Ensure directory exists
        path = config.storage_path / "memory" / year / month_name / week_str
        path.mkdir(parents=True, exist_ok=True)
        
        return path / filename

    @staticmethod
    def append_to_file(path: Path, content: str):
        """Append content to a file with newline handling."""
        if not path.parent.exists():
             path.parent.mkdir(parents=True, exist_ok=True)
        
        # Decode unicode escape sequences if present (e.g., \u4eca -> 今)
        try:
            if '\\u' in content or '\\n' in content:
                content = content.encode('utf-8').decode('unicode_escape')
        except Exception:
            pass  # Keep original content if decode fails
             
        with open(path, "a", encoding="utf-8") as f:
            if path.exists() and path.stat().st_size > 0:
                f.write("\n\n")
            f.write(content)

    @staticmethod
    def read_file(path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")
