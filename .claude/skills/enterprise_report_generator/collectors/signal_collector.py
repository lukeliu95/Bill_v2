"""
商机信号收集器

获取企业近期动态和商机信号
数据源: Serper 搜索 (新闻/融资/招聘) + PR TIMES + 新闻全文爬取
"""
import asyncio
import logging
from typing import Optional
from datetime import datetime
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

from .base_collector import BaseCollector
from ..models import SeedData, SignalsRaw
from ..utils.serper_client import SerperClient
from ..config import get_config

logger = logging.getLogger(__name__)

# ============================================================
# 新闻 URL 过滤规则
# ============================================================

NEWS_DOMAINS = [
    # PR 平台
    "prtimes.jp",
    "prwire.com",
    "atpress.ne.jp",
    # 科技/创业媒体
    "techcrunch.com",
    "thebridge.jp",
    "initial.inc",
    "startuptimes.jp",
    "venturetimes.jp",
    # 商业媒体
    "nikkei.com",
    "toyokeizai.net",
    "diamond.jp",
    "newspicks.com",
    "itmedia.co.jp",
    "zdnet.com",
    # 行业媒体
    "callcenter-japan.com",
    "markezine.jp",
    "ferret-plus.com",
]

EXCLUDED_DOMAINS = [
    "linkedin.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "youtube.com",
    "wantedly.com",
    "green-japan.com",
]

NEWS_PATH_PATTERNS = [
    "/news/", "/press/", "/article/", "/articles/",
    "/release/", "/releases/", "/blog/", "/topics/",
    "/story/", "/stories/", "/post/", "/posts/",
]


