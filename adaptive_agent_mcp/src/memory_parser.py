"""
MEMORY.md 智能解析器 - 支持 Scope 分区的偏好管理系统

格式规范:
---
type: user_preferences
version: "2.0"
---

[global]
language: zh-CN
timezone: Asia/Shanghai

[app:chat]
communication_style: 年轻女性、卖萌撒娇
use_kaomoji: true

[app:coding]
communication_style: 专业严谨
code_style: TypeScript

[project:my-app]
css_framework: vanilla CSS
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import re
from .config import config
from .lock_manager import LockManager


MEMORY_TEMPLATE_V2 = """---
type: user_preferences
version: "2.0"
last_updated: "{date}"
---

[global]
# 全局偏好 - 适用于所有场景
language: zh-CN

[app:chat]
# 聊天场景偏好 - Agent 判断为闲聊时使用
communication_style: 专业、友好

[app:coding]
# 编程场景偏好 - Agent 判断为技术任务时使用
communication_style: 专业、严谨
"""


class MemoryParser:
    """智能 MEMORY.md 解析器，支持 scope 分区读写"""
    
    SCOPE_PATTERN = re.compile(r'^\[([^\]]+)\]$', re.MULTILINE)
    KV_PATTERN = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(.+)$', re.MULTILINE)
    
    def __init__(self, memory_path: Optional[Path] = None):
        self.memory_path = memory_path or (config.storage_path / "MEMORY.md")
        self._data: Dict[str, Dict[str, str]] = {}
        self._frontmatter: Dict[str, Any] = {}
        self._raw_content: str = ""
    
    def load(self) -> "MemoryParser":
        """加载并解析 MEMORY.md"""
        if not self.memory_path.exists():
            self._init_default()
            return self
        
        self._raw_content = self.memory_path.read_text(encoding="utf-8")
        self._parse()
        return self
    
    def _init_default(self):
        """创建默认的 MEMORY.md"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        content = MEMORY_TEMPLATE_V2.format(date=current_date)
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(content, encoding="utf-8")
        self._raw_content = content
        self._parse()
    
    def _parse(self):
        """解析 MEMORY.md 内容"""
        content = self._raw_content
        
        # 1. 提取 YAML frontmatter
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if frontmatter_match:
            try:
                import yaml
                self._frontmatter = yaml.safe_load(frontmatter_match.group(1)) or {}
            except Exception:
                self._frontmatter = {}
            content = content[frontmatter_match.end():]
        
        # 2. 检测是否为 v2.0 格式（带 scope 区块）
        if '[' in content and ']' in content:
            self._parse_v2(content)
        else:
            # 兼容旧格式 v1.x：将所有内容放入 global
            self._parse_v1_legacy(content)
    
    def _parse_v2(self, content: str):
        """解析 v2.0 scope 分区格式"""
        current_scope = "global"
        self._data = {"global": {}}
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            
            # 跳过空行和注释
            if not line or line.startswith('#'):
                continue
            
            # 检测 scope 头
            scope_match = self.SCOPE_PATTERN.match(line)
            if scope_match:
                current_scope = scope_match.group(1)
                if current_scope not in self._data:
                    self._data[current_scope] = {}
                continue
            
            # 解析 key: value
            kv_match = self.KV_PATTERN.match(line)
            if kv_match:
                key = kv_match.group(1)
                value = kv_match.group(2).strip()
                self._data[current_scope][key] = value
    
    def _parse_v1_legacy(self, content: str):
        """兼容解析旧版 v1.x 格式"""
        self._data = {"global": {}}
        
        # 简单提取 - xxx: value 格式
        for match in re.finditer(r'[-*]\s*([^:]+):\s*(.+)', content):
            key = match.group(1).strip().replace(' ', '_').lower()
            value = match.group(2).strip()
            if key and value:
                self._data["global"][key] = value
        
        # 提取列表项作为 notes
        notes = []
        for match in re.finditer(r'^[-*]\s+([^\n:]+)$', content, re.MULTILINE):
            notes.append(match.group(1).strip())
        if notes:
            self._data["global"]["_legacy_notes"] = " | ".join(notes)
    
    def get(self, key: str, scope: str = "global", fallback: bool = True) -> Optional[str]:
        """
        获取偏好值，支持 scope 回退
        
        Args:
            key: 偏好键名
            scope: 作用域，如 "app:chat" 或 "project:my-app"
            fallback: 是否启用回退机制
        
        Returns:
            偏好值，若不存在则返回 None
        """
        # 构建查找顺序
        scopes_to_check = [scope]
        if fallback:
            # project:xxx -> app:coding -> global
            if scope.startswith("project:"):
                scopes_to_check.append("app:coding")
            elif scope.startswith("app:") and scope != "app:chat":
                pass  # app 级别只回退到 global
            scopes_to_check.append("global")
        
        for s in scopes_to_check:
            if s in self._data and key in self._data[s]:
                return self._data[s][key]
        return None
    
    def set(self, key: str, value: str, scope: str = "global") -> "MemoryParser":
        """
        设置偏好值，会覆盖同 scope 下的同名 key
        
        Args:
            key: 偏好键名（英文、下划线）
            value: 偏好值
            scope: 作用域
        """
        if scope not in self._data:
            self._data[scope] = {}
        self._data[scope][key] = value
        return self
    
    def get_scope_data(self, scope: str) -> Dict[str, str]:
        """获取指定 scope 的所有数据"""
        return self._data.get(scope, {}).copy()
    
    def get_all_scopes(self) -> List[str]:
        """获取所有 scope 名称"""
        return list(self._data.keys())
    
    def get_merged_preferences(self, current_scope: str) -> Dict[str, str]:
        """
        获取合并后的偏好（考虑 scope 优先级）
        
        优先级: current_scope > app:xxx > global
        """
        result = {}
        
        # 从低到高优先级合并
        scopes_order = ["global"]
        if current_scope.startswith("project:"):
            scopes_order.append("app:coding")
        if current_scope not in scopes_order:
            scopes_order.append(current_scope)
        
        for scope in scopes_order:
            if scope in self._data:
                result.update(self._data[scope])
        
        return result
    
    def save(self) -> Path:
        """保存到 MEMORY.md (带锁保护)"""
        lines = []
        
        # 1. 写入 frontmatter
        self._frontmatter["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        self._frontmatter["version"] = "2.0"
        self._frontmatter["type"] = "user_preferences"
        
        import yaml
        lines.append("---")
        lines.append(yaml.dump(self._frontmatter, allow_unicode=True, default_flow_style=False).strip())
        lines.append("---")
        lines.append("")
        
        # 2. 按 scope 写入数据（global 优先）
        scope_order = ["global"] + sorted([s for s in self._data.keys() if s != "global"])
        
        scope_comments = {
            "global": "# 全局偏好 - 适用于所有场景",
            "app:chat": "# 聊天场景偏好 - Agent 判断为闲聊时使用",
            "app:coding": "# 编程场景偏好 - Agent 判断为技术任务时使用",
            "app:writing": "# 写作场景偏好 - Agent 判断为内容创作时使用",
        }
        
        for scope in scope_order:
            if scope not in self._data:
                continue
            
            lines.append(f"[{scope}]")
            if scope in scope_comments:
                lines.append(scope_comments[scope])
            elif scope.startswith("project:"):
                project_name = scope.split(":", 1)[1]
                lines.append(f"# 项目 {project_name} 专属偏好")
            
            for key, value in self._data[scope].items():
                if not key.startswith("_"):  # 跳过内部字段
                    lines.append(f"{key}: {value}")
            
            lines.append("")
        
        content = "\n".join(lines)
        
        # 使用锁保护写入
        with LockManager.memory_lock():
            self.memory_path.write_text(content, encoding="utf-8")
        
        return self.memory_path
    
    def format_for_display(self) -> str:
        """格式化输出用于 initialize_session 返回"""
        lines = []
        
        for scope in self.get_all_scopes():
            data = self.get_scope_data(scope)
            if not data:
                continue
            
            lines.append(f"### [{scope}]")
            for key, value in data.items():
                if not key.startswith("_"):
                    lines.append(f"- **{key}**: {value}")
            lines.append("")
        
        return "\n".join(lines) if lines else "暂无用户偏好记录"


# 全局解析器实例
memory_parser = MemoryParser()
