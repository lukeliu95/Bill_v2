"""
销售情报收集器

获取用于销售路径分析的原始情报
数据源: Serper 搜索 + 官网团队页面爬取 + LinkedIn (可选)
"""
import asyncio
import logging
import re
from typing import Optional
from urllib.parse import urljoin

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

from .base_collector import BaseCollector
from ..models import SeedData, SalesIntelRaw
from ..utils.serper_client import SerperClient, SerperResponse
from ..config import get_config

logger = logging.getLogger(__name__)


class SalesIntelCollector(BaseCollector[SalesIntelRaw]):
    """
    销售情报收集器

    收集内容:
    - 搜索引擎: 高管信息、组织结构
    - 官网: 团队页面、关于我们页面
    - LinkedIn: 公司公开信息 (通过搜索) + 深度采集 (通过 Bright Data)
    """

    name = "SalesIntelCollector"
    cache_category = "sales_intel"

    def __init__(self, use_cache: bool = True, enable_linkedin: bool = True):
        """
        初始化销售情报收集器

        Args:
            use_cache: 是否使用缓存
            enable_linkedin: 是否启用 LinkedIn 深度采集
        """
        super().__init__(use_cache)
        self.crawler_config = get_config().crawler
        self.enable_linkedin = enable_linkedin
        self._config = get_config()

    async def collect(self, seed: SeedData) -> SalesIntelRaw:
        """
        收集销售情报

        Args:
            seed: 种子数据

        Returns:
            SalesIntelRaw
        """
        result = SalesIntelRaw()

        # 构建并行任务列表
        tasks = [
            self._search_sales_intel(seed.company_name),
            self._crawl_team_page(seed.website_url),
        ]

        # 如果启用 LinkedIn 深度采集，添加到并行任务
        linkedin_task_idx = None
        if self.enable_linkedin and self._config.has_linkedin_config():
            linkedin_task_idx = len(tasks)
            tasks.append(self._collect_linkedin_profiles(seed))

        # 并行执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)

        search_results = results[0]
        team_content = results[1]

        # 处理搜索结果
        if isinstance(search_results, Exception):
            self.add_error(f"搜索错误: {search_results}")
        else:
            result.executives_search_results = search_results.get("executives", [])
            result.organization_search_results = search_results.get("organization", [])
            result.linkedin_data = search_results.get("linkedin", {})

        # 处理团队页面爬取结果
        if isinstance(team_content, Exception):
            self.add_error(f"团队页面爬取错误: {team_content}")
        else:
            result.team_page_content = team_content

        # 处理 LinkedIn 深度采集结果
        if linkedin_task_idx is not None:
            linkedin_result = results[linkedin_task_idx]
            if isinstance(linkedin_result, Exception):
                self.add_error(f"LinkedIn 深度采集错误: {linkedin_result}")
            else:
                result.linkedin_profiles = linkedin_result

        result.errors = self.errors.copy()
        return result

    async def _collect_linkedin_profiles(self, seed: SeedData) -> Optional[dict]:
        """
        通过 Bright Data 收集 LinkedIn 深度资料

        Args:
            seed: 种子数据

        Returns:
            LinkedIn 采集结果字典
        """
        try:
            from .linkedin_collector import LinkedInCollector

            collector = LinkedInCollector(self._config)
            linkedin_data = await collector.collect(seed)

            if linkedin_data.collection_status == "failed":
                self.add_error(f"LinkedIn 采集失败: {linkedin_data.error_message}")
                return None

            # 转换为可序列化的字典
            return {
                "company_linkedin_url": linkedin_data.company_linkedin_url,
                "company_profile": self._serialize_company_profile(linkedin_data.company_profile),
                "key_persons": [self._serialize_person(p) for p in linkedin_data.key_persons],
                "employee_count": len(linkedin_data.all_employees),
                "collection_status": linkedin_data.collection_status,
            }

        except Exception as e:
            logger.error(f"LinkedIn 采集异常: {e}")
            return None

    @staticmethod
    def _serialize_company_profile(profile) -> Optional[dict]:
        """序列化公司 LinkedIn 资料"""
        if not profile:
            return None
        return {
            "name": profile.name,
            "description": profile.description,
            "industry": profile.industry,
            "company_size": profile.company_size,
            "headquarters": profile.headquarters,
            "founded": profile.founded,
            "website": profile.website,
        }

    @staticmethod
    def _serialize_person(person) -> dict:
        """序列化个人 LinkedIn 资料"""
        return {
            "name": person.name,
            "title": person.title,
            "company": person.company,
            "location": person.location,
            "summary": person.summary,
            "experience": person.experience[:3] if person.experience else [],  # 最近3段经历
            "education": person.education[:2] if person.education else [],  # 最近2段教育
            "skills": person.skills[:10] if person.skills else [],  # 前10个技能
            "linkedin_url": person.linkedin_url,
        }

    async def _search_sales_intel(self, company_name: str) -> dict:
        """
        搜索销售相关情报

        Args:
            company_name: 企业名称

        Returns:
            搜索结果字典
        """
        results = {
            "executives": [],
            "organization": [],
            "linkedin": {},
        }

        # 定义搜索查询
        queries = [
            (f"{company_name} 役員 OR 経営陣 OR 代表取締役 OR CEO OR CTO", "executives"),
            (f"{company_name} 組織図 OR 組織体制 OR 部署構成", "organization"),
            (f"site:linkedin.com {company_name}", "linkedin"),
        ]

        async with SerperClient() as client:
            for query, result_type in queries:
                try:
                    response = await client.search(query, num_results=10)

                    if response.error:
                        self.add_error(f"搜索 '{result_type}' 失败: {response.error}")
                        continue

                    # 转换为字典列表
                    items = []
                    for r in response.results:
                        items.append({
                            "title": r.title,
                            "link": r.link,
                            "snippet": r.snippet,
                            "position": r.position,
                        })

                    if result_type == "linkedin":
                        results["linkedin"] = {
                            "query": query,
                            "results": items,
                        }
                    else:
                        results[result_type] = items

                    # 请求间隔
                    await asyncio.sleep(0.5)

                except Exception as e:
                    self.add_error(f"搜索 '{result_type}' 异常: {e}")

        return results

    async def _crawl_team_page(self, website_url: str) -> Optional[str]:
        """
        爬取团队/关于我们页面

        Args:
            website_url: 官网 URL

        Returns:
            页面内容
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
                # 先获取首页链接
                result = await crawler.arun(
                    url=website_url,
                    config=crawler_config,
                )

                if not result.success:
                    self.add_error(f"首页爬取失败: {website_url}")
                    return None

                # 找到团队相关页面
                team_urls = self._find_team_page_urls(
                    website_url,
                    result.links.get("internal", [])
                )

                if not team_urls:
                    logger.info("未找到团队页面链接")
                    return None

                # 爬取团队页面
                all_content = []
                for url in team_urls[:3]:  # 最多爬取3个相关页面
                    await asyncio.sleep(self.crawler_config.delay_between_requests)

                    team_result = await crawler.arun(
                        url=url,
                        config=crawler_config,
                    )

                    if team_result.success:
                        all_content.append(f"## {url}\n\n{team_result.markdown}")

                return "\n\n---\n\n".join(all_content) if all_content else None

        except Exception as e:
            logger.error(f"团队页面爬取失败: {e}")
            raise

    def _find_team_page_urls(
        self,
        base_url: str,
        internal_links: list
    ) -> list[str]:
        """
        从内部链接中找到团队相关页面

        Args:
            base_url: 基础 URL
            internal_links: 内部链接列表

        Returns:
            团队页面 URL 列表
        """
        # 团队页面的常见路径模式
        team_patterns = [
            r'/team/?$',
            r'/members/?$',
            r'/people/?$',
            r'/leadership/?$',
            r'/management/?$',
            r'/executives/?$',
            r'/about[-_]us/team/?',
            r'/company/team/?',
            r'/メンバー/?$',
            r'/チーム/?$',
            r'/経営陣/?$',
            r'/役員紹介/?$',
            r'/company/members/?',
            r'/ja/team/?$',
            r'/ja/members/?$',
        ]

        found_urls = []

        for link in internal_links:
            href = link.get("href", "") if isinstance(link, dict) else str(link)

            for pattern in team_patterns:
                if re.search(pattern, href, re.IGNORECASE):
                    # 确保是完整 URL
                    if href.startswith("http"):
                        full_url = href
                    else:
                        full_url = urljoin(base_url, href)

                    if full_url not in found_urls:
                        found_urls.append(full_url)
                    break

        return found_urls

    def _get_empty_result(self) -> SalesIntelRaw:
        """返回空结果"""
        return SalesIntelRaw(errors=self.errors.copy())

    def _deserialize(self, data: dict) -> SalesIntelRaw:
        """从缓存反序列化"""
        return SalesIntelRaw(**data)


# ============================================================
# 便捷函数
# ============================================================

async def collect_sales_intel(
    seed: SeedData,
    use_cache: bool = True,
    enable_linkedin: bool = True
) -> SalesIntelRaw:
    """
    收集销售情报的便捷函数

    Args:
        seed: 种子数据
        use_cache: 是否使用缓存
        enable_linkedin: 是否启用 LinkedIn 深度采集

    Returns:
        SalesIntelRaw
    """
    collector = SalesIntelCollector(use_cache=use_cache, enable_linkedin=enable_linkedin)
    return await collector.run(seed)


if __name__ == "__main__":
    # 测试
    async def test():
        print("=== SalesIntelCollector 测试 ===\n")

        seed = SeedData(
            company_name="Sparticle株式会社",
            corporate_number="4120001222866",
            website_url="https://www.sparticle.com/ja",
        )

        result = await collect_sales_intel(seed, use_cache=False)

        print(f"高管搜索结果: {len(result.executives_search_results)} 条")
        print(f"组织搜索结果: {len(result.organization_search_results)} 条")
        print(f"LinkedIn数据: {'有' if result.linkedin_data else '无'}")
        print(f"团队页面内容: {'有' if result.team_page_content else '无'}")
        print(f"错误: {result.errors}")

        if result.executives_search_results:
            print(f"\n--- 高管搜索结果 (前3条) ---")
            for item in result.executives_search_results[:3]:
                print(f"  - {item['title']}")
                print(f"    {item['snippet'][:100]}...")

    asyncio.run(test())
