<div align="center">

<img src="https://raw.githubusercontent.com/justforever17/adaptive-agent-mcp/main/assets/logo.svg" alt="Adaptive Agent MCP" width="500">

### **Self-Evolving RAG for AI Agents**

> *Agents don't just read memory — they write it.*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Protocol-green.svg)](https://modelcontextprotocol.io)
[![PyPI](https://img.shields.io/pypi/v/adaptive-agent-mcp.svg)](https://pypi.org/project/adaptive-agent-mcp/)

**中文** | [**English**](README.md)

</div>

---

## 核心理念

<table>
<tr>
<td width="50%">

### 传统 RAG

```
用户输入 → 检索知识库 → 生成回答
              ↑
           只读访问
         (人工维护)
```

</td>
<td width="50%">

### Self-Evolving RAG

```
用户输入 → 检索记忆库 → 生成回答
              ↑↓
           读 + 写
    Agent 自主演化知识
```

</td>
</tr>
</table>

**不同之处：**

| | 传统 RAG | Adaptive Agent MCP |
|:---:|:---|:---|
| 读 | 检索预先索引的文档 | Agent 运行时动态积累 |
| 写 | 人类维护知识库 | **Agent 自主写入** |
| 范围 | 通用知识 | **用户专属记忆** |
| 状态 | 静态数据 | **随对话持续进化** |

---

## 它是如何工作的？

```
在 Claude Code 中: "记住，我喜欢使用 TypeScript"
         ↓
    Agent 自动调用:
    • append_daily_log() → 记录到日志
    • update_preference() → 更新偏好
    • extract_knowledge() → 抽取知识图谱
         ↓
在 Antigravity 中: "我的编程偏好是什么？"
         ↓
    AI: "你喜欢使用 TypeScript"
```

**一次教会，终生受用。跨应用共享，永不遗忘。**

---

## 记忆不会混乱吗？——Scope 作用域机制

> _"如果所有项目共享记忆，那项目 A 的偏好会不会污染项目 B？"_
> _"跟 AI 聊天时想要卖萌撒娇，写代码时又要严谨专业，这怎么区分？"_

**都可以。** 我们设计了 **三层 Scope（作用域）** 机制来精确控制记忆的边界：

| 作用域类型 | 优先级 | 适用场景 | 示例 |
|-----------|-------|---------|------|
| **project:xxx** | 最高 | 项目专属规范 | "这个项目用 vanilla CSS" |
| **app:xxx** | 中等 | 场景特定偏好 | "聊天时卖萌，写代码时严谨" |
| **global** | 最低 | 通用偏好 | "我喜欢 TypeScript" |

### 场景级 Scope（v0.2.0 新增）

```
你: "跟我聊天时说话要甜一点，用颜文字"
AI: ✓ 已保存到 [app:chat]

你: "写代码时要专业严谨"  
AI: ✓ 已保存到 [app:coding]

(在聊天场景)
AI: 好的主人～ (≧▽≦)

(在写代码场景)
AI: 已完成代码重构，以下是变更说明...
```

### 语义理解驱动

**Agent 会根据对话意图自动选择合适的 scope**，无需用户明确说明：

| 对话意图 | 自动推断 Scope |
|---------|---------------|
| 闲聊、情感交流 | `app:chat` |
| 写代码、技术讨论 | `app:coding` |
| 写文档、文案创作 | `app:writing` |
| 在某项目中工作 | `project:xxx` |
| 无法判断 | `global` |

### 查询时的智能过滤

- 在**项目 A** 中查询 → 返回 **global + app:coding + project:A**
- 在**聊天场景**查询 → 返回 **global + app:chat**
- 更具体的 scope 优先级更高，会覆盖通用设置

**结论**: 既享受跨平台共享全局偏好的便利，又保证场景级和项目级的精确隔离。

---

## 快速开始

### 前提条件 (Prerequisites)

1. **Python 3.10+**
2. **Ripgrep (`rg`)**: **必需** (用于全文搜索)。
   - **Windows**: `choco install ripgrep` 或 `winget install BurntSushi.ripgrep.MSVC`
   - **macOS**: `brew install ripgrep`
   - **Linux**: `apt install ripgrep`
3. **SQLite**: Python 会自动处理，**无需** 手动安装。

### 配置 (Configuration v0.6.0)

配置通过 **环境变量** 管理。

#### 1. mcp.json 结构

配置 `mcp.json` (通常位于 `%APPDATA%\Claude\mcp.json` 或 `~/Library/Application Support/Claude/mcp.json`):

```json
{
  "mcpServers": {
    "adaptive-agent-mcp": {
      "command": "uvx",
      "args": ["adaptive-agent-mcp"],
      "env": {
        "ADAPTIVE_STORAGE_PATH": "C:/Users/YourName/.adaptive-agent/memory",
        "ADAPTIVE_EMBEDDING_PROVIDER": "openai_compatible",
        "ADAPTIVE_EMBEDDING_BASE_URL": "https://api.siliconflow.cn/v1",
        "ADAPTIVE_EMBEDDING_API_KEY": "sk-your-siliconflow-key",
        "ADAPTIVE_EMBEDDING_MODEL": "Qwen/Qwen2.5-Coder-7B-Instruct",
        "ADAPTIVE_RERANK_PROVIDER": "cohere_compatible",
        "ADAPTIVE_RERANK_BASE_URL": "https://api.siliconflow.cn/v1",
        "ADAPTIVE_RERANK_API_KEY": "sk-your-siliconflow-key",
        "ADAPTIVE_RERANK_MODEL": "BAAI/bge-reranker-v2-m3"
      }
    }
  }
}
```

#### 2. 环境变量一览

所有变量前缀为 `ADAPTIVE_`。

| 变量 | 说明 | 默认值 |
|---|---|---|
| `ADAPTIVE_STORAGE_PATH` | 记忆存储路径 | `~/.adaptive-agent/memory` |
| `ADAPTIVE_RIPGREP_PATH` | `rg` 可执行文件路径 | 自动检测 |
| `ADAPTIVE_EMBEDDING_PROVIDER` | Embedding 提供商 (`openai_compatible`) | `openai_compatible` |
| `ADAPTIVE_EMBEDDING_BASE_URL` | API 端点 | `None` |
| `ADAPTIVE_EMBEDDING_API_KEY` | API Key | `None` |
| `ADAPTIVE_EMBEDDING_MODEL` | Embedding 模型名 | `Qwen/Qwen3-Embedding-8B` |
| `ADAPTIVE_RERANK_PROVIDER` | Rerank 提供商 (`cohere_compatible`) | `cohere_compatible` |
| `ADAPTIVE_RERANK_BASE_URL` | API 端点 | `None` |
| `ADAPTIVE_RERANK_API_KEY` | API Key | `None` |
| `ADAPTIVE_RERANK_MODEL` | Rerank 模型名 | `Qwen/Qwen3-Reranker-8B` |

> 默认存储路径: `~/.adaptive-agent/memory`。所有应用共享同一份记忆。

### 增强 Agent 记忆行为 (可选)

如果你的 AI 不太主动读写记忆，可以将以下内容加入 System Prompt 或 User Rules：

```markdown
## Memory System Instructions

- At the start of each conversation, call `initialize_session` to load user preferences.
- When user says "remember", "save", or expresses preferences, call `update_preference` or `append_daily_log`.
- After completing tasks, briefly record progress using `append_daily_log`.
- When user asks about past conversations, use `query_memory_headers` or `search_memory_content`.
```

---

## 项目结构

```
.
├── docs/                        # 完整文档
├── adaptive_agent_mcp/          # 主项目目录
│   ├── server.py                # MCP 服务器入口
│   ├── src/                     # 源代码
│   │   ├── config.py            # 配置管理
│   │   ├── storage.py           # 存储层
│   │   ├── indexer.py           # 增量索引系统
│   │   ├── search_engine.py     # 搜索引擎
│   │   ├── lock_manager.py      # 并发锁管理 (v0.3.0+)
│   │   ├── vector_client.py     # 向量 API 客户端 (v0.4.0+)
│   │   ├── vector_store.py      # SQLite 向量存储 (v0.4.0+)
│   │   ├── graph_store.py       # 知识图谱存储 (v0.5.0+)
│   │   └── tools/               # MCP 工具
│   └── README.md                # 项目详细文档
├── smoke_test.py                # 烟雾测试
└── verify_full.py               # 完整功能测试
```

---

## 特性

| 特性 | 说明 | 版本 |
|------|------|:---:|
| **三层记忆架构** | MEMORY.md + 每日日志 + 知识条目 | v0.1.0 |
| **Scope 作用域隔离** | `project:xxx`, `app:xxx`, `global` | v0.2.0 |
| **并发安全** | 跨进程文件锁 + 异步锁 | v0.3.0 |
| **增量索引** | 基于 mtime 的智能增量索引 | v0.3.0 |
| **混合搜索 (Hybrid)** | 向量 + FTS5 全文搜索 + RRF 融合 | v0.6.0 |
| **区域分区 (Areas)** | 基于 Scope 的知识自动路由与存储 | v0.6.0 |
| **知识图谱** | NetworkX 实体关系存储 | v0.5.0 |
| **全异步架构** | 核心 I/O 全链路异步化 | v0.6.0 |

---

## 建议安装：ripgrep

全文搜索功能依赖 [ripgrep](https://github.com/BurntSushi/ripgrep)，如需使用 `search_memory_content` 工具请安装：

<details>
<summary><b>安装方法</b></summary>

**Windows (推荐)**:
```powershell
winget install BurntSushi.ripgrep.MSVC
```

**macOS**:
```bash
brew install ripgrep
```

**Linux**:
```bash
# Ubuntu/Debian
sudo apt install ripgrep

# Arch
sudo pacman -S ripgrep
```

**手动配置环境变量** (如自动检测失败):
```bash
# Windows: 将 rg.exe 所在目录添加到 PATH
# 或设置环境变量
ADAPTIVE_AGENT_RIPGREP_PATH=C:\path\to\rg.exe
```

</details>

---

## 可选配置：语义搜索 API (v0.4.0+)

启用语义搜索需要配置 Embedding API，Rerank API 可选但推荐。

<details>
<summary><b>环境变量配置</b></summary>

```bash
# Embedding API (必需 - 用于语义搜索)
ADAPTIVE_EMBEDDING_BASE_URL=https://api-inference.modelscope.cn/v1
ADAPTIVE_EMBEDDING_API_KEY=your-api-key
ADAPTIVE_EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B

# Rerank API (可选 - 提升搜索精度)
ADAPTIVE_RERANK_BASE_URL=https://api-inference.modelscope.cn/v1
ADAPTIVE_RERANK_API_KEY=your-api-key
ADAPTIVE_RERANK_MODEL=Qwen/Qwen3-Reranker-8B
```

支持任何 OpenAI 兼容的 Embedding API (如 ModelScope, SiliconFlow, DeepSeek) 和 Cohere 兼容的 Rerank API。

</details>

---

## MCP 工具 (14个)

### 会话与检索
| 工具 | 说明 |
|------|------|
| `initialize_session` | 会话初始化，每次对话必须首先调用 |
| `query_memory_headers` | 索引扫描，快速浏览记忆文件元数据 |
| `read_memory_content` | 读取指定文件的完整内容 |
| `search_memory_content` | 基于 ripgrep 的全文搜索 |

### 记忆与知识
| 工具 | 说明 |
|------|------|
| `update_preference` | 智能更新用户偏好 |
| `append_daily_log` | 写入每日笔记或知识条目 |
| `query_knowledge` | 混合搜索 (向量+FTS5+RRF) + 浏览回退模式 |
| `delete_knowledge` | 软删除知识条目 (Status: deleted) |
| `get_period_context` | 聚合周/月日志用于总结 |
| `archive_period` | 保存周期总结 |

### 知识图谱
| 工具 | 说明 |
|------|------|
| `extract_knowledge` | 从文本自动抽取实体关系 |
| `add_knowledge_relation` | 手动添加实体关系 |
| `query_knowledge_graph` | 查询实体/关系/统计 |
| `multi_hop_query` | 多跳关系推理查询 |

---

## 文档


- [快速开始](./docs/快速开始.md)
- [使用指南](./docs/使用指南.md)
- [架构设计](./docs/架构设计.md)
- [使用场景示例](./docs/使用场景示例.md)
- [项目详细文档](./adaptive_agent_mcp/README.md)

---

<details>
<summary><b>开发安装</b></summary>

```bash
git clone https://github.com/justforever17/adaptive-agent-mcp.git
cd adaptive-agent-mcp

# 安装依赖
pip install -e .

# 可选：安装 ripgrep 以启用全文搜索
# Windows: choco install ripgrep
# macOS: brew install ripgrep
```

</details>

<details>
<summary><b>项目级记忆隔离 (可选)</b></summary>

如果希望每个项目使用独立的记忆，可以指定 `--storage-path`:

```json
{
  "mcpServers": {
    "adaptive-agent-mcp": {
      "command": "uvx",
      "args": [
        "adaptive-agent-mcp",
        "--storage-path",
        "${workspaceFolder}/.agent_memory"
      ]
    }
  }
}
```

</details>

---

## 贡献

欢迎提交 Issue 和 Pull Request。

---

## 许可证

MIT License - 详见 [LICENSE](./LICENSE)

---

## 致谢

- [Anthropic](https://www.anthropic.com/) - MCP 协议创建者
- [FastMCP](https://github.com/jlowin/fastmcp) - 简化 MCP 开发
- [ripgrep](https://github.com/BurntSushi/ripgrep) - 高性能搜索引擎

---

## 赞助 (Sponsorship)

维护开源项目不易，如果您觉得 adaptive-agent-mcp 对您有帮助，欢迎请作者喝杯咖啡！

<div align="center">

| 平台 | 链接 | 支付方式 |
| :--- | :--- | :--- |
| **爱发电 (Afdian)** | [![Afdian](https://img.shields.io/badge/Afdian-支持我-946ce6?logo=afdian)](https://afdian.com/a/justforever17) | 微信, 支付宝 |

</div>