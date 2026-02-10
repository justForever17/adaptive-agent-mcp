import asyncio
import logging
from mcp.server.fastmcp import FastMCP
from .src.config import config
from .src.storage import StorageValidation
from .src.indexer import indexer

logger = logging.getLogger("adaptive-agent-mcp")

# Initialize Storage (Auto-create directories)
StorageValidation.initialize_storage()

# Deferred Indexing — runs on first tool call, not at import time
# Avoids RuntimeError in hosts that already have an event loop
_indexing_done = False

async def ensure_indexed():
    """Run indexing once, lazily. Safe to call multiple times."""
    global _indexing_done
    if not _indexing_done:
        try:
            await indexer.build_index()
        except Exception as e:
            logger.warning(f"Startup indexing failed: {e}")
        _indexing_done = True

# Initialize FastMCP Server
mcp = FastMCP("Adaptive-Agent-MCP")

# Import tools to register them
from .src.tools import session
from .src.tools import retrieval
from .src.tools import memory
from .src.tools import graph

def main():
    """Main entry point for the MCP server."""
    logger.info(f"Starting Adaptive-Agent-MCP v1.0.0")
    logger.info(f"Storage path: {config.storage_path}")
    mcp.run()

if __name__ == "__main__":
    main()
