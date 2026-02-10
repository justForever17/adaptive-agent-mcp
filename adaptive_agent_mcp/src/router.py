
from pathlib import Path
from typing import Dict, Any, Optional
from .config import config

class KnowledgeRouter:
    """
    Knowledge Router - Routes knowledge items to specific files based on scope/category.
    Realizes "True Partitioning".
    """
    
    @staticmethod
    def get_target_file(scope: str, category: str = "general") -> Path:
        """
        Determine the target file path based on scope and category.
        
        Routing Logic:
        1. project:{name} -> knowledge/areas/projects/{name}/items.json
        2. app:chat        -> knowledge/areas/chat/items.json
        3. app:coding      -> knowledge/areas/coding/items.json
        4. app:writing     -> knowledge/areas/writing/items.json
        5. global          -> knowledge/areas/general/items.json
        6. * (fallback)    -> knowledge/areas/general/items.json
        """
        base_dir = config.storage_path / "knowledge" / "areas"
        
        if scope.startswith("project:"):
            project_name = scope.split(":", 1)[1]
            # Sanitize project name to avoid path traversal
            project_name = "".join([c for c in project_name if c.isalnum() or c in "-_"])
            return base_dir / "projects" / project_name / "items.json"
            
        elif scope == "app:chat":
            return base_dir / "chat" / "items.json"
            
        elif scope == "app:coding":
            return base_dir / "coding" / "items.json"
            
        elif scope == "app:writing":
            return base_dir / "writing" / "items.json"
            
        # Default / Global
        return base_dir / "general" / "items.json"

    @staticmethod
    def get_all_partition_files() -> list[Path]:
        """
        Get all known partition files (for search/indexing).
        """
        base_dir = config.storage_path / "knowledge" / "areas"
        files = []
        
        # 1. General, Coding, Writing
        for area in ["general", "chat", "coding", "writing"]:
            p = base_dir / area / "items.json"
            if p.exists():
                files.append(p)
                
        # 2. Projects
        projects_dir = base_dir / "projects"
        if projects_dir.exists():
            for project_dir in projects_dir.iterdir():
                if project_dir.is_dir():
                    p = project_dir / "items.json"
                    if p.exists():
                        files.append(p)
                        
        return files
