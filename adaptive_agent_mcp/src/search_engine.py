import shutil
import subprocess
from typing import List, Dict, Any, Optional
from pathlib import Path
from .config import config

class SearchEngine:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        # Try explicit config first, then PATH
        self.rg_path = config.ripgrep_path or shutil.which("rg")
        
    @property
    def is_available(self) -> bool:
        return self.rg_path is not None

    def search(self, query: str, regex: bool = False, limit: int = 20) -> str:
        """
        Executes ripgrep search.
        Args:
            query: Search term
            regex: If True, treats query as regex pattern. If False, fixed string.
            limit: Max results (not strictly enforced by rg, but we truncate output)
        """
        if not self.is_available:
            return "Error: 'rg' (ripgrep) not found in PATH."

        cmd = [
            self.rg_path,
            "--color=never",
            "--line-number",
            "--context=2",  # Show 2 lines around match
            "--max-count", str(limit), # Limit matches per file
            "--encoding", "utf-8"
        ]

        if not regex:
            cmd.append("--fixed-strings")
        
        # Case insensitive by default for better UX
        cmd.append("--ignore-case")
        
        cmd.append(query)
        cmd.append(str(self.root_path))

        try:
            # Use shell=False for security
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                encoding="utf-8",
                check=False # Don't raise on no match (exit code 1)
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                # Truncate if too long to save context window
                if len(output) > 8000: 
                    output = output[:8000] + "\n...[Output Truncated]..."
                return output
            elif result.returncode == 1:
                return "No matches found."
            else:
                return f"Ripgrep error: {result.stderr}"

        except Exception as e:
            return f"Search execution failed: {str(e)}"
