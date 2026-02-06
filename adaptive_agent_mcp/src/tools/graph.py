"""
知识图谱工具 - 实体关系管理与查询

提供:
- 实体抽取 (从文本提取三元组)
- 关系查询 (查询实体的关联)
- 图统计信息
"""

import re
from typing import List, Optional, Dict, Any
from ...server import mcp
from ..config import config
from ..graph_store import (
    GraphStore, get_graph_store, 
    Triple, Entity
)


# 常见的谓词模式 (用于简单规则提取)
PREDICATE_PATTERNS = {
    r"喜欢|偏好|prefer|like": "LIKES",
    r"使用|用|use": "USES",
    r"不喜欢|讨厌|dislike|hate": "DISLIKES",
    r"擅长|精通|expert|master": "SKILLED_AT",
    r"学习|在学|learning": "LEARNING",
    r"工作于|在.*工作|work.*at|work.*on": "WORKS_ON",
    r"创建|创造|create|build": "CREATED",
    r"属于|是.*的一部分|belong|part of": "BELONGS_TO",
    r"依赖|基于|depend|based on": "DEPENDS_ON",
}

# 常见实体类型提示词
ENTITY_TYPE_HINTS = {
    "user": ["我", "用户", "user", "自己"],
    "technology": [
        "react", "vue", "angular", "next.js", "nuxt", "svelte",
        "python", "javascript", "typescript", "java", "go", "rust",
        "tailwind", "css", "html", "node.js", "deno", "bun",
        "docker", "kubernetes", "aws", "gcp", "azure",
        "postgresql", "mysql", "mongodb", "redis", "sqlite",
    ],
    "framework": ["fastapi", "django", "flask", "express", "nestjs", "spring"],
    "tool": ["vscode", "vim", "git", "npm", "pnpm", "yarn"],
    "concept": ["dark mode", "暗色模式", "简洁", "minimal", "性能", "performance"],
}


def infer_entity_type(name: str) -> str:
    """推断实体类型"""
    name_lower = name.lower().strip()
    
    for entity_type, hints in ENTITY_TYPE_HINTS.items():
        for hint in hints:
            if hint.lower() in name_lower or name_lower in hint.lower():
                return entity_type
    
    return "concept"


def extract_triples_simple(text: str) -> List[Triple]:
    """
    简单规则提取三元组 (不依赖外部 LLM)
    
    支持的模式:
    - "我喜欢 X" -> (user, LIKES, X)
    - "我使用 X" -> (user, USES, X)
    - "X 依赖 Y" -> (X, DEPENDS_ON, Y)
    """
    triples = []
    text = text.strip()
    
    # 用户偏好模式
    for pattern, predicate in PREDICATE_PATTERNS.items():
        # 匹配 "我/用户 + 谓词 + 宾语"
        user_pattern = rf"(我|用户|user)\s*({pattern})\s*(.+?)(?:[,，。.!！?？]|$)"
        matches = re.findall(user_pattern, text, re.IGNORECASE)
        
        for match in matches:
            obj = match[2].strip()
            if obj:
                triples.append(Triple(
                    subject="user",
                    predicate=predicate,
                    object=obj,
                    subject_type="user",
                    object_type=infer_entity_type(obj)
                ))
        
        # 匹配 "X + 谓词 + Y" (非用户主语)
        general_pattern = rf"([^,，。.!！?？\s]+)\s+({pattern})\s+([^,，。.!！?？]+)"
        matches = re.findall(general_pattern, text, re.IGNORECASE)
        
        for match in matches:
            subj, _, obj = match
            subj = subj.strip()
            obj = obj.strip()
            
            # 跳过用户主语 (已处理)
            if subj.lower() in ["我", "用户", "user"]:
                continue
            
            if subj and obj:
                triples.append(Triple(
                    subject=subj,
                    predicate=predicate,
                    object=obj,
                    subject_type=infer_entity_type(subj),
                    object_type=infer_entity_type(obj)
                ))
    
    return triples


