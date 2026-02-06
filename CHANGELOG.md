# Changelog

所有重要变更都会记录在此文件中。

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
