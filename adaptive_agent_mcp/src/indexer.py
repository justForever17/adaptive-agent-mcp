
import os
import json
import re
import hashlib
import logging
import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

import yaml
from .config import config
from .vector_store import get_vector_store
from .services.embedding import EmbeddingService
from .router import KnowledgeRouter

YAML_FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)

logger = logging.getLogger("adaptive-agent-mcp")
HEADER_CHUNK_RE = re.compile(r'(^|\n)(?P<header>#{1,6}\s+.*?)(\n|$)', re.MULTILINE)

class Indexer:
    def __init__(self):
        self.memory_dir = config.storage_path / "memory"
        self.index_file = config.storage_path / ".index" / "memory_index.json"
        self._build_lock = asyncio.Lock()
        
    def _compute_hash(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()
        
    async def _load_index(self) -> Dict[str, Any]:
        if not self.index_file.exists():
            return {"files": {}, "items": {}}
        try:
            async with aiofiles.open(self.index_file, mode='r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except Exception:
            return {"files": {}, "items": {}}
            
    async def _save_index(self, data: Dict[str, Any]):
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(self.index_file, mode='w', encoding='utf-8') as f:
            await f.write(json.dumps(data, indent=2, ensure_ascii=False))

    async def build_index(self, force_full: bool = False):
        """
        Async Incremental Indexing with Smart Chunking & Vectorization.
        Guarded by asyncio.Lock to prevent concurrent corruption.
        """
        if self._build_lock.locked():
            logger.info("Indexing already in progress, skipping.")
            return
        
        async with self._build_lock:
            await self._do_build_index(force_full)

    async def _do_build_index(self, force_full: bool = False):
        """Internal: actual indexing logic."""
        logger.info("Starting Async Indexing...")
        index_data = await self._load_index()
        files_index = index_data.get("files", {})
        items_index = index_data.get("items", {}) # Track ID -> hash
        
        vector_store = get_vector_store()
        
        try:
            embed_service = EmbeddingService.get_instance()
            can_embed = True
        except ValueError as e:
            logger.info(f"Embedding service unavailable: {e}")
            can_embed = False
        except Exception as e:
             logger.warning(f"Embedding service error: {e}")
             can_embed = False

        # 1. Process Markdown Logs (Files)
        walk_result = await asyncio.to_thread(lambda: list(os.walk(self.memory_dir)))
        for root, _, files in walk_result:
            for file in files:
                if not file.endswith(".md"):
                    continue
                    
                path = Path(root) / file
                rel_path = str(path.relative_to(self.memory_dir)).replace("\\", "/")
                
                # Check modification time
                current_mtime = path.stat().st_mtime
                cached_data = files_index.get(rel_path, {})
                
                if not force_full and cached_data.get("mtime") == current_mtime:
                    continue  # Skip unchanged
                
                logger.debug(f"Indexing File: {rel_path}")
                try:
                    async with aiofiles.open(path, mode='r', encoding='utf-8') as f:
                        content = await f.read()
                        
                    # Metadata Extraction
                    metadata = {}
                    match = YAML_FRONTMATTER_RE.match(content)
                    body_content = content
                    if match:
                        try:
                            metadata = yaml.safe_load(match.group(1)) or {}
                            body_content = content[match.end():]
                        except Exception:
                            pass
                            
                    # Update File Index
                    files_index[rel_path] = {
                        "mtime": current_mtime,
                        "metadata": metadata
                    }
                    
                    if can_embed:
                        # Smart Chunking
                        # Split by H2/H3 headers or just paragraphs if standard
                        # For daily logs (### HH:MM), we treat each entry as a chunk
                        chunks = self._chunk_markdown(body_content, rel_path, metadata)
                        
                        embeddings = await embed_service.embed_documents([c["text"] for c in chunks])
                        
                        for i, chunk in enumerate(chunks):
                            await vector_store.async_add(
                                doc_id=chunk["id"],
                                content=chunk["text"],
                                embedding=embeddings[i],
                                metadata=chunk["metadata"]
                            )
                            
                except Exception as e:
                    logger.warning(f"Error indexing {rel_path}: {e}")

        # 2. Process Knowledge Items (Atomic Facts)
        # Search all partitions via Router
        partition_files = KnowledgeRouter.get_all_partition_files()
        
        for p_file in partition_files:
            try:
                # Read synchronous here? Or async? Async is better.
                if not p_file.exists():
                     continue
                     
                async with aiofiles.open(p_file, mode='r', encoding='utf-8') as f:
                    content = await f.read()
                    items = json.loads(content)
                    
                new_items_to_embed = []
                new_item_indices = []
                
                for i, item in enumerate(items):
                    if item.get("status") != "active":
                        continue
                        
                    item_id = item.get("id")
                    if not item_id: continue
                    
                    fact_text = item.get("fact", "")
                    current_hash = self._compute_hash(fact_text)
                    
                    # Check if Changed
                    cached_item = items_index.get(item_id)
                    if not force_full and cached_item and cached_item.get("hash") == current_hash:
                        continue
                    
                    if can_embed:
                        new_items_to_embed.append(fact_text)
                        new_item_indices.append(i)
                        
                        # Update Index
                        items_index[item_id] = {
                            "hash": current_hash,
                            "updated_at": datetime.now().isoformat()
                        }
                
                # Batch Embed
                if new_items_to_embed and can_embed:
                    logger.debug(f"Embedding {len(new_items_to_embed)} items from {p_file.name}")
                    embeddings = await embed_service.embed_documents(new_items_to_embed)
                    
                    for idx, emb in zip(new_item_indices, embeddings):
                        item = items[idx]
                        await vector_store.async_add(
                            doc_id=item["id"],
                            content=item["fact"],
                            embedding=emb,
                            metadata={
                                "category": item.get("category"),
                                "scope": item.get("scope"),
                                "source": str(p_file)
                            }
                        )

            except Exception as e:
                logger.warning(f"Error indexing items in {p_file}: {e}")

        # Save Updated Index
        await self._save_index({"files": files_index, "items": items_index})
        logger.info("Indexing Complete.")
        
    def _chunk_markdown(self, content: str, source: str, metadata: Dict) -> List[Dict]:
        """Split markdown content into semantic chunks."""
        chunks = []
        lines = content.split('\n')
        current_chunk = []
        current_header = "Start"
        
        for line in lines:
            if re.match(r'^#{1,6}\s+', line):
                if current_chunk:
                    text = "\n".join(current_chunk).strip()
                    if text:
                        chunks.append({
                            "id": f"{source}#{self._compute_hash(text)[:8]}",
                            "text": f"[{current_header}] {text}",
                            "metadata": {**metadata, "source": source, "header": current_header}
                        })
                current_chunk = []
                current_header = line.strip().lstrip('#').strip()
            
            current_chunk.append(line)
            
        if current_chunk:
            text = "\n".join(current_chunk).strip()
            if text:
                chunks.append({
                    "id": f"{source}#{self._compute_hash(text)[:8]}",
                    "text": f"[{current_header}] {text}",
                    "metadata": {**metadata, "source": source, "header": current_header}
                })
                
        return chunks

# Singleton Instance
indexer = Indexer()
