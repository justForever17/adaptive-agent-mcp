"""
GraphStore - 基于 NetworkX 的知识图谱存储

提供:
- 实体 (Entity) 和关系 (Relation) 的结构化存储
- 三元组 (Subject) -> [Predicate] -> (Object) 管理
- 多跳推理 (Multi-hop Reasoning) 查询
- JSON 序列化持久化
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

from .config import config
from .lock_manager import LockManager


@dataclass
class Entity:
    """实体节点"""
    id: str
    name: str
    type: str  # "user", "technology", "concept", "project" 等
    attributes: Dict[str, Any]
    created_at: str


@dataclass
class Relation:
    """关系边"""
    subject_id: str
    predicate: str  # "LIKES", "USES", "PREFERS", "WORKS_ON" 等
    object_id: str
    weight: float = 1.0
    source: str = ""  # 记录来源 (如 daily_log ID)
    created_at: str = ""


@dataclass
class Triple:
    """三元组 (用于 LLM 提取结果)"""
    subject: str
    predicate: str
    object: str
    subject_type: str = "unknown"
    object_type: str = "unknown"


class GraphStore:
    """
    基于 NetworkX 的知识图谱存储
    
    使用方式:
        store = GraphStore()
        
        # 添加实体和关系
        store.add_entity("user", "User", "user")
        store.add_entity("nextjs", "Next.js", "technology")
        store.add_relation("user", "LIKES", "nextjs")
        
        # 查询关系
        results = store.query_relations("user", "LIKES")
        # -> [("nextjs", "Next.js", "technology")]
    """
    
    def __init__(self, graph_path: Optional[Path] = None):
        """
        初始化图存储
        
        Args:
            graph_path: 图数据文件路径，默认在 storage_path/.graph/knowledge.json
        """
        self.graph_path = graph_path or (config.storage_path / ".graph" / "knowledge.json")
        self._graph: Optional["nx.DiGraph"] = None
        
        # 确保目录存在
        self.graph_path.parent.mkdir(parents=True, exist_ok=True)
    
    @property
    def available(self) -> bool:
        """检查 NetworkX 是否可用"""
        return NETWORKX_AVAILABLE
    
    @property
    def graph(self) -> "nx.DiGraph":
        """获取图实例 (懒加载)"""
        if self._graph is None:
            if NETWORKX_AVAILABLE:
                self._graph = nx.DiGraph()
                self._load()
            else:
                raise ImportError("NetworkX is not installed. Run: pip install networkx")
        return self._graph
    
    def _load(self):
        """从 JSON 加载图数据"""
        if not self.graph_path.exists():
            return
        
        try:
            with open(self.graph_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 加载节点
            for node_data in data.get("nodes", []):
                self._graph.add_node(
                    node_data["id"],
                    name=node_data.get("name", ""),
                    type=node_data.get("type", "unknown"),
                    attributes=node_data.get("attributes", {}),
                    created_at=node_data.get("created_at", "")
                )
            
            # 加载边
            for edge_data in data.get("edges", []):
                self._graph.add_edge(
                    edge_data["source"],
                    edge_data["target"],
                    predicate=edge_data.get("predicate", "RELATED_TO"),
                    weight=edge_data.get("weight", 1.0),
                    source=edge_data.get("source_doc", ""),
                    created_at=edge_data.get("created_at", "")
                )
        except (json.JSONDecodeError, KeyError) as e:
            # 文件损坏，重新初始化
            self._graph = nx.DiGraph()
    
    def _save(self):
        """保存图数据到 JSON"""
        nodes = []
        for node_id, attrs in self.graph.nodes(data=True):
            nodes.append({
                "id": node_id,
                "name": attrs.get("name", ""),
                "type": attrs.get("type", "unknown"),
                "attributes": attrs.get("attributes", {}),
                "created_at": attrs.get("created_at", "")
            })
        
        edges = []
        for source, target, attrs in self.graph.edges(data=True):
            edges.append({
                "source": source,
                "target": target,
                "predicate": attrs.get("predicate", "RELATED_TO"),
                "weight": attrs.get("weight", 1.0),
                "source_doc": attrs.get("source", ""),
                "created_at": attrs.get("created_at", "")
            })
        
        data = {"nodes": nodes, "edges": edges}
        
        with LockManager.knowledge_lock():
            with open(self.graph_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_entity(
        self, 
        entity_id: str, 
        name: str, 
        entity_type: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        添加或更新实体
        
        Args:
            entity_id: 实体唯一ID (小写，下划线分隔)
            name: 实体显示名称
            entity_type: 实体类型 (user, technology, concept, project, ...)
            attributes: 附加属性
        """
        created_at = datetime.now().isoformat()
        
        # 如果节点已存在，更新属性
        if self.graph.has_node(entity_id):
            self.graph.nodes[entity_id].update({
                "name": name,
                "type": entity_type,
                "attributes": attributes or {}
            })
        else:
            self.graph.add_node(
                entity_id,
                name=name,
                type=entity_type,
                attributes=attributes or {},
                created_at=created_at
            )
        
        self._save()
        return True
    
    def add_relation(
        self, 
        subject_id: str, 
        predicate: str, 
        object_id: str,
        weight: float = 1.0,
        source: str = ""
    ) -> bool:
        """
        添加关系 (三元组)
        
        Args:
            subject_id: 主语实体ID
            predicate: 谓词/关系类型 (LIKES, USES, PREFERS, WORKS_ON, ...)
            object_id: 宾语实体ID
            weight: 关系强度
            source: 关系来源文档ID
        """
        # 确保两端节点存在
        if not self.graph.has_node(subject_id):
            self.add_entity(subject_id, subject_id, "unknown")
        if not self.graph.has_node(object_id):
            self.add_entity(object_id, object_id, "unknown")
        
        created_at = datetime.now().isoformat()
        
        # 添加或更新边
        self.graph.add_edge(
            subject_id,
            object_id,
            predicate=predicate.upper(),
            weight=weight,
            source=source,
            created_at=created_at
        )
        
        self._save()
        return True
    
    def add_triple(self, triple: Triple, source: str = "") -> bool:
        """
        添加三元组 (从 LLM 提取结果)
        """
        # 规范化 ID
        subject_id = triple.subject.lower().replace(" ", "_")
        object_id = triple.object.lower().replace(" ", "_")
        
        # 添加实体
        self.add_entity(subject_id, triple.subject, triple.subject_type)
        self.add_entity(object_id, triple.object, triple.object_type)
        
        # 添加关系
        return self.add_relation(subject_id, triple.predicate, object_id, source=source)
    
    def query_relations(
        self, 
        subject_id: Optional[str] = None,
        predicate: Optional[str] = None,
        object_id: Optional[str] = None
    ) -> List[Tuple[str, str, str, Dict[str, Any]]]:
        """
        查询关系
        
        Args:
            subject_id: 主语实体ID (可选)
            predicate: 谓词 (可选)
            object_id: 宾语实体ID (可选)
            
        Returns:
            List of (subject_id, predicate, object_id, edge_attrs)
        """
        results = []
        
        for s, o, attrs in self.graph.edges(data=True):
            edge_predicate = attrs.get("predicate", "RELATED_TO")
            
            # 应用过滤条件
            if subject_id and s != subject_id:
                continue
            if predicate and edge_predicate != predicate.upper():
                continue
            if object_id and o != object_id:
                continue
            
            results.append((s, edge_predicate, o, attrs))
        
        return results
    
    def query_entity_neighbors(
        self, 
        entity_id: str, 
        predicate: Optional[str] = None,
        direction: str = "out"
    ) -> List[Tuple[str, str, Dict[str, Any]]]:
        """
        查询实体的邻居
        
        Args:
            entity_id: 实体ID
            predicate: 过滤谓词 (可选)
            direction: "out" (出边), "in" (入边), "both"
            
        Returns:
            List of (neighbor_id, predicate, neighbor_attrs)
        """
        if not self.graph.has_node(entity_id):
            return []
        
        results = []
        
        # 出边 (entity -> neighbor)
        if direction in ("out", "both"):
            for neighbor in self.graph.successors(entity_id):
                edge_attrs = self.graph.edges[entity_id, neighbor]
                edge_predicate = edge_attrs.get("predicate", "RELATED_TO")
                
                if predicate and edge_predicate != predicate.upper():
                    continue
                
                neighbor_attrs = self.graph.nodes[neighbor]
                results.append((neighbor, edge_predicate, neighbor_attrs))
        
        # 入边 (neighbor -> entity)
        if direction in ("in", "both"):
            for neighbor in self.graph.predecessors(entity_id):
                edge_attrs = self.graph.edges[neighbor, entity_id]
                edge_predicate = edge_attrs.get("predicate", "RELATED_TO")
                
                if predicate and edge_predicate != predicate.upper():
                    continue
                
                neighbor_attrs = self.graph.nodes[neighbor]
                results.append((neighbor, edge_predicate, neighbor_attrs))
        
        return results
    
    def multi_hop_query(
        self, 
        start_id: str, 
        predicates: List[str],
        max_depth: int = 3
    ) -> List[List[str]]:
        """
        多跳推理查询
        
        Args:
            start_id: 起始实体ID
            predicates: 路径上的谓词列表
            max_depth: 最大深度
            
        Returns:
            所有匹配路径 (节点ID列表)
        """
        if not self.graph.has_node(start_id):
            return []
        
        paths = []
        
        def dfs(current: str, remaining_predicates: List[str], path: List[str]):
            if not remaining_predicates:
                paths.append(path.copy())
                return
            
            if len(path) > max_depth:
                return
            
            target_predicate = remaining_predicates[0].upper()
            
            for neighbor in self.graph.successors(current):
                edge_predicate = self.graph.edges[current, neighbor].get("predicate", "")
                if edge_predicate == target_predicate:
                    path.append(neighbor)
                    dfs(neighbor, remaining_predicates[1:], path)
                    path.pop()
        
        dfs(start_id, predicates, [start_id])
        return paths
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """获取实体详情"""
        if not self.graph.has_node(entity_id):
            return None
        
        attrs = self.graph.nodes[entity_id]
        return Entity(
            id=entity_id,
            name=attrs.get("name", ""),
            type=attrs.get("type", "unknown"),
            attributes=attrs.get("attributes", {}),
            created_at=attrs.get("created_at", "")
        )
    
    def get_all_entities(self, entity_type: Optional[str] = None) -> List[Entity]:
        """获取所有实体 (可按类型过滤)"""
        entities = []
        for node_id, attrs in self.graph.nodes(data=True):
            if entity_type and attrs.get("type") != entity_type:
                continue
            entities.append(Entity(
                id=node_id,
                name=attrs.get("name", ""),
                type=attrs.get("type", "unknown"),
                attributes=attrs.get("attributes", {}),
                created_at=attrs.get("created_at", "")
            ))
        return entities
    
    def delete_entity(self, entity_id: str) -> bool:
        """删除实体及其所有关系"""
        if not self.graph.has_node(entity_id):
            return False
        
        with LockManager.knowledge_lock():
            self.graph.remove_node(entity_id)
            self._save()
        return True
    
    def delete_relation(self, subject_id: str, object_id: str) -> bool:
        """删除关系"""
        if not self.graph.has_edge(subject_id, object_id):
            return False
        
        with LockManager.knowledge_lock():
            self.graph.remove_edge(subject_id, object_id)
            self._save()
        return True
    
    def stats(self) -> Dict[str, Any]:
        """获取图统计信息"""
        entity_types = {}
        for _, attrs in self.graph.nodes(data=True):
            t = attrs.get("type", "unknown")
            entity_types[t] = entity_types.get(t, 0) + 1
        
        predicate_types = {}
        for _, _, attrs in self.graph.edges(data=True):
            p = attrs.get("predicate", "RELATED_TO")
            predicate_types[p] = predicate_types.get(p, 0) + 1
        
        return {
            "entity_count": self.graph.number_of_nodes(),
            "relation_count": self.graph.number_of_edges(),
            "entity_types": entity_types,
            "predicate_types": predicate_types
        }
    
    def close(self):
        """关闭存储"""
        self._graph = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


# 全局实例 (懒加载)
_graph_store: Optional[GraphStore] = None


def get_graph_store() -> GraphStore:
    """获取全局 GraphStore 实例"""
    global _graph_store
    if _graph_store is None:
        _graph_store = GraphStore()
    return _graph_store
