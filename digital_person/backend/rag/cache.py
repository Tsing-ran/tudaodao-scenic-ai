"""
LRU 答案缓存。

命中条件：scenic_id + query 完全一致（忽略首尾空格和大小写）。
缓存命中直接返回，跳过 embed + 检索 + LLM，延迟从 ~2s → <5ms。
"""

import hashlib
import time
from collections import OrderedDict
from typing import Any


class LRUCache:
    def __init__(self, maxsize: int = 300, ttl_seconds: int = 3600):
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self.maxsize = maxsize
        self.ttl = ttl_seconds

    def _key(self, scenic_id: str, query: str) -> str:
        normalized = f"{scenic_id}::{query.strip().lower()}"
        return hashlib.md5(normalized.encode()).hexdigest()

    def get(self, scenic_id: str, query: str) -> Any | None:
        key = self._key(scenic_id, query)
        if key not in self._cache:
            return None
        value, ts = self._cache[key]
        if time.time() - ts > self.ttl:
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        return value

    def set(self, scenic_id: str, query: str, value: Any) -> None:
        key = self._key(scenic_id, query)
        self._cache[key] = (value, time.time())
        self._cache.move_to_end(key)
        if len(self._cache) > self.maxsize:
            self._cache.popitem(last=False)

    def invalidate(self, scenic_id: str | None = None) -> None:
        """知识库更新后调用，清空对应景区缓存。"""
        if scenic_id is None:
            self._cache.clear()
            return
        drop = [k for k, (v, _) in self._cache.items()
                if isinstance(v, dict) and v.get("scenic_id") == scenic_id]
        for k in drop:
            del self._cache[k]

    @property
    def size(self) -> int:
        return len(self._cache)


answer_cache = LRUCache(maxsize=300, ttl_seconds=3600)
