import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List
from .config import config

# Regex to capture YAML frontmatter
YAML_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL | re.MULTILINE)

class Indexer:
    def __init__(self):
        pass

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
        """Simple YAML parser for frontmatter (avoiding heavy PyYAML for speed if possible, but we utilize yaml here since installed)."""
        import yaml
        try:
            return yaml.safe_load(raw_yaml) or {}
        except:
            return {}

    def build_index(self) -> Dict[str, Any]:
        """Scans all .md files in memory/ and rebuilds the index."""
        index_data = {}
        
        if not self.memory_dir.exists():
            return index_data

        for root, _, files in os.walk(self.memory_dir):
            for file in files:
                if not file.endswith(".md"): continue
                
                path = Path(root) / file
                rel_path = str(path.relative_to(self.memory_dir)).replace("\\", "/") # Normalize to forward slashes
                
                try:
                    # Read header only
                    with open(path, "r", encoding="utf-8") as f:
                        chunk = f.read(1000) # Read enough for frontmatter
                    
                    match = YAML_FRONTMATTER_RE.match(chunk)
                    if match:
                        frontmatter_raw = match.group(1)
                        metadata = self._parse_yaml(frontmatter_raw)
                        
                        # Store lightweight metadata
                        index_data[rel_path] = {
                            "date": metadata.get("date"),
                            "tags": metadata.get("tags", []),
                            "summary": metadata.get("summary", ""),
                            "type": metadata.get("type", "unknown")
                        }
                except Exception as e:
                    print(f"Error indexing {rel_path}: {e}")
                    continue
        
        # Atomic Write
        self._save_index(index_data)
        return index_data

    def _save_index(self, data: Dict[str, Any]):
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_index(self) -> Dict[str, Any]:
        if not self.index_file.exists():
            return self.build_index()
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return self.build_index()

# Global instance
indexer = Indexer()