class SignalCollector(BaseCollector[SignalsRaw]):
    """
    商机信号收集器

    收集内容:
    - 新闻搜索: 企业近期新闻
    - 融资搜索: 融资相关新闻
    - PR TIMES: 官方新闻稿
    - 招聘搜索: 当前招聘信息
    """

    name = "SignalCollector"
    cache_category = "signals"

    def __init__(self, use_cache: bool = True):
        super().__init__(use_cache)
        self.crawler_config = get_config().crawler

    async def collect(self, seed: SeedData) -> SignalsRaw:
        """
        收集商机信号

        Args:
            seed: 种子数据

        Returns:
            SignalsRaw
        """
        result = SignalsRaw()
        config = get_config()

        # 并行执行所有搜索
        tasks = [
            self._search_news(seed.company_name),
            self._search_funding(seed.company_name),
            self._search_hiring(seed.company_name),
            self._search_pr_times(seed.company_name),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理新闻搜索结果
        if isinstance(results[0], Exception):
            self.add_error(f"新闻搜索错误: {results[0]}")
        else:
            result.news_search_results = results[0]

        # 处理融资搜索结果
        if isinstance(results[1], Exception):
            self.add_error(f"融资搜索错误: {results[1]}")
        else:
            result.funding_search_results = results[1]

        # 处理招聘搜索结果
        if isinstance(results[2], Exception):
            self.add_error(f"招聘搜索错误: {results[2]}")
        else:
            result.hiring_search_results = results[2]

        # 处理 PR TIMES 搜索结果
        if isinstance(results[3], Exception):
            self.add_error(f"PR TIMES 搜索错误: {results[3]}")
        else:
            result.pr_times_results = results[3]

        # 新闻全文爬取
        if config.news_enrichment.enabled:
            all_search_results = (
                result.news_search_results
                + result.funding_search_results
                + result.pr_times_results
            )
            company_domain = urlparse(seed.website_url).netloc if seed.website_url else ""
            news_urls = self._filter_news_urls(all_search_results, company_domain)

            if news_urls:
                logger.info(f"筛选出 {len(news_urls)} 个新闻 URL，开始全文爬取")
                result.news_full_content = await self._crawl_news_articles(news_urls)
                logger.info(f"成功爬取 {len(result.news_full_content)} 篇新闻全文")
            else:
                logger.info("无可爬取的新闻 URL")

        result.errors = self.errors.copy()
        return result

    def _is_news_url(self, url: str, company_domain: str = "") -> bool:
        """
        判断 URL 是否为新闻类链接

        Args:
            url: 待判断的 URL
            company_domain: 企业自身域名（排除用）

        Returns:
            是否为新闻 URL
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
        except Exception:
            return False

        # 排除黑名单域名
        for excluded in EXCLUDED_DOMAINS:
            if excluded in domain:
                return False

        # 排除企业自身官网
        if company_domain and company_domain in domain:
            return False

        # 白名单域名直接通过
        for news_domain in NEWS_DOMAINS:
            if news_domain in domain:
                return True

        # 其他域名：检查路径是否包含新闻特征
        path = parsed.path.lower()
        for pattern in NEWS_PATH_PATTERNS:
            if pattern in path:
                return True

        return False

    def _filter_news_urls(self, search_results: list[dict], company_domain: str = "") -> list[dict]:
        """
        从搜索结果中筛选需要爬取的新闻 URL

        Args:
            search_results: 搜索结果列表
            company_domain: 企业自身域名

        Returns:
            去重后的新闻条目列表 [{"url": str, "title": str}]
        """
        config = get_config()
        seen_urls = set()
        news_items = []

        for item in search_results:
            url = item.get("link", "")
            if not url or url in seen_urls:
                continue

            if self._is_news_url(url, company_domain):
                seen_urls.add(url)
                news_items.append({
                    "url": url,
                    "title": item.get("title", ""),
                })

            if len(news_items) >= config.news_enrichment.max_articles:
                break

        return news_items

    async def _crawl_news_articles(self, news_items: list[dict]) -> list[dict]:
        """
        并发爬取新闻文章全文

        Args:
            news_items: [{"url": str, "title": str}]

        Returns:
            [{"url": str, "title": str, "content": str, "crawled_at": str}]
        """
        config = get_config()
        enrichment_config = config.news_enrichment
        results = []
        semaphore = asyncio.Semaphore(enrichment_config.concurrency)

        async def crawl_one(item: dict) -> Optional[dict]:
            async with semaphore:
                url = item["url"]
                try:
                    browser_config = BrowserConfig(headless=True)
                    crawler_run_config = CrawlerRunConfig(
                        word_count_threshold=50,
                    )

                    async with AsyncWebCrawler(config=browser_config) as crawler:
                        result = await asyncio.wait_for(
                            crawler.arun(url=url, config=crawler_run_config),
                            timeout=enrichment_config.timeout,
                        )

                        if result.success and result.markdown:
                            content = result.markdown[:enrichment_config.max_content_length]
                            return {
                                "url": url,
                                "title": item.get("title", ""),
                                "content": content,
                                "crawled_at": datetime.now().isoformat(),
                            }
                        else:
                            logger.warning(f"爬取失败: {url} — {getattr(result, 'error_message', '未知错误')}")
                            return None

                except asyncio.TimeoutError:
                    logger.warning(f"爬取超时: {url}")
                    return None
                except Exception as e:
                    logger.warning(f"爬取异常: {url} — {e}")
                    return None
                finally:
                    await asyncio.sleep(enrichment_config.delay_between_requests)

        tasks = [crawl_one(item) for item in news_items]
        crawl_results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in crawl_results:
            if isinstance(r, dict):
                results.append(r)

        return results

    async def _search_news(self, company_name: str) -> list[dict]:
        """
        搜索企业新闻

        Args:
            company_name: 企业名称

        Returns:
            新闻搜索结果列表
        """
        current_year = datetime.now().year
        last_year = current_year - 1

        query = f"{company_name} ニュース OR プレスリリース {last_year} OR {current_year}"

        async with SerperClient() as client:
            # 使用新闻搜索
            response = await client.search_news(query, num_results=15)

            if response.error:
                self.add_error(f"新闻搜索失败: {response.error}")
                return []

            return [
                {
                    "title": r.title,
                    "link": r.link,
                    "snippet": r.snippet,
                    "position": r.position,
                    "query": query,
                }
                for r in response.results
            ]

    async def _search_funding(self, company_name: str) -> list[dict]:
        """
        搜索融资相关新闻

        Args:
            company_name: 企业名称

        Returns:
            融资搜索结果列表
        """
        queries = [
            f"{company_name} 資金調達",
            f"{company_name} 出資 OR 増資",
            f"{company_name} シリーズA OR シリーズB OR シード",
        ]

        all_results = []

        async with SerperClient() as client:
            for query in queries:
                response = await client.search(query, num_results=5)

                if response.error:
                    self.add_error(f"融资搜索失败 ({query}): {response.error}")
                    continue

                for r in response.results:
                    # 去重
                    if not any(item["link"] == r.link for item in all_results):
                        all_results.append({
                            "title": r.title,
                            "link": r.link,
                            "snippet": r.snippet,
                            "position": r.position,
                            "query": query,
                        })

                await asyncio.sleep(0.3)

        return all_results

    async def _search_hiring(self, company_name: str) -> list[dict]:
        """
        搜索招聘信息

        Args:
            company_name: 企业名称

        Returns:
            招聘搜索结果列表
        """
        queries = [
            f"{company_name} 採用 OR 求人 OR 募集",
            f"site:wantedly.com {company_name}",
            f"site:green-japan.com {company_name}",
        ]

        all_results = []

        async with SerperClient() as client:
            for query in queries:
                response = await client.search(query, num_results=5)

                if response.error:
                    continue

                for r in response.results:
                    # 去重
                    if not any(item["link"] == r.link for item in all_results):
                        all_results.append({
                            "title": r.title,
                            "link": r.link,
                            "snippet": r.snippet,
                            "position": r.position,
                            "query": query,
                            "source": self._identify_hiring_source(r.link),
                        })

                await asyncio.sleep(0.3)

        return all_results

    async def _search_pr_times(self, company_name: str) -> list[dict]:
        """
        搜索 PR TIMES 新闻稿

        Args:
            company_name: 企业名称

        Returns:
            PR TIMES 搜索结果列表
        """
        query = f"site:prtimes.jp {company_name}"

        async with SerperClient() as client:
            response = await client.search(query, num_results=10)

            if response.error:
                self.add_error(f"PR TIMES 搜索失败: {response.error}")
                return []

            return [
                {
                    "title": r.title,
                    "link": r.link,
                    "snippet": r.snippet,
                    "position": r.position,
                    "source": "PR TIMES",
                }
                for r in response.results
            ]

    def _identify_hiring_source(self, url: str) -> str:
        """识别招聘来源网站"""
        if "wantedly.com" in url:
            return "Wantedly"
        elif "green-japan.com" in url:
            return "Green"
        elif "doda.jp" in url:
            return "doda"
        elif "en-japan.com" in url:
            return "en-japan"
        elif "rikunabi.com" in url:
            return "リクナビ"
        elif "mynavi.jp" in url:
            return "マイナビ"
        else:
            return "other"

    def _get_empty_result(self) -> SignalsRaw:
        """返回空结果"""
        return SignalsRaw(errors=self.errors.copy())

    def _deserialize(self, data: dict) -> SignalsRaw:
        """从缓存反序列化"""
        return SignalsRaw(**data)


# ============================================================
# 便捷函数
# ============================================================

async def collect_signals(seed: SeedData, use_cache: bool = True) -> SignalsRaw:
    """
    收集商机信号的便捷函数

    Args:
        seed: 种子数据
        use_cache: 是否使用缓存

    Returns:
        SignalsRaw
    """
    collector = SignalCollector(use_cache=use_cache)
    return await collector.run(seed)


if __name__ == "__main__":
    # 测试
    async def test():
        print("=== SignalCollector 测试 ===\n")

        seed = SeedData(
            company_name="Sparticle株式会社",
            corporate_number="4120001222866",
            website_url="https://www.sparticle.com/ja",
        )

        result = await collect_signals(seed, use_cache=False)

        print(f"新闻搜索结果: {len(result.news_search_results)} 条")
        print(f"融资搜索结果: {len(result.funding_search_results)} 条")
        print(f"招聘搜索结果: {len(result.hiring_search_results)} 条")
        print(f"PR TIMES结果: {len(result.pr_times_results)} 条")
        print(f"错误: {result.errors}")

        if result.news_search_results:
            print(f"\n--- 新闻搜索结果 (前3条) ---")
            for item in result.news_search_results[:3]:
                print(f"  - {item['title']}")
                print(f"    {item['link']}")

        if result.funding_search_results:
            print(f"\n--- 融资搜索结果 (前3条) ---")
            for item in result.funding_search_results[:3]:
                print(f"  - {item['title']}")
                print(f"    {item['snippet'][:80]}...")

    asyncio.run(test())
