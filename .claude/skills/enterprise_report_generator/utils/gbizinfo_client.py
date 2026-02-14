"""
gBizINFO API 客户端

日本经济产业省法人信息 API
API文档: https://info.gbiz.go.jp/hojin/swagger-ui.html
"""
import asyncio
import logging
from typing import Optional
from dataclasses import dataclass, field

import httpx

from ..config import get_config, GBizInfoConfig

logger = logging.getLogger(__name__)


@dataclass
class GBizInfoData:
    """gBizINFO 返回的企业数据"""
    # 基本信息
    corporate_number: str = ""
    name: str = ""
    name_kana: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None

    # 代表人
    representative_name: Optional[str] = None
    representative_position: Optional[str] = None

    # 其他信息
    capital_stock: Optional[int] = None
    employee_number: Optional[int] = None
    founding_year: Optional[int] = None
    close_cause: Optional[str] = None
    close_date: Optional[str] = None
    update_date: Optional[str] = None

    # 业务信息
    business_summary: Optional[str] = None
    company_url: Optional[str] = None

    # 财务信息 (如果有)
    date_of_establishment: Optional[str] = None

    # 原始数据
    raw_data: dict = field(default_factory=dict)

    # 错误信息
    error: Optional[str] = None


class GBizInfoClient:
    """gBizINFO API 客户端"""

    def __init__(self, config: Optional[GBizInfoConfig] = None):
        self.config = config or get_config().gbizinfo
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=self.config.timeout,
            headers={
                "X-hojinInfo-api-token": self.config.api_token,
                "Accept": "application/json",
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Client not initialized. Use 'async with GBizInfoClient()' context manager.")
        return self._client

    async def get_by_corporate_number(self, corporate_number: str) -> GBizInfoData:
        """
        根据法人番号获取企业信息

        Args:
            corporate_number: 13位法人番号

        Returns:
            GBizInfoData
        """
        # 验证法人番号格式
        if not corporate_number or len(corporate_number) != 13 or not corporate_number.isdigit():
            return GBizInfoData(
                corporate_number=corporate_number,
                error=f"无效的法人番号格式: {corporate_number}"
            )

        url = f"{self.config.base_url}/hojin/{corporate_number}"

        for attempt in range(self.config.max_retries):
            try:
                response = await self.client.get(url)
                response.raise_for_status()
                data = response.json()

                # 解析返回数据
                hojin_infos = data.get("hojin-infos", [])
                if not hojin_infos:
                    return GBizInfoData(
                        corporate_number=corporate_number,
                        error="未找到企业信息"
                    )

                info = hojin_infos[0]

                return GBizInfoData(
                    corporate_number=info.get("corporate_number", corporate_number),
                    name=info.get("name", ""),
                    name_kana=info.get("kana", None),
                    location=info.get("location", None),
                    status=info.get("status", None),
                    representative_name=info.get("representative_name", None),
                    representative_position=info.get("representative_position", None),
                    capital_stock=self._parse_int(info.get("capital_stock")),
                    employee_number=self._parse_int(info.get("employee_number")),
                    founding_year=self._parse_int(info.get("founding_year")),
                    close_cause=info.get("close_cause", None),
                    close_date=info.get("close_date", None),
                    update_date=info.get("update_date", None),
                    business_summary=info.get("business_summary", None),
                    company_url=info.get("company_url", None),
                    date_of_establishment=info.get("date_of_establishment", None),
                    raw_data=info,
                )

            except httpx.HTTPStatusError as e:
                logger.warning(f"gBizINFO API HTTP error (attempt {attempt + 1}): {e}")
                if e.response.status_code == 404:
                    return GBizInfoData(
                        corporate_number=corporate_number,
                        error="未找到企业信息 (404)"
                    )
                if attempt == self.config.max_retries - 1:
                    return GBizInfoData(
                        corporate_number=corporate_number,
                        error=f"HTTP error: {e.response.status_code}"
                    )
                await asyncio.sleep(2 ** attempt)

            except Exception as e:
                logger.error(f"gBizINFO API error (attempt {attempt + 1}): {e}")
                if attempt == self.config.max_retries - 1:
                    return GBizInfoData(
                        corporate_number=corporate_number,
                        error=str(e)
                    )
                await asyncio.sleep(2 ** attempt)

        return GBizInfoData(
            corporate_number=corporate_number,
            error="Max retries exceeded"
        )

    async def search_by_name(
        self,
        name: str,
        limit: int = 10
    ) -> list[GBizInfoData]:
        """
        根据企业名称搜索

        Args:
            name: 企业名称
            limit: 返回结果数量

        Returns:
            GBizInfoData 列表
        """
        url = f"{self.config.base_url}/hojin"
        params = {
            "name": name,
            "limit": limit,
        }

        for attempt in range(self.config.max_retries):
            try:
                response = await self.client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                results = []
                for info in data.get("hojin-infos", []):
                    results.append(GBizInfoData(
                        corporate_number=info.get("corporate_number", ""),
                        name=info.get("name", ""),
                        name_kana=info.get("kana", None),
                        location=info.get("location", None),
                        status=info.get("status", None),
                        raw_data=info,
                    ))

                return results

            except httpx.HTTPStatusError as e:
                logger.warning(f"gBizINFO search API HTTP error (attempt {attempt + 1}): {e}")
                if attempt == self.config.max_retries - 1:
                    return [GBizInfoData(error=f"HTTP error: {e.response.status_code}")]
                await asyncio.sleep(2 ** attempt)

            except Exception as e:
                logger.error(f"gBizINFO search API error (attempt {attempt + 1}): {e}")
                if attempt == self.config.max_retries - 1:
                    return [GBizInfoData(error=str(e))]
                await asyncio.sleep(2 ** attempt)

        return [GBizInfoData(error="Max retries exceeded")]

    @staticmethod
    def _parse_int(value) -> Optional[int]:
        """安全解析整数"""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None


# ============================================================
# 便捷函数
# ============================================================

async def get_company_info(corporate_number: str) -> GBizInfoData:
    """
    获取企业信息的便捷函数

    Args:
        corporate_number: 13位法人番号

    Returns:
        GBizInfoData
    """
    async with GBizInfoClient() as client:
        return await client.get_by_corporate_number(corporate_number)


async def search_company(name: str, limit: int = 10) -> list[GBizInfoData]:
    """
    搜索企业的便捷函数

    Args:
        name: 企业名称
        limit: 返回结果数量

    Returns:
        GBizInfoData 列表
    """
    async with GBizInfoClient() as client:
        return await client.search_by_name(name, limit)


def format_capital(capital: Optional[int]) -> Optional[str]:
    """
    格式化资本金显示

    Args:
        capital: 资本金(日元)

    Returns:
        格式化后的字符串 (如: "9,000万円")
    """
    if capital is None:
        return None

    if capital >= 100_000_000:
        oku = capital // 100_000_000
        man = (capital % 100_000_000) // 10_000
        if man > 0:
            return f"{oku}億{man:,}万円"
        return f"{oku}億円"
    elif capital >= 10_000:
        man = capital // 10_000
        return f"{man:,}万円"
    else:
        return f"{capital:,}円"


if __name__ == "__main__":
    # 测试
    async def test():
        print("=== gBizINFO API 测试 ===\n")

        # 测试法人番号查询 (Sparticle株式会社)
        corporate_number = "4120001222866"
        print(f"查询法人番号: {corporate_number}")

        result = await get_company_info(corporate_number)

        if result.error:
            print(f"错误: {result.error}")
        else:
            print(f"企业名: {result.name}")
            print(f"所在地: {result.location}")
            print(f"代表人: {result.representative_name}")
            print(f"资本金: {format_capital(result.capital_stock)}")
            print(f"员工数: {result.employee_number}")
            print(f"成立年: {result.founding_year}")
            print(f"官网: {result.company_url}")

    asyncio.run(test())
