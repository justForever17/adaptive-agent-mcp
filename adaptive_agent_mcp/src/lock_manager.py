"""
Lock Manager - In-Process Concurrency Control (Serial Execution)

Replaces heavy FileLock with asyncio.Lock for single-instance efficiency.
"""

import asyncio
import threading
from contextlib import contextmanager, asynccontextmanager
from typing import Optional, Generator, AsyncGenerator

class LockManager:
    """
    Lock Manager - Manages async locks for resource access.
    
    Implementation:
    - Sync methods: No-op (assuming single-threaded execution context).
    - Async methods: asyncio.Lock (serializing async tasks).
    """

    _files_locks: dict[str, asyncio.Lock] = {}
    _global_sync_lock = threading.Lock() # Just in case

    @classmethod
    def _get_async_lock(cls, name: str) -> asyncio.Lock:
        if name not in cls._files_locks:
            cls._files_locks[name] = asyncio.Lock()
        return cls._files_locks[name]

    # --- Sync Context Managers (No-op/Threading) ---
    @classmethod
    @contextmanager
    def memory_lock(cls, timeout: float = 10) -> Generator[None, None, None]:
        """Sync lock for MEMORY.md (No-op in async event loop)"""
        # In a single-threaded async app, sync code blocks everything anyway.
        yield

    @classmethod
    @contextmanager
    def knowledge_lock(cls, timeout: float = 10) -> Generator[None, None, None]:
        """Sync lock for items.json"""
        yield

    @classmethod
    @contextmanager
    def daily_log_lock(cls, timeout: float = 10) -> Generator[None, None, None]:
        """Sync lock for daily logs"""
        yield

    # --- Async Context Managers (Asyncio.Lock) ---
    @classmethod
    @asynccontextmanager
    async def async_memory_lock(cls, timeout: float = 10) -> AsyncGenerator[None, None]:
        """Async lock for MEMORY.md"""
        lock = cls._get_async_lock("memory")
        # We ignore timeout for asyncio.lock as it's a queue, not a spinlock
        async with lock:
            yield

    @classmethod
    @asynccontextmanager
    async def async_knowledge_lock(cls, timeout: float = 10) -> AsyncGenerator[None, None]:
        """Async lock for knowledge items"""
        lock = cls._get_async_lock("knowledge")
        async with lock:
            yield

    @classmethod
    @asynccontextmanager
    async def async_daily_log_lock(cls, timeout: float = 10) -> AsyncGenerator[None, None]:
        """Async lock for daily logs"""
        lock = cls._get_async_lock("daily_log")
        async with lock:
            yield

