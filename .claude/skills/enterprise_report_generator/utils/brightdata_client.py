"""
Bright Data API 客户端 (LinkedIn 数据采集)

支持的数据类型:
- 公司资料 + 员工概览
- 个人详细资料
- 人员搜索
"""
import httpx
import logging
from typing import Optional, Any
from dataclasses import dataclass

from ..config import get_config

logger = logging.getLogger(__name__)


@dataclass
class LinkedInEmployee:
    """LinkedIn 员工概览数据"""
    name: str
    title: str
    linkedin_url: Optional[str] = None
    profile_image: Optional[str] = None


@dataclass
class LinkedInCompanyProfile:
    """LinkedIn 公司资料"""
    name: str
    linkedin_url: str
    description: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    headquarters: Optional[str] = None
    founded: Optional[str] = None
    website: Optional[str] = None
    employees: list[LinkedInEmployee] = None

    def __post_init__(self):
        if self.employees is None:
            self.employees = []


@dataclass
class LinkedInPersonProfile:
    """LinkedIn 个人详细资料"""
    name: str
    linkedin_url: str
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    experience: list[dict] = None
    education: list[dict] = None
    skills: list[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    def __post_init__(self):
        if self.experience is None:
            self.experience = []
        if self.education is None:
            self.education = []
        if self.skills is None:
            self.skills = []


class BrightDataClient:
    """Bright Data API 客户端

    通过 Bright Data 的 Web Scraper API 获取 LinkedIn 数据。
    """

    # Bright Data Web Scraper API 端点
    BASE_URL = "https://api.brightdata.com/datasets/v3/trigger"

    # 数据集 ID (LinkedIn 专用)
    # 参考: https://docs.brightdata.com/api-reference/web-scraper-api/social-media-apis/linkedin
    DATASET_COMPANY_PROFILE = "gd_l1vikfnt1wgvvqz95w"  # LinkedIn Company Profile
    DATASET_PERSON_PROFILE = "gd_l1viktl72bvl7bjuj0"   # LinkedIn Person Profile
    DATASET_PEOPLE_SEARCH = "gd_l1viktl72bvl7bjv1u"    # LinkedIn People Search

    def __init__(self, config=None):
        self.config = config or get_config()
        self.api_key = self.config.brightdata.api_key
        self.user_id = self.config.brightdata.user_id
        self.timeout = self.config.brightdata.timeout
        self.max_retries = self.config.brightdata.max_retries

    def _get_headers(self) -> dict:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _make_request(
        self,
        dataset_id: str,
        inputs: list[dict],
        format: str = "json",
        max_wait_seconds: int = 120
    ) -> Optional[dict]:
        """发送数据采集请求 (异步模式)

        Bright Data API 工作流程:
        1. 触发采集 → 获得 snapshot_id
        2. 轮询状态直到 ready
        3. 下载结果

        Args:
            dataset_id: 数据集 ID
            inputs: 输入参数列表
            format: 输出格式
            max_wait_seconds: 最大等待时间

        Returns:
            API 响应数据
        """
        import asyncio

        if not self.api_key:
            logger.error("Bright Data API key not configured")
            return None

        # Step 1: 触发采集
        trigger_url = f"{self.BASE_URL}?dataset_id={dataset_id}&format={format}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    trigger_url,
                    headers=self._get_headers(),
                    json=inputs
                )

                if response.status_code == 401:
                    logger.error("Bright Data authentication failed")
                    return None
                elif response.status_code != 200:
                    logger.error(f"Bright Data trigger error: {response.status_code} - {response.text}")
                    return None

                trigger_result = response.json()
                snapshot_id = trigger_result.get("snapshot_id")

                if not snapshot_id:
                    logger.error(f"No snapshot_id in response: {trigger_result}")
                    return None

                logger.info(f"Triggered collection, snapshot_id: {snapshot_id}")

                # Step 2: 轮询状态
                progress_url = f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}"
                poll_interval = 3  # 秒
                waited = 0

                while waited < max_wait_seconds:
                    await asyncio.sleep(poll_interval)
                    waited += poll_interval

                    status_response = await client.get(
                        progress_url,
                        headers=self._get_headers()
                    )

                    if status_response.status_code != 200:
                        logger.warning(f"Progress check failed: {status_response.status_code}")
                        continue

                    status_data = status_response.json()
                    status = status_data.get("status")
                    logger.debug(f"Snapshot {snapshot_id} status: {status}")

                    if status == "ready":
                        # Step 3: 下载结果
                        download_url = f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}?format={format}"
                        download_response = await client.get(
                            download_url,
                            headers=self._get_headers()
                        )

                        if download_response.status_code == 200:
                            return download_response.json()
                        else:
                            logger.error(f"Download failed: {download_response.status_code} - {download_response.text}")
                            return None

                    elif status == "failed":
                        logger.error(f"Snapshot collection failed: {status_data}")
                        return None

                logger.error(f"Timeout waiting for snapshot {snapshot_id} (waited {waited}s)")
                return None

        except httpx.TimeoutException:
            logger.error("Request timeout")
            return None
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None

    async def get_company_profile(self, linkedin_url: str) -> Optional[LinkedInCompanyProfile]:
        """获取公司资料及员工概览

        Args:
            linkedin_url: 公司 LinkedIn URL

        Returns:
            LinkedInCompanyProfile 或 None
        """
        logger.info(f"Fetching LinkedIn company profile: {linkedin_url}")

        inputs = [{"url": linkedin_url}]
        result = await self._make_request(self.DATASET_COMPANY_PROFILE, inputs)

        if not result or not isinstance(result, list) or len(result) == 0:
            return None

        data = result[0] if isinstance(result, list) else result

        # 解析员工列表
        # Bright Data 返回字段: title=名字, subtitle=职位, link=URL, img=头像
        employees = []
        raw_employees = data.get("employees", []) or []
        for emp in raw_employees[:self.config.brightdata.max_employees_per_request]:
            employees.append(LinkedInEmployee(
                name=emp.get("title", ""),  # Bright Data 用 title 字段存储名字
                title=emp.get("subtitle", ""),  # subtitle 才是职位
                linkedin_url=emp.get("link"),  # link 字段是 LinkedIn URL
                profile_image=emp.get("img")  # img 字段是头像
            ))

        return LinkedInCompanyProfile(
            name=data.get("name", ""),
            linkedin_url=linkedin_url,
            description=data.get("description"),
            industry=data.get("industry"),
            company_size=data.get("company_size") or data.get("size"),
            headquarters=data.get("headquarters"),
            founded=data.get("founded"),
            website=data.get("website"),
            employees=employees
        )

    async def get_person_profile(self, linkedin_url: str) -> Optional[LinkedInPersonProfile]:
        """获取个人详细资料

        Args:
            linkedin_url: 个人 LinkedIn URL

        Returns:
            LinkedInPersonProfile 或 None
        """
        logger.info(f"Fetching LinkedIn person profile: {linkedin_url}")

        inputs = [{"url": linkedin_url}]
        result = await self._make_request(self.DATASET_PERSON_PROFILE, inputs)

        if not result or not isinstance(result, list) or len(result) == 0:
            return None

        data = result[0] if isinstance(result, list) else result

        return LinkedInPersonProfile(
            name=data.get("name", ""),
            linkedin_url=linkedin_url,
            title=data.get("title") or data.get("headline"),
            company=data.get("company") or data.get("current_company"),
            location=data.get("location"),
            summary=data.get("summary") or data.get("about"),
            experience=data.get("experience", []),
            education=data.get("education", []),
            skills=data.get("skills", []),
            email=data.get("email"),
            phone=data.get("phone")
        )

    async def search_people(
        self,
        company_name: str,
        keywords: Optional[str] = None,
        title_filter: Optional[str] = None,
        limit: int = 20
    ) -> list[LinkedInEmployee]:
        """搜索公司员工

        Args:
            company_name: 公司名称
            keywords: 搜索关键词
            title_filter: 职位过滤
            limit: 返回数量限制

        Returns:
            员工列表
        """
        logger.info(f"Searching LinkedIn people at {company_name}")

        # 构建搜索查询
        query_parts = [company_name]
        if keywords:
            query_parts.append(keywords)
        if title_filter:
            query_parts.append(f"title:{title_filter}")

        inputs = [{
            "keyword": " ".join(query_parts),
            "limit": limit
        }]

        result = await self._make_request(self.DATASET_PEOPLE_SEARCH, inputs)

        if not result:
            return []

        employees = []
        results = result if isinstance(result, list) else [result]

        for data in results[:limit]:
            if isinstance(data, dict):
                employees.append(LinkedInEmployee(
                    name=data.get("name", ""),
                    title=data.get("title", ""),
                    linkedin_url=data.get("linkedin_url") or data.get("profile_url"),
                    profile_image=data.get("profile_image")
                ))

        return employees


# 便捷函数
async def get_company_linkedin_data(linkedin_url: str) -> Optional[LinkedInCompanyProfile]:
    """获取公司 LinkedIn 数据的便捷函数"""
    client = BrightDataClient()
    return await client.get_company_profile(linkedin_url)


async def get_person_linkedin_data(linkedin_url: str) -> Optional[LinkedInPersonProfile]:
    """获取个人 LinkedIn 数据的便捷函数"""
    client = BrightDataClient()
    return await client.get_person_profile(linkedin_url)