@mcp.tool()
def extract_knowledge(
    text: str,
    source: str = "manual"
) -> str:
    """
    **知识抽取** - 从文本中提取实体和关系，存入知识图谱。
    
    ## 使用场景
    当用户表达偏好或陈述事实时自动调用：
    - "我喜欢 Next.js" -> 提取 (user) -[LIKES]-> (Next.js)
    - "我使用 Tailwind CSS" -> 提取 (user) -[USES]-> (Tailwind CSS)
    - "React 依赖 Node.js" -> 提取 (React) -[DEPENDS_ON]-> (Node.js)
    
    ## 参数说明
    - `text`: 要分析的文本
    - `source`: 来源标识 (如 daily_log ID)
    
    ## 返回
    提取并存储的三元组列表
    """
    store = get_graph_store()
    
    if not store.available:
        return "❌ 知识图谱不可用：NetworkX 未安装。\n请运行: pip install networkx"
    
    try:
        triples = extract_triples_simple(text)
        
        if not triples:
            return "未从文本中提取到明确的实体关系。"
        
        # 存入图谱
        for triple in triples:
            store.add_triple(triple, source=source)
        
        # 格式化输出
        output = [f"✅ 已提取并存储 {len(triples)} 条关系:\n"]
        
        for t in triples:
            output.append(
                f"  ({t.subject}:{t.subject_type}) "
                f"-[{t.predicate}]-> "
                f"({t.object}:{t.object_type})"
            )
        
        return "\n".join(output)
        
    except Exception as e:
        return f"❌ 知识抽取失败: {str(e)}"


@mcp.tool()
def add_knowledge_relation(
    subject: str,
    predicate: str,
    object: str,
    subject_type: str = "concept",
    object_type: str = "concept"
) -> str:
    """
    **添加关系** - 手动添加实体关系到知识图谱。
    
    ## 使用场景
    - 手动记录用户偏好
    - 建立技术栈关联
    - 创建项目依赖关系
    
    ## 参数说明
    - `subject`: 主语实体名称
    - `predicate`: 关系类型 (LIKES, USES, DEPENDS_ON, WORKS_ON, ...)
    - `object`: 宾语实体名称
    - `subject_type`: 主语类型 (user, technology, concept, project)
    - `object_type`: 宾语类型
    
    ## 常用谓词
    | 谓词 | 含义 | 示例 |
    |------|------|------|
    | LIKES | 喜欢 | (user)-[LIKES]->(React) |
    | USES | 使用 | (user)-[USES]->(VSCode) |
    | DISLIKES | 不喜欢 | (user)-[DISLIKES]->(Java) |
    | SKILLED_AT | 擅长 | (user)-[SKILLED_AT]->(Python) |
    | DEPENDS_ON | 依赖 | (Next.js)-[DEPENDS_ON]->(React) |
    """
    store = get_graph_store()
    
    if not store.available:
        return "❌ 知识图谱不可用：NetworkX 未安装。"
    
    try:
        triple = Triple(
            subject=subject,
            predicate=predicate,
            object=object,
            subject_type=subject_type,
            object_type=object_type
        )
        
        store.add_triple(triple, source="manual")
        
        return (
            f"✅ 已添加关系:\n"
            f"  ({subject}:{subject_type}) -[{predicate.upper()}]-> ({object}:{object_type})"
        )
        
    except Exception as e:
        return f"❌ 添加失败: {str(e)}"


