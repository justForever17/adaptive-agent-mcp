# 本地模型部署指南 (Advanced)

> **注意**: 本指南面向希望使用本地硬件运行 Embedding/Rerank 模型的高级用户。
> 默认情况下，`adaptive-agent-mcp` 使用 API 提供向量能力，无需任何本地模型。

## 适用场景

选择本地模型的理由：
- **隐私优先**: 所有数据留在本地，不发送到任何外部 API
- **离线可用**: 无网络环境下依然可用
- **成本节约**: 无 API 调用费用（前提是你有合适的硬件）

---

## 📦 安装依赖

### 1. 安装 sentence-transformers

```bash
pip install sentence-transformers
```

> 这会同时安装 PyTorch。如果你有 NVIDIA GPU，建议先安装 CUDA 版本的 PyTorch：
>
> ```bash
> pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
> ```

### 2. 下载推荐模型

**Embedding 模型** (语义理解):
```python
from sentence_transformers import SentenceTransformer

# 推荐：轻量级高效模型 (~90MB)
model = SentenceTransformer('all-MiniLM-L6-v2')

# 或者：更强的中文支持
model = SentenceTransformer('shibing624/text2vec-base-chinese')
```

**Rerank 模型** (精排):
```python
from sentence_transformers import CrossEncoder

# 推荐：BGE 系列
reranker = CrossEncoder('BAAI/bge-reranker-base')
```

模型会自动下载到 `~/.cache/huggingface/hub/`。

---

## 配置 adaptive-agent-mcp 使用本地模型

### 方案 A：修改 `config.py`

在 `adaptive_agent_mcp/src/config.py` 中添加：

```python
class Settings(BaseSettings):
    # ... 其他配置 ...
    
    # 本地模型设置
    use_local_embedding: bool = True
    local_embedding_model: str = "all-MiniLM-L6-v2"
    local_rerank_model: str = "BAAI/bge-reranker-base"
```

### 方案 B：通过环境变量

```bash
# .env 文件
ADAPTIVE_USE_LOCAL_EMBEDDING=true
ADAPTIVE_LOCAL_EMBEDDING_MODEL=all-MiniLM-L6-v2
ADAPTIVE_LOCAL_RERANK_MODEL=BAAI/bge-reranker-base
```

---

## 实现本地 VectorClient

创建 `adaptive_agent_mcp/src/vector_client_local.py`:

```python
from sentence_transformers import SentenceTransformer, CrossEncoder
from typing import List
import numpy as np

class LocalVectorClient:
    """本地向量客户端 - 使用 sentence-transformers"""
    
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2", 
                 rerank_model: str = "BAAI/bge-reranker-base"):
        self._embed_model = None
        self._rerank_model = None
        self._embedding_model_name = embedding_model
        self._rerank_model_name = rerank_model
    
    @property
    def embed_model(self):
        if self._embed_model is None:
            self._embed_model = SentenceTransformer(self._embedding_model_name)
        return self._embed_model
    
    @property
    def rerank_model(self):
        if self._rerank_model is None:
            self._rerank_model = CrossEncoder(self._rerank_model_name)
        return self._rerank_model
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """将文本转换为向量"""
        embeddings = self.embed_model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    def rerank(self, query: str, documents: List[str], top_n: int = 10) -> List[dict]:
        """对文档进行重排序"""
        pairs = [(query, doc) for doc in documents]
        scores = self.rerank_model.predict(pairs)
        
        # 按分数降序排列
        scored_docs = sorted(
            enumerate(zip(documents, scores)),
            key=lambda x: x[1][1],
            reverse=True
        )[:top_n]
        
        return [
            {"index": idx, "document": doc, "relevance_score": float(score)}
            for idx, (doc, score) in scored_docs
        ]
```

---

## 🧪 测试本地模型

```python
from adaptive_agent_mcp.src.vector_client_local import LocalVectorClient

client = LocalVectorClient()

# 测试 Embedding
texts = ["今天天气很好", "明天会下雨"]
embeddings = client.embed(texts)
print(f"Embedding 维度: {len(embeddings[0])}")

# 测试 Rerank
query = "天气预报"
docs = ["今天天气很好", "明天会下雨", "我喜欢吃苹果"]
results = client.rerank(query, docs, top_n=2)
print(f"Rerank 结果: {results}")
```

---

## 📊 性能对比

| 指标 | 本地模型 (MiniLM) | API (Qwen3-8B) |
|------|-----------------|----------------|
| 延迟 | 10-50ms | 200-500ms |
| 内存占用 | ~500MB | 0 (远程) |
| 中文效果 | 一般 | 优秀 |
| 离线可用 | ✅ | ❌ |
| 隐私 | 完全本地 | 数据发送到 API |

---

## ❓ 常见问题

### Q: 模型下载很慢怎么办？

使用镜像源：
```bash
export HF_ENDPOINT=https://hf-mirror.com
```

### Q: GPU 内存不足？

使用 CPU 模式：
```python
model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
```

### Q: 如何选择模型？

- **通用场景**: `all-MiniLM-L6-v2` (快速、轻量)
- **中文优化**: `shibing624/text2vec-base-chinese`
- **多语言**: `paraphrase-multilingual-MiniLM-L12-v2`
