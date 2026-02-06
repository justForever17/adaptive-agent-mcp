"""
VectorStore - 基于 sqlite-vec 的向量存储 + SQLite FTS5 全文搜索

提供:
- 向量索引存储
- KNN 语义搜索
- FTS5 全文搜索 (替代 ripgrep)
- 与 VectorClient 集成的完整 RAG 管道
"""

import sqlite3
import struct
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json

try:
    import sqlite_vec
    SQLITE_VEC_AVAILABLE = True
except ImportError:
    SQLITE_VEC_AVAILABLE = False

from .config import config
from .lock_manager import LockManager


@dataclass
class SearchResult:
    """向量搜索结果"""
    id: str
    content: str
    metadata: Dict[str, Any]
    distance: float
    score: float  # 1 - normalized_distance (越高越相关)


@dataclass
class FTSResult:
    """全文搜索结果"""
    id: str
    content: str
    metadata: Dict[str, Any]
    snippet: str  # 匹配片段高亮
    rank: float  # BM25 排名分数


def serialize_vector(vector: List[float]) -> bytes:
    """将 Python list 序列化为 float32 bytes (sqlite-vec 格式)"""
    return struct.pack(f'{len(vector)}f', *vector)


def deserialize_vector(blob: bytes) -> List[float]:
    """将 bytes 反序列化为 Python list"""
    n = len(blob) // 4  # float32 = 4 bytes
    return list(struct.unpack(f'{n}f', blob))


