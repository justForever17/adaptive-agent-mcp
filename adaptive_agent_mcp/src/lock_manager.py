"""
Lock Manager - 跨进程并发控制

提供文件级别的互斥锁，确保多个 MCP 客户端同时运行时不会发生数据竞争。
"""

from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Generator
from filelock import FileLock, Timeout
from .config import config


class LockManager:
    """
    锁管理器 - 管理所有关键文件的访问锁
    
    使用方式:
        with LockManager.memory_lock():
            # 安全地读写 MEMORY.md
            pass
        
        with LockManager.knowledge_lock():
            # 安全地读写 items.json
            pass
    """
    
    _lock_dir: Optional[Path] = None
    _memory_lock: Optional[FileLock] = None
    _knowledge_lock: Optional[FileLock] = None
    _daily_log_lock: Optional[FileLock] = None
    
    @classmethod
    def _ensure_lock_dir(cls) -> Path:
        """确保锁目录存在"""
        if cls._lock_dir is None:
            cls._lock_dir = config.storage_path / ".locks"
            cls._lock_dir.mkdir(parents=True, exist_ok=True)
        return cls._lock_dir
    
    @classmethod
    def _get_memory_lock(cls) -> FileLock:
        """获取 MEMORY.md 的锁对象"""
        if cls._memory_lock is None:
            lock_path = cls._ensure_lock_dir() / "memory.lock"
            cls._memory_lock = FileLock(lock_path, timeout=10)
        return cls._memory_lock
    
    @classmethod
    def _get_knowledge_lock(cls) -> FileLock:
        """获取 knowledge/items.json 的锁对象"""
        if cls._knowledge_lock is None:
            lock_path = cls._ensure_lock_dir() / "knowledge.lock"
            cls._knowledge_lock = FileLock(lock_path, timeout=10)
        return cls._knowledge_lock
    
    @classmethod
    def _get_daily_log_lock(cls) -> FileLock:
        """获取每日日志的锁对象"""
        if cls._daily_log_lock is None:
            lock_path = cls._ensure_lock_dir() / "daily_log.lock"
            cls._daily_log_lock = FileLock(lock_path, timeout=10)
        return cls._daily_log_lock
    
    @classmethod
    @contextmanager
    def memory_lock(cls, timeout: float = 10) -> Generator[None, None, None]:
        """
        获取 MEMORY.md 的互斥锁
        
        Args:
            timeout: 等待锁的超时时间（秒），默认 10 秒
            
        Raises:
            Timeout: 如果在超时时间内无法获取锁
        """
        lock = cls._get_memory_lock()
        lock.timeout = timeout
        try:
            with lock:
                yield
        except Timeout:
            raise Timeout(f"无法获取 MEMORY.md 锁，可能有其他进程正在写入。超时: {timeout}s")
    
    @classmethod
    @contextmanager
    def knowledge_lock(cls, timeout: float = 10) -> Generator[None, None, None]:
        """
        获取 knowledge/items.json 的互斥锁
        
        Args:
            timeout: 等待锁的超时时间（秒），默认 10 秒
            
        Raises:
            Timeout: 如果在超时时间内无法获取锁
        """
        lock = cls._get_knowledge_lock()
        lock.timeout = timeout
        try:
            with lock:
                yield
        except Timeout:
            raise Timeout(f"无法获取 knowledge 锁，可能有其他进程正在写入。超时: {timeout}s")
    
    @classmethod
    @contextmanager
    def daily_log_lock(cls, timeout: float = 10) -> Generator[None, None, None]:
        """
        获取每日日志的互斥锁
        
        Args:
            timeout: 等待锁的超时时间（秒），默认 10 秒
            
        Raises:
            Timeout: 如果在超时时间内无法获取锁
        """
        lock = cls._get_daily_log_lock()
        lock.timeout = timeout
        try:
            with lock:
                yield
        except Timeout:
            raise Timeout(f"无法获取 daily_log 锁，可能有其他进程正在写入。超时: {timeout}s")