@mcp.tool()
def query_knowledge_graph(
    entity: Optional[str] = None,
    predicate: Optional[str] = None,
    entity_type: Optional[str] = None
) -> str:
    """
    **查询知识图谱** - 查询实体关系。
    
    ## 使用场景
    - "用户喜欢什么框架？" -> query_knowledge_graph(entity="user", predicate="LIKES")
    - "有哪些技术实体？" -> query_knowledge_graph(entity_type="technology")
    - "Next.js 的所有关系" -> query_knowledge_graph(entity="next.js")
    
    ## 参数说明
    - `entity`: 查询特定实体的关系 (可选)
    - `predicate`: 过滤特定关系类型 (可选)
    - `entity_type`: 过滤实体类型 (可选)
    
    ## 返回
    匹配的实体和关系列表
    """
    store = get_graph_store()
    
    if not store.available:
        return "❌ 知识图谱不可用：NetworkX 未安装。"
    
    try:
        output = []
        
        if entity:
            # 查询特定实体的关系
            entity_id = entity.lower().replace(" ", "_")
            entity_info = store.get_entity(entity_id)
            
            if entity_info:
                output.append(f"📌 **实体: {entity_info.name}** (类型: {entity_info.type})\n")
            
            # 出边关系
            neighbors = store.query_entity_neighbors(entity_id, predicate, direction="out")
            if neighbors:
                output.append("**出边关系 (->):**")
                for neighbor_id, pred, attrs in neighbors:
                    output.append(f"  -[{pred}]-> {attrs.get('name', neighbor_id)} ({attrs.get('type', 'unknown')})")
            
            # 入边关系
            neighbors_in = store.query_entity_neighbors(entity_id, predicate, direction="in")
            if neighbors_in:
                output.append("\n**入边关系 (<-):**")
                for neighbor_id, pred, attrs in neighbors_in:
                    output.append(f"  <-[{pred}]- {attrs.get('name', neighbor_id)} ({attrs.get('type', 'unknown')})")
            
            if not neighbors and not neighbors_in:
                output.append("未找到相关关系。")
        
        elif entity_type:
            # 按类型查询实体
            entities = store.get_all_entities(entity_type)
            
            if entities:
                output.append(f"📋 **类型 '{entity_type}' 的实体 ({len(entities)} 个):**\n")
                for e in entities:
                    output.append(f"  • {e.name} ({e.id})")
            else:
                output.append(f"未找到类型为 '{entity_type}' 的实体。")
        
        else:
            # 返回图统计
            stats = store.stats()
            output.append("📊 **知识图谱统计**\n")
            output.append(f"实体总数: {stats['entity_count']}")
            output.append(f"关系总数: {stats['relation_count']}")
            
            if stats['entity_types']:
                output.append("\n**实体类型分布:**")
                for t, count in sorted(stats['entity_types'].items(), key=lambda x: -x[1]):
                    output.append(f"  • {t}: {count}")
            
            if stats['predicate_types']:
                output.append("\n**关系类型分布:**")
                for p, count in sorted(stats['predicate_types'].items(), key=lambda x: -x[1]):
                    output.append(f"  • {p}: {count}")
        
        return "\n".join(output) if output else "知识图谱为空。"
        
    except Exception as e:
        return f"❌ 查询失败: {str(e)}"


@mcp.tool()
def multi_hop_query(
    start_entity: str,
    path: str
) -> str:
    """
    **多跳查询** - 沿关系路径进行推理查询。
    
    ## 使用场景
    - "用户喜欢的技术依赖什么？" -> multi_hop_query("user", "LIKES->DEPENDS_ON")
    - "和用户一起工作的人喜欢什么？" -> multi_hop_query("user", "WORKS_WITH->LIKES")
    
    ## 参数说明
    - `start_entity`: 起始实体名称
    - `path`: 关系路径 (用 -> 分隔，如 "LIKES->DEPENDS_ON")
    
    ## 返回
    所有匹配的路径终点
    """
    store = get_graph_store()
    
    if not store.available:
        return "❌ 知识图谱不可用：NetworkX 未安装。"
    
    try:
        start_id = start_entity.lower().replace(" ", "_")
        predicates = [p.strip().upper() for p in path.split("->")]
        
        paths = store.multi_hop_query(start_id, predicates)
        
        if not paths:
            return f"未找到从 '{start_entity}' 沿路径 '{path}' 的结果。"
        
        output = [f"🔗 **多跳查询结果** (起点: {start_entity}, 路径: {path})\n"]
        output.append(f"找到 {len(paths)} 条路径:\n")
        
        for i, p in enumerate(paths, 1):
            # 获取每个节点的名称
            path_names = []
            for node_id in p:
                entity = store.get_entity(node_id)
                path_names.append(entity.name if entity else node_id)
            
            # 添加谓词
            formatted_path = []
            for j, name in enumerate(path_names):
                formatted_path.append(name)
                if j < len(predicates):
                    formatted_path.append(f"-[{predicates[j]}]->")
            
            output.append(f"  {i}. {''.join(formatted_path)}")
        
        return "\n".join(output)
        
    except Exception as e:
        return f"❌ 多跳查询失败: {str(e)}"
