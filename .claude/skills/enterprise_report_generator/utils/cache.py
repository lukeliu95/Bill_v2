"""
缓存工具

轻量级文件缓存，支持 TTL
"""
import json
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any, TypeVar, Generic
from dataclasses import dataclass

from ..config import get_config, CacheConfig

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """缓存条目"""
    key: str
    value: T
    created_at: datetime
    expires_at: datetime
    hit: bool = False


class FileCache:
    """文件缓存"""

    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or get_config().cache
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        if self.config.enabled:
            self.config.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        # 使用 hash 避免文件名过长或包含非法字符
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.config.cache_dir / f"{key_hash}.json"

    def _make_key(self, category: str, identifier: str) -> str:
        """生成缓存键"""
        return f"{category}:{identifier}"

    def get(self, category: str, identifier: str) -> Optional[Any]:
        """
        获取缓存

        Args:
            category: 缓存类别 (basic_info/website/search/ai)
            identifier: 标识符

        Returns:
            缓存的值，如果不存在或过期则返回 None
        """
        if not self.config.enabled:
            return None

        key = self._make_key(category, identifier)
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            logger.debug(f"Cache miss: {key}")
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            expires_at = datetime.fromisoformat(data["expires_at"])

            if datetime.now() > expires_at:
                logger.debug(f"Cache expired: {key}")
                cache_path.unlink()  # 删除过期缓存
                return None

            logger.debug(f"Cache hit: {key}")
            return data["value"]

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Cache read error for {key}: {e}")
            return None

    def set(
        self,
        category: str,
        identifier: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        设置缓存

        Args:
            category: 缓存类别
            identifier: 标识符
            value: 要缓存的值
            ttl_seconds: TTL 秒数，默认使用配置

        Returns:
            是否成功
        """
        if not self.config.enabled:
            return False

        # 确定 TTL
        if ttl_seconds is None:
            ttl_seconds = self._get_default_ttl(category)

        key = self._make_key(category, identifier)
        cache_path = self._get_cache_path(key)

        now = datetime.now()
        expires_at = now + timedelta(seconds=ttl_seconds)

        data = {
            "key": key,
            "value": value,
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
        }

        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            logger.debug(f"Cache set: {key} (TTL: {ttl_seconds}s)")
            return True

        except Exception as e:
            logger.error(f"Cache write error for {key}: {e}")
            return False

    def delete(self, category: str, identifier: str) -> bool:
        """
        删除缓存

        Args:
            category: 缓存类别
            identifier: 标识符

        Returns:
            是否成功删除
        """
        key = self._make_key(category, identifier)
        cache_path = self._get_cache_path(key)

        if cache_path.exists():
            cache_path.unlink()
            logger.debug(f"Cache deleted: {key}")
            return True

        return False

    def clear(self, category: Optional[str] = None) -> int:
        """
        清空缓存

        Args:
            category: 指定类别，None 则清空所有

        Returns:
            删除的缓存数量
        """
        if not self.config.cache_dir.exists():
            return 0

        count = 0
        for cache_file in self.config.cache_dir.glob("*.json"):
            try:
                if category:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if not data.get("key", "").startswith(f"{category}:"):
                        continue

                cache_file.unlink()
                count += 1
            except Exception:
                pass

        logger.info(f"Cache cleared: {count} entries")
        return count

    def cleanup_expired(self) -> int:
        """
        清理过期缓存

        Returns:
            清理的缓存数量
        """
        if not self.config.cache_dir.exists():
            return 0

        count = 0
        now = datetime.now()

        for cache_file in self.config.cache_dir.glob("*.json"):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                expires_at = datetime.fromisoformat(data["expires_at"])
                if now > expires_at:
                    cache_file.unlink()
                    count += 1
            except Exception:
                # 无法读取的文件也删除
                cache_file.unlink()
                count += 1

        logger.info(f"Expired cache cleaned: {count} entries")
        return count

    def _get_default_ttl(self, category: str) -> int:
        """获取默认 TTL"""
        ttl_map = {
            "basic_info": self.config.basic_info_ttl,
            "website": self.config.website_content_ttl,
            "search": self.config.search_results_ttl,
            "ai": self.config.ai_analysis_ttl,
        }
        return ttl_map.get(category, self.config.search_results_ttl)

    def stats(self) -> dict:
        """
        获取缓存统计

        Returns:
            统计信息字典
        """
        if not self.config.cache_dir.exists():
            return {"total": 0, "expired": 0, "valid": 0, "size_bytes": 0}

        total = 0
        expired = 0
        valid = 0
        size_bytes = 0
        now = datetime.now()

        for cache_file in self.config.cache_dir.glob("*.json"):
            total += 1
            size_bytes += cache_file.stat().st_size

            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                expires_at = datetime.fromisoformat(data["expires_at"])
                if now > expires_at:
                    expired += 1
                else:
                    valid += 1
            except Exception:
                expired += 1

        return {
            "total": total,
            "expired": expired,
            "valid": valid,
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / 1024 / 1024, 2),
        }


# ============================================================
# 全局缓存实例
# ============================================================

_cache: Optional[FileCache] = None


def get_cache() -> FileCache:
    """获取全局缓存实例"""
    global _cache
    if _cache is None:
        _cache = FileCache()
    return _cache


# ============================================================
# 便捷函数
# ============================================================

def cache_get(category: str, identifier: str) -> Optional[Any]:
    """获取缓存"""
    return get_cache().get(category, identifier)


def cache_set(
    category: str,
    identifier: str,
    value: Any,
    ttl_seconds: Optional[int] = None
) -> bool:
    """设置缓存"""
    return get_cache().set(category, identifier, value, ttl_seconds)


def cache_delete(category: str, identifier: str) -> bool:
    """删除缓存"""
    return get_cache().delete(category, identifier)


# ============================================================
# 缓存装饰器
# ============================================================

def cached(category: str, key_func=None, ttl_seconds: Optional[int] = None):
    """
    缓存装饰器

    Args:
        category: 缓存类别
        key_func: 生成缓存键的函数，接收与被装饰函数相同的参数
        ttl_seconds: TTL 秒数

    Example:
        @cached("search", key_func=lambda query: query)
        async def search(query: str):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                identifier = key_func(*args, **kwargs)
            else:
                identifier = str(args) + str(kwargs)

            # 尝试从缓存获取
            cached_value = cache_get(category, identifier)
            if cached_value is not None:
                return cached_value

            # 执行函数
            result = await func(*args, **kwargs)

            # 写入缓存
            cache_set(category, identifier, result, ttl_seconds)

            return result

        return wrapper
    return decorator


if __name__ == "__main__":
    # 测试
    print("=== 缓存工具测试 ===\n")

    cache = FileCache()

    # 测试设置和获取
    cache.set("test", "key1", {"name": "テスト", "value": 123})
    result = cache.get("test", "key1")
    print(f"设置并获取: {result}")

    # 测试统计
    stats = cache.stats()
    print(f"缓存统计: {stats}")

    # 清理测试数据
    cache.delete("test", "key1")
    print("测试缓存已清理")
