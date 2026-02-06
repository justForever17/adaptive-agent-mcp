import argparse
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    storage_path: Path = Path.home() / ".adaptive-agent" / "memory"
    ripgrep_path: Optional[str] = None  # Auto-detect via shutil.which("rg")

    class Config:
        env_prefix = "ADAPTIVE_AGENT_"

def get_config() -> Settings:
    parser = argparse.ArgumentParser(description="Adaptive Agent MCP Server")
    parser.add_argument("--storage-path", type=Path, help="Path to memory storage directory")
    parser.add_argument("--ripgrep-path", type=str, help="Path to ripgrep binary")
    args, unknown = parser.parse_known_args()
    
    settings = Settings()
    if args.storage_path:
        settings.storage_path = args.storage_path.resolve()
    if args.ripgrep_path:
        settings.ripgrep_path = args.ripgrep_path
    
    return settings

# Global config instance
config = get_config()
