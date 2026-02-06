import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from .config import config

# Regex to capture YAML frontmatter
YAML_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL | re.MULTILINE)

class Indexer:
    """
    增量索引器 - 仅对变化的文件进行重新索引
    
    索引结构:
    {
        "metadata": {"last_build": 时间戳, "version": "2.0"},
        "files": {
            "path": {"date": ..., "tags": ..., "mtime": 修改时间戳}
        }
    }
    """
    
    INDEX_VERSION = "2.0"
    
    def __init__(self):
        self._cached_index: Optional[Dict[str, Any]] = None

    @property
    def root(self) -> Path:
        return config.storage_path

    @property
    def memory_dir(self) -> Path:
        return self.root / "memory"

    @property
    def index_file(self) -> Path:
        return self.root / ".index" / "memory_index.json"

    def _parse_yaml(self, raw_yaml: str) -> Dict[str, Any]:
        """Simple YAML parser for frontmatter."""
        import yaml
        try:
            return yaml.safe_load(raw_yaml) or {}
        except:
            return {}

    def _get_file_mtime(self, path: Path) -> float:
        """获取文件修改时间戳"""
        try:
            return path.stat().st_mtime
        except:
            return 0.0

    def build_index(self, force_full: bool = False) -> Dict[str, Any]:
        """
        构建索引（增量模式）
        
        Args:
            force_full: 如果为 True，强制全量重建
        
        Returns:
            完整的索引数据
        """
        # 加载现有索引
        existing_index = self._load_raw_index() if not force_full else None
        existing_files = existing_index.get("files", {}) if existing_index else {}
        
        # 检查索引版本
        if existing_index and existing_index.get("metadata", {}).get("version") != self.INDEX_VERSION:
            print(f"索引版本不匹配，强制全量重建")
            existing_files = {}
        
        new_files_data = {}
        files_updated = 0
        files_skipped = 0
        
        if not self.memory_dir.exists():
            self._save_index({"metadata": self._build_metadata(), "files": {}})
            return {}

        # 收集所有当前存在的文件路径
        current_file_paths = set()
        
        for root, _, files in os.walk(self.memory_dir):
            for file in files:
                if not file.endswith(".md"):
                    continue
                
                path = Path(root) / file
                rel_path = str(path.relative_to(self.memory_dir)).replace("\\", "/")
                current_file_paths.add(rel_path)
                
                current_mtime = self._get_file_mtime(path)
                
                # 检查是否需要重新索引
                if rel_path in existing_files:
                    cached_mtime = existing_files[rel_path].get("mtime", 0)
                    if cached_mtime >= current_mtime:
                        # 文件未修改，复用缓存
                        new_files_data[rel_path] = existing_files[rel_path]
                        files_skipped += 1
                        continue
                
                # 需要重新索引此文件
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        chunk = f.read(1000)
                    
                    match = YAML_FRONTMATTER_RE.match(chunk)
                    if match:
                        frontmatter_raw = match.group(1)
                        metadata = self._parse_yaml(frontmatter_raw)
                        
                        new_files_data[rel_path] = {
                            "date": metadata.get("date"),
                            "tags": metadata.get("tags", []),
                            "summary": metadata.get("summary", ""),
                            "type": metadata.get("type", "unknown"),
                            "mtime": current_mtime
                        }
                        files_updated += 1
                    else:
                        # 没有 frontmatter，只记录基本信息
                        new_files_data[rel_path] = {
                            "date": None,
                            "tags": [],
                            "summary": "",
                            "type": "plain",
                            "mtime": current_mtime
                        }
                        files_updated += 1
                        
                except Exception as e:
                    print(f"Error indexing {rel_path}: {e}")
                    continue
        
        # 构建最终索引
        final_index = {
            "metadata": self._build_metadata(),
            "files": new_files_data
        }
        
        # 原子写入
        self._save_index(final_index)
        
        print(f"索引完成: {files_updated} 更新, {files_skipped} 跳过")
        
        return new_files_data

    def _build_metadata(self) -> Dict[str, Any]:
        """构建索引元数据"""
        import time
        return {
            "last_build": time.time(),
            "version": self.INDEX_VERSION
        }

    def _load_raw_index(self) -> Optional[Dict[str, Any]]:
        """加载原始索引文件"""
        if not self.index_file.exists():
            return None
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return None

    def _save_index(self, data: Dict[str, Any]):
        """原子写入索引"""
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self._cached_index = data

    def load_index(self) -> Dict[str, Any]:
        """加载索引（仅返回 files 部分，保持向后兼容）"""
        if self._cached_index:
            return self._cached_index.get("files", {})
        
        raw = self._load_raw_index()
        if raw and "files" in raw:
            self._cached_index = raw
            return raw["files"]
        
        # 索引不存在或格式错误，重建
        return self.build_index()

# Global instance
indexer = Indexer()

