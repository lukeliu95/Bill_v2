"""
Serper API 客户端

用于 Google 搜索，获取企业相关信息
"""
import asyncio
import logging
from typing import Optional
from dataclasses import dataclass

import httpx

from ..config import get_config, SerperConfig

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """搜索结果项"""
    title: str
    link: str
    snippet: str
    position: int


@dataclass
class SerperResponse:
    """Serper API 响应"""
    query: str
    results: list[SearchResult]
    total_results: Optional[int] = None
    search_time: Optional[float] = None
    error: Optional[str] = None


class SerperClient:
    """Serper API 客户端"""

    def __init__(self, config: Optional[SerperConfig] = None):
        self.config = config or get_config().serper
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=self.config.timeout,
            headers={
                "X-API-KEY": self.config.api_key,
                "Content-Type": "application/json",
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Client not initialized. Use 'async with SerperClient()' context manager.")
        return self._client

    async def search(
        self,
        query: str,
        num_results: int = 10,
        country: str = "jp",
        language: str = "ja",
    ) -> SerperResponse:
        """
        执行 Google 搜索

        Args:
            query: 搜索查询
            num_results: 返回结果数量
            country: 国家代码
            language: 语言代码

        Returns:
            SerperResponse
        """
        url = f"{self.config.base_url}/search"

        payload = {
            "q": query,
            "num": num_results,
            "gl": country,
            "hl": language,
        }

        for attempt in range(self.config.max_retries):
            try:
                response = await self.client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

                results = []
                for i, item in enumerate(data.get("organic", [])):
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        link=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        position=i + 1,
                    ))

                return SerperResponse(
                    query=query,
                    results=results,
                    total_results=data.get("searchInformation", {}).get("totalResults"),
                    search_time=data.get("searchInformation", {}).get("searchTime"),
                )

            except httpx.HTTPStatusError as e:
                logger.warning(f"Serper API HTTP error (attempt {attempt + 1}): {e}")
                if attempt == self.config.max_retries - 1:
                    return SerperResponse(
                        query=query,
                        results=[],
                        error=f"HTTP error: {e.response.status_code}",
                    )
                await asyncio.sleep(2 ** attempt)  # 指数退避

            except Exception as e:
                logger.error(f"Serper API error (attempt {attempt + 1}): {e}")
                if attempt == self.config.max_retries - 1:
                    return SerperResponse(
                        query=query,
                        results=[],
                        error=str(e),
                    )
                await asyncio.sleep(2 ** attempt)

        return SerperResponse(query=query, results=[], error="Max retries exceeded")

    async def search_news(
        self,
        query: str,
        num_results: int = 10,
        country: str = "jp",
        language: str = "ja",
    ) -> SerperResponse:
        """
        搜索新闻

        Args:
            query: 搜索查询
            num_results: 返回结果数量
            country: 国家代码
            language: 语言代码

        Returns:
            SerperResponse
        """
        url = f"{self.config.base_url}/news"

        payload = {
            "q": query,
            "num": num_results,
            "gl": country,
            "hl": language,
        }

        for attempt in range(self.config.max_retries):
            try:
                response = await self.client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

                results = []
                for i, item in enumerate(data.get("news", [])):
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        link=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        position=i + 1,
                    ))

                return SerperResponse(
                    query=query,
                    results=results,
                )

            except httpx.HTTPStatusError as e:
                logger.warning(f"Serper News API HTTP error (attempt {attempt + 1}): {e}")
                if attempt == self.config.max_retries - 1:
                    return SerperResponse(
                        query=query,
                        results=[],
                        error=f"HTTP error: {e.response.status_code}",
                    )
                await asyncio.sleep(2 ** attempt)

            except Exception as e:
                logger.error(f"Serper News API error (attempt {attempt + 1}): {e}")
                if attempt == self.config.max_retries - 1:
                    return SerperResponse(
                        query=query,
                        results=[],
                        error=str(e),
                    )
                await asyncio.sleep(2 ** attempt)

        return SerperResponse(query=query, results=[], error="Max retries exceeded")


# ============================================================
# 便捷函数
# ============================================================

async def search_company_info(company_name: str, query_type: str) -> SerperResponse:
    """
    搜索企业信息的便捷函数

    Args:
        company_name: 企业名称
        query_type: 查询类型 (executives/organization/funding/news/hiring)

    Returns:
        SerperResponse
    """
    query_templates = {
        "executives": f"{company_name} 役員 OR 経営陣 OR 代表取締役",
        "organization": f"{company_name} 組織図 OR 部署 OR 体制",
        "funding": f"{company_name} 資金調達 OR 融資 OR 出資",
        "news": f"{company_name} 2024 OR 2025 ニュース",
        "hiring": f"{company_name} 採用 OR 求人 OR 募集",
        "partnership": f"{company_name} 提携 OR 協業 OR パートナーシップ",
    }

    query = query_templates.get(query_type, f"{company_name} {query_type}")

    async with SerperClient() as client:
        if query_type == "news":
            return await client.search_news(query)
        else:
            return await client.search(query)


async def batch_search(queries: list[str], delay: float = 0.5) -> list[SerperResponse]:
    """
    批量搜索

    Args:
        queries: 查询列表
        delay: 请求间隔(秒)

    Returns:
        搜索结果列表
    """
    results = []
    async with SerperClient() as client:
        for query in queries:
            result = await client.search(query)
            results.append(result)
            await asyncio.sleep(delay)
    return results


if __name__ == "__main__":
    # 测试
    async def test():
        print("=== Serper API 测试 ===\n")

        # 测试搜索
        result = await search_company_info("Sparticle株式会社", "executives")
        print(f"查询: {result.query}")
        print(f"结果数: {len(result.results)}")
        if result.error:
            print(f"错误: {result.error}")
        else:
            for r in result.results[:3]:
                print(f"  - {r.title}")
                print(f"    {r.link}")
                print()

    asyncio.run(test())
