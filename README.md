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

## Getting Started

### Prerequisites

1. **Python 3.10+**
2. **Ripgrep (`rg`)**: **REQUIRED** for full-text search. (**Windows**: `choco install ripgrep`, **macOS**: `brew install ripgrep`)
3. **SQLite**: Handled automatically by Python.

### Configuration (v0.6.0)

Configuration is managed via **Environment Variables**.

#### 1. mcp.json Structure

```json
{
  "mcpServers": {
    "adaptive-agent-mcp": {
      "command": "uvx",
      "args": ["adaptive-agent-mcp"],
      "env": {
        "ADAPTIVE_EMBEDDING_BASE_URL": "https://api.xxx.cn/v1",
        "ADAPTIVE_EMBEDDING_API_KEY": "sk-your-xxx-key",
        "ADAPTIVE_EMBEDDING_MODEL": "Qwen/Qwen2.5-Coder-7B-Instruct",
        "ADAPTIVE_RERANK_BASE_URL": "https://api.xxx.cn/v1",
        "ADAPTIVE_RERANK_API_KEY": "sk-your-xxx-key",
        "ADAPTIVE_RERANK_MODEL": "BAAI/bge-reranker-v2-m3"
      }
    }
  }
}
```

> **Local Models**:
> - **Ollama**: Set `ADAPTIVE_EMBEDDING_PROVIDER` to `ollama`.
> - **LM Studio/vLLM**: Set `ADAPTIVE_EMBEDDING_PROVIDER` to `openai_compatible`.
> - **Base URL**: Set to your local endpoint (e.g., `http://localhost:11434/v1` or `http://localhost:1234/v1`).
> - **API Key**: Any string.

#### 2. Environment Variables

All variables are prefixed with `ADAPTIVE_`.

| Variable | Description | Default |
|---|---|---|
| `ADAPTIVE_STORAGE_PATH` | Storage location | `~/.adaptive-agent/memory` |
| `ADAPTIVE_RIPGREP_PATH` | Path to `rg` executable | Auto-detect |
| `ADAPTIVE_EMBEDDING_PROVIDER` | Embedding provider (`openai_compatible`) | `openai_compatible` |
| `ADAPTIVE_EMBEDDING_BASE_URL` | API Endpoint | `None` |
| `ADAPTIVE_EMBEDDING_API_KEY` | API Key | `None` |
| `ADAPTIVE_EMBEDDING_MODEL` | Embedding Model | `Qwen/Qwen3-Embedding-8B` |
| `ADAPTIVE_RERANK_PROVIDER` | Rerank provider (`cohere_compatible`) | `cohere_compatible` |
| `ADAPTIVE_RERANK_BASE_URL` | API Endpoint | `None` |
| `ADAPTIVE_RERANK_API_KEY` | API Key | `None` |
| `ADAPTIVE_RERANK_MODEL` | Reranker Model | `Qwen/Qwen3-Reranker-8B` |

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
| **Rerank Service** | Cohere-compatible re-ranking for higher precision | v0.6.1 |
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

## License

MIT License - See [LICENSE](LICENSE) for details.

---

<div align="center">

**Adaptive Agent MCP** — *Where agents learn, remember, and evolve.*

</div>
