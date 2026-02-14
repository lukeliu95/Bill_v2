"""
收集器基类

所有数据收集器的抽象基类
"""
import logging
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional
from datetime import datetime

from ..models import SeedData
from ..utils.cache import get_cache

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseCollector(ABC, Generic[T]):
    """
    数据收集器基类

    所有收集器继承此类，实现 collect 方法
    """

    # 子类需要定义
    name: str = "base"
    cache_category: str = "default"

    def __init__(self, use_cache: bool = True):
        """
        初始化收集器

        Args:
            use_cache: 是否使用缓存
        """
        self.use_cache = use_cache
        self.cache = get_cache() if use_cache else None
        self.errors: list[str] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    @abstractmethod
    async def collect(self, seed: SeedData) -> T:
        """
        收集数据

        Args:
            seed: 种子数据

        Returns:
            收集到的数据
        """
        pass

    async def run(self, seed: SeedData) -> T:
        """
        运行收集器 (带缓存和日志)

        Args:
            seed: 种子数据

        Returns:
            收集到的数据
        """
        self.errors = []
        self.start_time = datetime.now()

        logger.info(f"[{self.name}] 开始收集: {seed.company_name}")

        # 检查缓存
        cache_key = self._get_cache_key(seed)
        if self.use_cache and self.cache:
            cached_data = self.cache.get(self.cache_category, cache_key)
            if cached_data is not None:
                logger.info(f"[{self.name}] 缓存命中")
                self.end_time = datetime.now()
                return self._deserialize(cached_data)

        # 执行收集
        try:
            result = await self.collect(seed)

            # 写入缓存
            if self.use_cache and self.cache and not self.errors:
                serialized = self._serialize(result)
                self.cache.set(self.cache_category, cache_key, serialized)

        except Exception as e:
            logger.error(f"[{self.name}] 收集失败: {e}")
            self.errors.append(str(e))
            result = self._get_empty_result()

        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        logger.info(f"[{self.name}] 收集完成 (耗时: {duration:.2f}s, 错误: {len(self.errors)})")

        return result

    def _get_cache_key(self, seed: SeedData) -> str:
        """
        生成缓存键

        Args:
            seed: 种子数据

        Returns:
            缓存键
        """
        return seed.corporate_number

    def _serialize(self, data: T) -> dict:
        """
        序列化数据用于缓存

        Args:
            data: 收集到的数据

        Returns:
            可JSON序列化的字典
        """
        if hasattr(data, "model_dump"):
            return data.model_dump()
        return dict(data) if isinstance(data, dict) else {"value": data}

    def _deserialize(self, data: dict) -> T:
        """
        从缓存反序列化数据

        Args:
            data: 缓存的字典数据

        Returns:
            原始数据类型
        """
        # 子类可以覆盖此方法进行更精确的反序列化
        return data  # type: ignore

    @abstractmethod
    def _get_empty_result(self) -> T:
        """
        获取空结果 (用于错误时返回)

        Returns:
            空的结果对象
        """
        pass

    def add_error(self, error: str):
        """添加错误信息"""
        self.errors.append(error)
        logger.warning(f"[{self.name}] {error}")

    @property
    def duration_seconds(self) -> Optional[float]:
        """获取执行时长(秒)"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


class CollectorResult:
    """收集器结果包装"""

    def __init__(
        self,
        data: any,
        errors: list[str] = None,
        duration: float = None,
        from_cache: bool = False
    ):
        self.data = data
        self.errors = errors or []
        self.duration = duration
        self.from_cache = from_cache
        self.collected_at = datetime.now()

    @property
    def success(self) -> bool:
        """是否成功 (无错误)"""
        return len(self.errors) == 0

    @property
    def partial(self) -> bool:
        """是否部分成功 (有数据但也有错误)"""
        return self.data is not None and len(self.errors) > 0