class VectorStore:
    """
    基于 sqlite-vec 的向量存储
    
    使用方式:
        store = VectorStore()
        
        # 添加文档
        store.add("doc1", "Hello world", [0.1, 0.2, ...], {"source": "memory"})
        
        # 搜索相似文档
        results = store.search([0.15, 0.25, ...], top_k=10)
    """
    
    def __init__(self, db_path: Optional[Path] = None, dimension: int = 1024):
        """
        初始化向量存储
        
        Args:
            db_path: 数据库文件路径，默认在 storage_path/.vector/vectors.db
            dimension: 向量维度，默认 1024 (Qwen3-Embedding-8B)
        """
        self.db_path = db_path or (config.storage_path / ".vector" / "vectors.db")
        self.dimension = dimension
        self._conn: Optional[sqlite3.Connection] = None
        
        # 确保目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    @property
    def available(self) -> bool:
        """检查 sqlite-vec 是否可用"""
        return SQLITE_VEC_AVAILABLE
    
    @property
    def conn(self) -> sqlite3.Connection:
        """获取数据库连接 (懒加载)"""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            
            if SQLITE_VEC_AVAILABLE:
                # 加载 sqlite-vec 扩展
                self._conn.enable_load_extension(True)
                sqlite_vec.load(self._conn)
                self._conn.enable_load_extension(False)
            
            self._init_tables()
        
        return self._conn
    
    def _init_tables(self):
        """初始化数据库表"""
        # 文档元数据表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                metadata TEXT,  -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # FTS5 全文搜索表
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts
            USING fts5(
                id,
                content,
                content='documents',
                content_rowid='rowid',
                tokenize='unicode61'
            )
        """)
        
        # FTS5 触发器 - 自动同步
        self.conn.executescript("""
            CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
                INSERT INTO documents_fts(rowid, id, content) VALUES (new.rowid, new.id, new.content);
            END;
            CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
                INSERT INTO documents_fts(documents_fts, rowid, id, content) VALUES('delete', old.rowid, old.id, old.content);
            END;
            CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
                INSERT INTO documents_fts(documents_fts, rowid, id, content) VALUES('delete', old.rowid, old.id, old.content);
                INSERT INTO documents_fts(rowid, id, content) VALUES (new.rowid, new.id, new.content);
            END;
        """)
        
        if SQLITE_VEC_AVAILABLE:
            # 向量索引表 (sqlite-vec virtual table)
            self.conn.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS vec_index 
                USING vec0(
                    id TEXT PRIMARY KEY,
                    embedding float[{self.dimension}]
                )
            """)
        
        self.conn.commit()
    
    def add(
        self, 
        doc_id: str, 
        content: str, 
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        添加文档和向量
        
        Args:
            doc_id: 文档唯一ID
            content: 文档内容
            embedding: 向量表示
            metadata: 附加元数据
            
        Returns:
            是否添加成功
        """
        if len(embedding) != self.dimension:
            raise ValueError(f"向量维度不匹配: 期望 {self.dimension}, 实际 {len(embedding)}")
        
        with LockManager.knowledge_lock():
            try:
                # 插入文档元数据
                self.conn.execute(
                    "INSERT OR REPLACE INTO documents (id, content, metadata) VALUES (?, ?, ?)",
                    (doc_id, content, json.dumps(metadata or {}, ensure_ascii=False))
                )
                
                if SQLITE_VEC_AVAILABLE:
                    # 插入向量
                    self.conn.execute(
                        "INSERT OR REPLACE INTO vec_index (id, embedding) VALUES (?, ?)",
                        (doc_id, serialize_vector(embedding))
                    )
                
                self.conn.commit()
                return True
            except Exception as e:
                self.conn.rollback()
                raise e
    
    def search(
        self, 
        query_embedding: List[float], 
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        向量相似度搜索
        
        Args:
            query_embedding: 查询向量
            top_k: 返回前 K 个结果
            filter_metadata: 元数据过滤条件 (暂未实现)
            
        Returns:
            相似度从高到低排序的搜索结果
        """
        if not SQLITE_VEC_AVAILABLE:
            return []
        
        if len(query_embedding) != self.dimension:
            raise ValueError(f"查询向量维度不匹配: 期望 {self.dimension}, 实际 {len(query_embedding)}")
        
        # KNN 查询
        cursor = self.conn.execute("""
            SELECT 
                v.id,
                v.distance,
                d.content,
                d.metadata
            FROM vec_index v
            JOIN documents d ON v.id = d.id
            WHERE v.embedding MATCH ?
            ORDER BY v.distance
            LIMIT ?
        """, (serialize_vector(query_embedding), top_k))
        
        results = []
        for row in cursor.fetchall():
            doc_id, distance, content, metadata_json = row
            
            # 计算相关性分数 (距离越小越相关，转换为 0-1 分数)
            score = 1.0 / (1.0 + distance)
            
            results.append(SearchResult(
                id=doc_id,
                content=content,
                metadata=json.loads(metadata_json) if metadata_json else {},
                distance=distance,
                score=score
            ))
        
        return results
    
    def fulltext_search(
        self, 
        query: str, 
        limit: int = 20
    ) -> List[FTSResult]:
        """
        FTS5 全文搜索 (替代 ripgrep)
        
        Args:
            query: 搜索关键词
            limit: 最大返回数量
            
        Returns:
            按 BM25 排名的搜索结果
        """
        # FTS5 搜索，使用 BM25 排名
        cursor = self.conn.execute("""
            SELECT 
                f.id,
                d.content,
                d.metadata,
                snippet(documents_fts, 1, '>>>>', '<<<<', '...', 32) as snippet,
                bm25(documents_fts) as rank
            FROM documents_fts f
            JOIN documents d ON f.id = d.id
            WHERE documents_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit))
        
        results = []
        for row in cursor.fetchall():
            doc_id, content, metadata_json, snippet, rank = row
            results.append(FTSResult(
                id=doc_id,
                content=content,
                metadata=json.loads(metadata_json) if metadata_json else {},
                snippet=snippet,
                rank=rank
            ))
        
        return results
    
    def delete(self, doc_id: str) -> bool:
        """删除文档和向量"""
        with LockManager.knowledge_lock():
            try:
                self.conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
                if SQLITE_VEC_AVAILABLE:
                    self.conn.execute("DELETE FROM vec_index WHERE id = ?", (doc_id,))
                self.conn.commit()
                return True
            except Exception:
                self.conn.rollback()
                return False
    
    def count(self) -> int:
        """获取文档总数"""
        cursor = self.conn.execute("SELECT COUNT(*) FROM documents")
        return cursor.fetchone()[0]
    
    def get(self, doc_id: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """获取文档内容和元数据"""
        cursor = self.conn.execute(
            "SELECT content, metadata FROM documents WHERE id = ?", 
            (doc_id,)
        )
        row = cursor.fetchone()
        if row:
            return row[0], json.loads(row[1]) if row[1] else {}
        return None
    
    def close(self):
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


# 全局实例 (懒加载)
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """获取全局 VectorStore 实例"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
