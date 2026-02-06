from typing import List, Optional
import os
import re
from pathlib import Path
from ...server import mcp
from ..config import config
from ..search_engine import SearchEngine
from ..indexer import indexer

# Regex to capture YAML frontmatter (simplified)
YAML_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL | re.MULTILINE)

@mcp.tool()
def query_memory_headers(tags: Optional[List[str]] = None, limit: int = 50) -> str:
    """
    **索引扫描** - 快速查找记忆文件的"目录"，不读取完整内容。
    
    ## 使用场景
    当用户问：
    - "之前我们讨论过什么？"
    - "上个月关于 Next.js 的记录在哪？"
    - "有没有关于 Docker 的笔记？"
    
    ## 工作流程
    1. 调用 `query_memory_headers(tags=['nextjs'])` 按标签过滤
    2. 系统返回匹配文件的 **摘要信息**（日期、标签、类型）
    3. 分析摘要，确定需要读取哪些文件
    4. 对感兴趣的文件调用 `read_memory_content` 获取完整内容
    
    ## 参数说明
    - `tags`: 按标签过滤，如 `['development', 'nextjs']`
    - `limit`: 最大返回数量，默认 50
    
    ## 返回格式
    每个匹配文件返回：文件路径、类型、日期、标签、摘要
    """
    results = []
    # Load from persistent JSON Cache (O(1))
    index_data = indexer.load_index()
    memory_root = config.storage_path / "memory"
    
    count = 0
    for rel_path, meta in index_data.items():
        if tags:
            # Check if any requested tag is in file's tags
            file_tags = meta.get("tags", [])
            if not isinstance(file_tags, list): file_tags = []
            
            if not any(tag in file_tags for tag in tags):
                continue
        
        full_path = memory_root / rel_path
        header_summary = f"Type: {meta.get('type')}\nDate: {meta.get('date')}\nTags: {meta.get('tags')}\nSummary: {meta.get('summary')}"
        results.append(f"File: {full_path}\nHeader:\n{header_summary}\n---")
        
        count += 1
        if count >= limit:
            break
            
    return "\n\n".join(results) if results else "No matching headers found."

@mcp.tool()
def read_memory_content(file_paths: List[str]) -> str:
    """
    **文件读取器** - 获取指定记忆文件的完整 Markdown 内容。
    
    ## 使用场景
    - 从 `query_memory_headers` 获取文件路径后，需要查看具体内容
    - 从 `search_memory_content` 找到匹配后，需要完整上下文
    
    ## 参数说明
    - `file_paths`: 文件绝对路径列表，如 `["/path/to/2026-02-01.md"]`
    
    ## 注意事项
    - **节省上下文**: 只读取真正需要的文件，不要一次读取太多
    - **安全限制**: 只能读取记忆存储目录内的文件
    
    ## 返回格式
    每个文件返回完整的 Markdown 内容，带有文件名标题
    """
    outputs = []
    for path_str in file_paths:
        path = Path(path_str)
        if not path.exists():
            outputs.append(f"Error: File not found: {path_str}")
            continue
            
        # Security check: Ensure path is within storage_path
        try:
            path.resolve().relative_to(config.storage_path.resolve())
            tokens = path.read_text(encoding="utf-8")
            outputs.append(f"=== CONTENT OF {path.name} ===\n{tokens}")
        except ValueError:
            outputs.append(f"Error: Access denied for file outside memory storage: {path_str}")
            
    return "\n\n".join(outputs)


@mcp.tool()
def search_memory_content(query: str, regex: bool = False, limit: int = 20) -> str:
    """
    **全文搜索** - 在所有记忆文件中搜索关键词或模式。
    
    ## 使用场景
    当 `query_memory_headers` 无法定位时：
    - "有没有提到过 'ECONNREFUSED' 错误？"
    - "之前解决 CORS 问题的记录在哪？"
    - "搜索所有包含 'TypeScript' 的笔记"
    
    ## 参数说明
    - `query`: 搜索关键词，如 "CORS" 或 "用户认证"
    - `regex`: 是否使用正则表达式，默认 False
    - `limit`: 最大返回结果数，默认 20（防止 Context Window 爆炸）
    
    ## 搜索引擎
    使用 ripgrep (rg) 进行高速搜索，支持：
    - 大小写不敏感匹配
    - 显示匹配行的上下文
    - 自动截断过长输出
    
    ## 返回格式
    匹配的文件路径、行号、以及周围的上下文内容
    
    ## 依赖说明
    需要安装 ripgrep，若未安装会返回错误提示
    """
    engine = SearchEngine(config.storage_path)
    if not engine.is_available:
        return "Error: 'rg' (ripgrep) not configured or found. Please install ripgrep."
        
    return engine.search(query, regex=regex, limit=limit)

