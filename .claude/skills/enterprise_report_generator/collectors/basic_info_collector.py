"""
基本信息收集器

获取企业官方注册信息和官网公开信息
数据源: gBizINFO API + 官网爬取 (Crawl4AI)
"""
import asyncio
import logging
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

from .base_collector import BaseCollector
from ..models import SeedData, BasicInfoRaw
from ..utils.gbizinfo_client import GBizInfoClient
from ..config import get_config

logger = logging.getLogger(__name__)


class BasicInfoCollector(BaseCollector[BasicInfoRaw]):
    """
    基本信息收集器

    收集内容:
    - gBizINFO: 法人编号验证、代表人、所在地、资本金、员工数
    - 官网: 业务内容、主要产品、公司简介
    """

    name = "BasicInfoCollector"
    cache_category = "basic_info"

    def __init__(self, use_cache: bool = True):
        super().__init__(use_cache)
        self.crawler_config = get_config().crawler

    async def collect(self, seed: SeedData) -> BasicInfoRaw:
        """
        收集基本信息

        Args:
            seed: 种子数据

        Returns:
            BasicInfoRaw
        """
        result = BasicInfoRaw()

        # 并行执行 gBizINFO 查询和官网爬取
        gbizinfo_task = self._fetch_gbizinfo(seed.corporate_number)
        website_task = self._crawl_website(seed.website_url)

        gbizinfo_data, (website_content, company_page_url) = await asyncio.gather(
            gbizinfo_task,
            website_task,
            return_exceptions=True
        )

        # 处理 gBizINFO 结果
        if isinstance(gbizinfo_data, Exception):
            self.add_error(f"gBizINFO API 错误: {gbizinfo_data}")
            result.gbizinfo_data = None
        else:
            result.gbizinfo_data = gbizinfo_data

        # 处理官网爬取结果
        if isinstance(website_content, Exception):
            self.add_error(f"官网爬取错误: {website_content}")
            result.website_content = None
            result.company_page_url = None
        else:
            result.website_content = website_content
            result.company_page_url = company_page_url

        result.errors = self.errors.copy()
        return result

    async def _fetch_gbizinfo(self, corporate_number: str) -> Optional[dict]:
        """
        从 gBizINFO API 获取企业信息

        Args:
            corporate_number: 法人番号

        Returns:
            API 返回的原始数据字典
        """
        try:
            async with GBizInfoClient() as client:
                data = await client.get_by_corporate_number(corporate_number)

                if data.error:
                    self.add_error(f"gBizINFO: {data.error}")
                    return None

                return data.raw_data

        except Exception as e:
            logger.error(f"gBizINFO API 调用失败: {e}")
            raise

    async def _crawl_website(self, website_url: str) -> tuple[Optional[str], Optional[str]]:
        """
        爬取企业官网

        Args:
            website_url: 官网 URL

        Returns:
            (网页内容, 公司简介页URL)
        """
        try:
            browser_config = BrowserConfig(
                headless=True,
                verbose=False,
            )

            crawler_config = CrawlerRunConfig(
                word_count_threshold=50,
                remove_overlay_elements=True,
            )

            async with AsyncWebCrawler(config=browser_config) as crawler:
                # 首先爬取首页
                result = await crawler.arun(
                    url=website_url,
                    config=crawler_config,
                )

                if not result.success:
                    self.add_error(f"官网首页爬取失败: {website_url}")
                    return None, None

                main_content = result.markdown

                # 尝试找到公司简介页面
                company_page_url = self._find_company_page_url(
                    website_url,
                    result.links.get("internal", [])
                )

                if company_page_url and company_page_url != website_url:
                    # 爬取公司简介页
                    await asyncio.sleep(self.crawler_config.delay_between_requests)

                    about_result = await crawler.arun(
                        url=company_page_url,
                        config=crawler_config,
                    )

                    if about_result.success:
                        # 合并内容
                        main_content = f"{main_content}\n\n---\n\n{about_result.markdown}"

                return main_content, company_page_url

        except Exception as e:
            logger.error(f"官网爬取失败: {e}")
            raise

    def _find_company_page_url(
        self,
        base_url: str,
        internal_links: list
    ) -> Optional[str]:
        """
        从内部链接中找到公司简介页面

        Args:
            base_url: 基础 URL
            internal_links: 内部链接列表

        Returns:
            公司简介页 URL
        """
        # 公司简介页面的常见路径模式
        about_patterns = [
            r'/about/?$',
            r'/company/?$',
            r'/corporate/?$',
            r'/about[-_]us/?$',
            r'/who[-_]we[-_]are/?$',
            r'/会社概要/?$',
            r'/企業情報/?$',
            r'/会社情報/?$',
            r'/corporate/about/?$',
            r'/company/about/?$',
            r'/ja/about/?$',
            r'/ja/company/?$',
        ]

        # 遍历链接寻找匹配
        for link in internal_links:
            href = link.get("href", "") if isinstance(link, dict) else str(link)

            for pattern in about_patterns:
                if re.search(pattern, href, re.IGNORECASE):
                    # 确保是完整 URL
                    if href.startswith("http"):
                        return href
                    else:
                        return urljoin(base_url, href)

        return None

    def _get_empty_result(self) -> BasicInfoRaw:
        """返回空结果"""
        return BasicInfoRaw(errors=self.errors.copy())

    def _deserialize(self, data: dict) -> BasicInfoRaw:
        """从缓存反序列化"""
        return BasicInfoRaw(**data)


# ============================================================
# 便捷函数
# ============================================================

async def collect_basic_info(seed: SeedData, use_cache: bool = True) -> BasicInfoRaw:
    """
    收集基本信息的便捷函数

    Args:
        seed: 种子数据
        use_cache: 是否使用缓存

    Returns:
        BasicInfoRaw
    """
    collector = BasicInfoCollector(use_cache=use_cache)
    return await collector.run(seed)


if __name__ == "__main__":
    # 测试
    async def test():
        print("=== BasicInfoCollector 测试 ===\n")

        seed = SeedData(
            company_name="Sparticle株式会社",
            corporate_number="4120001222866",
            website_url="https://www.sparticle.com/ja",
        )

        result = await collect_basic_info(seed, use_cache=False)

        print(f"gBizINFO 数据: {'有' if result.gbizinfo_data else '无'}")
        print(f"官网内容: {'有' if result.website_content else '无'}")
        print(f"公司简介页: {result.company_page_url}")
        print(f"错误: {result.errors}")

        if result.gbizinfo_data:
            print(f"\n--- gBizINFO 数据 ---")
            for key, value in result.gbizinfo_data.items():
                if value:
                    print(f"  {key}: {value}")

        if result.website_content:
            print(f"\n--- 官网内容预览 (前500字) ---")
            print(result.website_content[:500])

    asyncio.run(test())
