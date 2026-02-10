<div align="center">

<img src="https://raw.githubusercontent.com/justforever17/adaptive-agent-mcp/main/assets/logo.svg" alt="Adaptive Agent MCP" width="500">

### **Self-Evolving RAG for AI Agents**

> *Agents don't just read memory — they write it.*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Protocol-green.svg)](https://modelcontextprotocol.io)
[![PyPI](https://img.shields.io/pypi/v/adaptive-agent-mcp.svg)](https://pypi.org/project/adaptive-agent-mcp/)

[**中文**](README_zh.md) | **English**

</div>

---

## Core Concept

<table>
<tr>
<td width="50%">

### Traditional RAG

```
User Input → Retrieve KB → Generate
               ↑
            Read-only
        (Human-maintained)
```

</td>
<td width="50%">

### Self-Evolving RAG

```
User Input → Retrieve Memory → Generate
               ↑↓
           Read + Write
    Agent autonomously evolves
```

</td>
</tr>
</table>

**Key Differences:**

| | Traditional RAG | Adaptive Agent MCP |
|:---:|:---|:---|
| Read | Retrieves pre-indexed documents | Dynamically accumulates at runtime |
| Write | Human-maintained knowledge base | **Agent writes autonomously** |
| Scope | Generic knowledge | **User-specific memory** |
| State | Static data | **Continuously evolves** |

---

## How It Works

```
In Claude Code: "Remember, I prefer TypeScript"
         ↓
    Agent automatically calls:
    • append_daily_log() → Record to daily log
    • update_preference() → Update preferences
    • extract_knowledge() → Extract knowledge graph
         ↓
In Antigravity: "What are my coding preferences?"
         ↓
    AI: "You prefer TypeScript"
```

**Teach once, remember forever. Share across apps, never forget.**

---

## Quick Start

### Installation

Configure `mcp.json` in any MCP-compatible AI application:

**Basic Configuration:**
```json
{
  "mcpServers": {
    "adaptive-agent-mcp": {
      "command": "uvx",
      "args": ["adaptive-agent-mcp"]
    }
  }
}
```

**Full Configuration (with Semantic Search API):**
```json
{
  "mcpServers": {
    "adaptive-agent-mcp": {
      "command": "uvx",
      "args": ["adaptive-agent-mcp"],
      "env": {
        "ADAPTIVE_EMBEDDING_BASE_URL": "https://api.openai.com/v1",
        "ADAPTIVE_EMBEDDING_API_KEY": "your-api-key",
        "ADAPTIVE_EMBEDDING_MODEL": "text-embedding-3-small",
        "ADAPTIVE_RERANK_BASE_URL": "https://api.cohere.ai/v1",
        "ADAPTIVE_RERANK_API_KEY": "your-api-key",
        "ADAPTIVE_RERANK_MODEL": "rerank-english-v3.0"
      }
    }
  }
}
```

> Default storage path: `~/.adaptive-agent/memory`. All apps share the same memory.

### Enhance Agent Memory Behavior (Optional)

If your AI doesn't actively read/write memory, add this to your system prompt or user rules:

```
## Memory System Instructions

- At the start of each conversation, call `initialize_session` to load user preferences.
- When user says "remember", "save", or expresses preferences, call `update_preference` or `append_daily_log`.
- After completing tasks, briefly record progress using `append_daily_log`.
- When user asks about past conversations, use `query_memory_headers` or `search_memory_content`.
```

---

## Features

| Feature | Description | Version |
|:---|:---|:---:|
| **Three-Layer Memory** | MEMORY.md + Daily Logs + Knowledge Items | v0.1.0 |
| **Scope Isolation** | `project:xxx`, `app:xxx`, `global` | v0.2.0 |
| **Concurrent Safety** | Cross-process file locking + async locks | v0.3.0 |
| **Incremental Indexing** | mtime-based smart updates | v0.3.0 |
| **Hybrid Search** | Vector + FTS5 with RRF fusion | v0.6.0 |
| **Area Partitioning** | Scope-based knowledge routing | v0.6.0 |
| **Knowledge Graph** | NetworkX-based entity relations | v0.5.0 |
| **Async Foundation** | Non-blocking I/O throughout | v0.6.0 |

---

## Available Tools (14 tools)

### Session & Retrieval
| Tool | Description |
|:---|:---|
| `initialize_session` | Initialize session with user profile and recent context |
| `query_memory_headers` | Index scan — browse memory file metadata |
| `read_memory_content` | Read complete memory file content |
| `search_memory_content` | Full-text search using ripgrep |

### Memory & Knowledge
| Tool | Description |
|:---|:---|
| `update_preference` | Intelligently update user preferences |
| `append_daily_log` | Append content to daily log or knowledge items |
| `query_knowledge` | Hybrid search (Vector + FTS5 + RRF fusion) with browse fallback |
| `delete_knowledge` | Soft-delete knowledge items |
| `get_period_context` | Aggregate weekly/monthly logs for summaries |
| `archive_period` | Save period summaries |

### Knowledge Graph
| Tool | Description |
|:---|:---|
| `extract_knowledge` | Extract entity relations from text |
| `add_knowledge_relation` | Manually add relations |
| `query_knowledge_graph` | Query entities, relations, or stats |
| `multi_hop_query` | Multi-hop reasoning queries |

---

## Storage Structure

```
~/.adaptive-agent/memory/
├── MEMORY.md                          # User preferences (scope-based)
├── knowledge/
│   └── areas/
│       ├── general/items.json         # Global knowledge
│       ├── chat/items.json            # Chat-scope knowledge
│       ├── coding/items.json          # Coding-scope knowledge
│       ├── writing/items.json         # Writing-scope knowledge
│       └── projects/{name}/items.json # Project-specific knowledge
├── .index/
│   ├── vectors.db                     # SQLite + sqlite-vec + FTS5
│   └── index.json                     # Indexer metadata
├── .graph/
│   └── knowledge.json                 # NetworkX graph
├── .locks/                            # File lock directory
└── memory/
    └── 2026/
        └── 02_february/
            └── week_07/
                └── 2026-02-10.md      # Daily logs
```

---

## Data Safety

- **Isolated storage**: Data stored in `~/.adaptive-agent/memory`, independent of uvx installation
- **Concurrent safety**: filelock prevents data corruption from multiple clients
- **Human-readable**: All data in Markdown/JSON format, easy to backup and version control

---

## Documentation

- [Architecture Design](docs/架构设计.md) (Chinese)
- [Local Model Setup](docs/setup_local_model.md)
- [Changelog](CHANGELOG.md)

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

<div align="center">

**Adaptive Agent MCP** — *Where agents learn, remember, and evolve.*

</div>
