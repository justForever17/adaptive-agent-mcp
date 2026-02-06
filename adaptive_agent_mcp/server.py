from mcp.server.fastmcp import FastMCP
from .src.config import config
from .src.storage import StorageValidation
from .src.indexer import indexer

# Initialize Storage (Auto-create directories)
StorageValidation.initialize_storage()
# Build Index on Startup
indexer.build_index()

# Initialize FastMCP Server
mcp = FastMCP("Adaptive-Agent-MCP")

# Import tools to register them
from .src.tools import session
from .src.tools import retrieval
from .src.tools import memory

def main():
    """Main entry point for the MCP server."""
    print(f"Starting Adaptive-Agent-MCP v1.0.0")
    print(f"Storage path: {config.storage_path}")
    mcp.run()

if __name__ == "__main__":
    main()
