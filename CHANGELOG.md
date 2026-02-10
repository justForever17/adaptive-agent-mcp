# Changelog

所有重要变更都会记录在此文件中。

## [0.6.0] - 2026-02-10

### 🚀 重大重构 (The Awakening)

- **全异步架构 (Async Foundation)**: 重写核心 I/O 路径，彻底消除 Event Loop 阻塞。
- **混合搜索 (Hybrid Search)**: 集成 `sqlite-vec` 向量检索 + SQLite FTS5 全文检索，通过 RRF (Reciprocal Rank Fusion) 算法融合结果。
- **区域分区 (Area Partitioning)**: 实现了基于 Scope 的知识自动路由与存储 (`knowledge/areas/{partition}/items.json`)。
- **延迟索引 (Deferred Indexing)**: 优化启动性能，将索引构建推迟到首次工具调用。

### ✨ 新增

- **工具增强**:
  - `query_knowledge`: 支持浏览模式回退 (Browse Fallback)。
  - `delete_knowledge`: 支持软删除知识条目 (Status: deleted)。
  - `EmbeddingService`: 支持 Ollama 并发 Embedding (Bounded Concurrency)。
  - `VectorStore`: 新增 5 个异步方法 (`async_add`, `async_search` 等)。

### 🛠️ 修复与优化

- **正确性**: 修复 `MemoryParser` 缓存共享可变状态问题；修复 FTS5 中文分词前缀搜索。
- **可维护性**: 全局 `print()` 替换为 `logging`；提取所有 Magic Numbers 到 `config.py`。
- **数据安全**: 实现 `MemoryParser` 读取时的 `deepcopy` 隔离。

### 🗑️ 移除

- 移除未注册的实验性工具: `semantic_search` (独立版), `fulltext_search`, `index_document` (功能已合并至 `query_knowledge` 和自动索引)。
- 移除过时的 `vector_client.py` (被 `services/embedding.py` 取代)。

---

## [0.5.4] - 2026-02-07

### 变更

- **Agent 引导增强**: README 添加 System Prompt 建议代码块
- **工具触发词优化**: 在核心工具 docstring 添加 `[CRITICAL]`/`[SAVE]` 强触发标记

---

## [0.5.2] - 2026-02-07

### 变更

- **文档整理**

---

## [0.5.1] - 2026-02-07

### 变更

- **依赖更新**: 升级所有依赖到最新稳定版

---
## [0.5.0] - 2026-02-06

### 新增
- **知识图谱 (Graph RAG)**: 基于 NetworkX 的实体关系存储
  - `GraphStore` 类支持三元组管理和多跳推理
  - `extract_knowledge` 工具：从文本自动抽取实体关系
  - `add_knowledge_relation` 工具：手动添加关系
  - `query_knowledge_graph` 工具：查询实体/关系/统计
  - `multi_hop_query` 工具：多跳关系推理查询

### 依赖
- 新增 `networkx>=3.0`

---

## [0.4.0] - 2026-02-05

### 新增
- **语义搜索**: 基于 Embedding API 的向量检索
  - `VectorClient` 类支持 OpenAI 兼容 Embedding 和 Cohere 兼容 Rerank
  - `VectorStore` 类基于 sqlite-vec 实现向量存储
  - `semantic_search` 工具：语义相似度搜索
  - `index_document` 工具：索引文档到向量库
  - `get_vector_stats` 工具：查看向量系统状态

- **FTS5 全文搜索**: SQLite 内置全文搜索
  - `fulltext_search` 工具：BM25 排名的关键词搜索
  - 替代 ripgrep 的轻量级方案

### 依赖
- 新增 `httpx>=0.27.0`
- 新增 `sqlite-vec>=0.1.18`

### 文档
- 新增 `docs/setup_local_model.md` 本地模型配置指南

---

## [0.3.0] - 2026-02-04

### 新增
- **并发安全**: 基于 filelock 的跨进程文件锁
  - `LockManager` 类管理 MEMORY.md、items.json、daily logs 的锁
  - 防止多客户端同时写入导致的数据损坏

- **增量索引**: 基于 mtime 的智能索引更新
  - `Indexer` 类仅重建变更文件的索引
  - 大幅提升写入性能

- **分页支持**: 防止 Context Window 爆炸
  - `query_knowledge` 支持 `limit` 和 `offset` 参数
  - `search_memory_content` 支持 `limit` 参数

### 依赖
- 新增 `filelock>=3.12.0`

---

## [0.2.1] - 2026-02-03

### 修复
- 修复 PyPI 发布的包结构问题
- 改进工具 docstring 的 Agent 引导

---

## [0.2.0] - 2026-02-02

### 新增
- **Scope 作用域机制**: 三层作用域隔离
  - `project:xxx` - 项目专属配置
  - `app:xxx` - 场景特定偏好 (chat, coding, writing)
  - `global` - 通用偏好
- **语义驱动**: Agent 根据对话意图自动选择 scope

---

## [0.1.0] - 2026-02-01

### 初始版本
- MCP 服务器基础框架
- 7 个核心工具
- 三层记忆架构
- ripgrep 全文搜索
