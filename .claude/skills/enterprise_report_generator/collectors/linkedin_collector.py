"""
LinkedIn 联系人收集器

两阶段采集流程:
1. 获取公司概览 + 员工列表
2. Gemini 筛选关键人物 → 定向获取详细资料
"""
import asyncio
import logging
from typing import Optional
from dataclasses import dataclass, field

from .base_collector import BaseCollector
from ..models import SeedData
from ..utils.brightdata_client import (
    BrightDataClient,
    LinkedInCompanyProfile,
    LinkedInPersonProfile,
    LinkedInEmployee,
)
from ..config import get_config
from ..prompts.linkedin_filter_prompt import get_linkedin_filter_prompt

logger = logging.getLogger(__name__)


@dataclass
class KeyPersonCandidate:
    """关键人物候选"""
    name: str
    title: str
    linkedin_url: Optional[str] = None
    priority: int = 0  # 优先级 1-5, 5 最高
    reason: Optional[str] = None  # 被选中的原因


@dataclass
class LinkedInData:
    """LinkedIn 采集结果"""
    company_profile: Optional[LinkedInCompanyProfile] = None
    key_persons: list[LinkedInPersonProfile] = field(default_factory=list)
    all_employees: list[LinkedInEmployee] = field(default_factory=list)
    company_linkedin_url: Optional[str] = None
    collection_status: str = "pending"  # pending, partial, complete, failed
    error_message: Optional[str] = None


class LinkedInCollector(BaseCollector):
    """LinkedIn 联系人收集器

    实现两阶段采集:
    Phase 1: 获取公司 LinkedIn 资料 + 员工概览
    Phase 2: Gemini 分析筛选 → 获取关键人物详细资料
    """

    name = "LinkedInCollector"
    cache_category = "linkedin"

    def __init__(self, config=None, use_cache: bool = True):
        super().__init__(use_cache=use_cache)
        self.config = config or get_config()
        self.brightdata_client = BrightDataClient(self.config)
        self.max_key_persons = self.config.brightdata.max_key_persons

    async def collect(self, seed: SeedData) -> LinkedInData:
        """执行 LinkedIn 数据采集

        Args:
            seed: 种子数据

        Returns:
            LinkedInData 采集结果
        """
        result = LinkedInData()

        # 检查配置
        if not self.config.has_linkedin_config():
            logger.warning("LinkedIn collection skipped: Bright Data not configured")
            result.collection_status = "skipped"
            result.error_message = "Bright Data API not configured"
            return result

        try:
            # Phase 1: 获取公司 LinkedIn URL 和概览
            company_url = await self._find_company_linkedin_url(seed)
            if not company_url:
                logger.warning(f"Could not find LinkedIn URL for {seed.company_name}")
                result.collection_status = "failed"
                result.error_message = "Company LinkedIn URL not found"
                return result

            result.company_linkedin_url = company_url

            # 尝试从缓存获取
            cache_key = company_url.replace("https://", "").replace("/", "_")
            if self.cache:
                cached_data = self.cache.get(self.cache_category, cache_key)
                if cached_data:
                    logger.info(f"Using cached LinkedIn data for {seed.company_name}")
                    return self._deserialize_linkedin_data(cached_data)

            # 获取公司概览
            company_profile = await self.brightdata_client.get_company_profile(company_url)
            if not company_profile:
                result.collection_status = "failed"
                result.error_message = "Failed to fetch company profile"
                return result

            result.company_profile = company_profile
            result.all_employees = company_profile.employees
            result.collection_status = "partial"

            # Phase 2: 筛选关键人物并获取详细资料
            if company_profile.employees:
                key_persons = await self._collect_key_persons(
                    seed.company_name,
                    company_profile.employees
                )
                result.key_persons = key_persons

            result.collection_status = "complete"

            # 缓存结果
            if self.cache:
                self.cache.set(self.cache_category, cache_key, self._serialize_linkedin_data(result))

            return result

        except Exception as e:
            logger.error(f"LinkedIn collection error: {e}")
            result.collection_status = "failed"
            result.error_message = str(e)
            return result

    async def _find_company_linkedin_url(self, seed: SeedData) -> Optional[str]:
        """查找公司的 LinkedIn URL

        策略:
        1. 检查 seed 数据中是否已有
        2. 从官网查找 LinkedIn 链接
        3. 通过搜索引擎查找
        """
        # 如果官网有，尝试从官网抓取 LinkedIn 链接
        if seed.website_url:
            # 这里可以调用 Crawler 从官网找 LinkedIn 链接
            # 简化实现：直接构造搜索
            pass

        # 通过搜索引擎查找
        from ..utils.serper_client import SerperClient

        async with SerperClient(self.config.serper) as serper:
            search_query = f"{seed.company_name} LinkedIn company"
            results = await serper.search(search_query, num_results=5)

            if results and results.results:
                for item in results.results:
                    link = item.link.lower()
                    # 匹配 LinkedIn 公司页面 URL 模式
                    if "linkedin.com/company/" in link:
                        return item.link

            # 尝试日语搜索
            search_query_jp = f"{seed.company_name} LinkedIn 会社"
            results_jp = await serper.search(search_query_jp, num_results=5)

            if results_jp and results_jp.results:
                for item in results_jp.results:
                    link = item.link.lower()
                    if "linkedin.com/company/" in link:
                        return item.link

        return None

    async def _collect_key_persons(
        self,
        company_name: str,
        employees: list[LinkedInEmployee]
    ) -> list[LinkedInPersonProfile]:
        """Phase 2: 筛选关键人物并获取详细资料

        Args:
            company_name: 公司名称
            employees: 员工列表

        Returns:
            关键人物详细资料列表
        """
        if not employees:
            logger.warning(f"[KeyPersons] No employees to filter for {company_name}")
            return []

        # 调试: 记录员工列表
        logger.info(f"[KeyPersons] Processing {len(employees)} employees for {company_name}")
        for i, emp in enumerate(employees[:5]):  # 只记录前5个
            logger.debug(f"[KeyPersons] Employee {i+1}: {emp.name} - {emp.title or 'NO TITLE'}")

        # Step 1: 使用 Gemini 筛选关键人物
        candidates = await self._filter_key_persons(company_name, employees)

        logger.info(f"[KeyPersons] Filter returned {len(candidates)} candidates")

        if not candidates:
            logger.warning(f"[KeyPersons] No key persons identified for {company_name}, trying fallback")
            # 尝试兜底: 返回前几名员工
            candidates = self._fallback_include_all(employees)
            logger.info(f"[KeyPersons] Fallback returned {len(candidates)} candidates")

        # Step 2: 并行获取关键人物详细资料
        key_persons = []
        tasks = []

        for candidate in candidates[:self.max_key_persons]:
            if candidate.linkedin_url:
                tasks.append(self._get_person_with_retry(candidate.linkedin_url))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, LinkedInPersonProfile):
                    key_persons.append(result)
                elif isinstance(result, Exception):
                    logger.warning(f"Failed to fetch person profile: {result}")

        logger.info(f"Collected {len(key_persons)} key person profiles for {company_name}")
        return key_persons

    async def _filter_key_persons(
        self,
        company_name: str,
        employees: list[LinkedInEmployee]
    ) -> list[KeyPersonCandidate]:
        """使用 Gemini 筛选关键人物

        Args:
            company_name: 公司名称
            employees: 员工列表

        Returns:
            关键人物候选列表 (按优先级排序)
        """
        # 构建员工列表文本
        employee_list = []
        for i, emp in enumerate(employees):
            employee_list.append(f"{i+1}. {emp.name} - {emp.title}")

        employee_text = "\n".join(employee_list)

        # 调用 Gemini 分析
        prompt = get_linkedin_filter_prompt(company_name, employee_text)

        try:
            from ..utils.gemini_client import GeminiClient

            async with GeminiClient(self.config.gemini) as gemini:
                result = await gemini.generate_json(prompt)

                if not result or "key_persons" not in result:
                    return []

                candidates = []
                for person in result["key_persons"]:
                    # 在原始员工列表中找到对应的 URL
                    idx = person.get("index", 0) - 1
                    linkedin_url = None
                    if 0 <= idx < len(employees):
                        linkedin_url = employees[idx].linkedin_url

                    candidates.append(KeyPersonCandidate(
                        name=person.get("name", ""),
                        title=person.get("title", ""),
                        linkedin_url=linkedin_url,
                        priority=person.get("priority", 3),
                        reason=person.get("reason")
                    ))

                # 按优先级排序
                candidates.sort(key=lambda x: x.priority, reverse=True)
                return candidates

        except Exception as e:
            logger.error(f"Gemini filter error: {e}")
            # 降级: 通过职位关键词简单筛选
            return self._fallback_filter(employees)

    def _fallback_filter(self, employees: list[LinkedInEmployee]) -> list[KeyPersonCandidate]:
        """降级筛选: 通过职位关键词 (增强版)"""
        # 扩展关键词列表，支持更多变体
        priority_titles = {
            5: [
                "ceo", "代表取締役", "社長", "president", "founder", "創業者",
                "chief executive", "代表", "オーナー", "owner", "共同創業",
                "co-founder", "cofounder", "創設者"
            ],
            4: [
                "cto", "cfo", "coo", "cmo", "cio", "cpo", "cro", "cso",
                "vp", "vice president", "取締役", "執行役員", "常務", "専務",
                "chief technology", "chief financial", "chief operating",
                "chief marketing", "chief product", "役員", "board"
            ],
            3: [
                "director", "部長", "head of", "general manager", "gm",
                "本部長", "事業部長", "統括", "ディレクター", "シニアディレクター",
                "senior director", "associate director", "担当部長"
            ],
            2: [
                "manager", "課長", "lead", "senior", "principal", "staff",
                "マネージャー", "マネジャー", "リード", "シニア", "主任",
                "team lead", "tech lead", "engineering manager", "プロジェクト"
            ],
            1: [
                "engineer", "エンジニア", "developer", "デベロッパー",
                "specialist", "スペシャリスト", "consultant", "コンサルタント",
                "analyst", "アナリスト", "coordinator"
            ],
        }

        candidates = []
        for emp in employees:
            title_lower = (emp.title or "").lower()
            name_lower = (emp.name or "").lower()

            # 调试日志
            logger.debug(f"[FallbackFilter] Checking: {emp.name} - {emp.title}")

            matched = False
            for priority, keywords in priority_titles.items():
                if any(kw in title_lower for kw in keywords):
                    candidates.append(KeyPersonCandidate(
                        name=emp.name,
                        title=emp.title,
                        linkedin_url=emp.linkedin_url,
                        priority=priority,
                        reason=f"Title keyword match (priority {priority})"
                    ))
                    matched = True
                    logger.debug(f"[FallbackFilter] Matched: {emp.name} with priority {priority}")
                    break

            if not matched:
                logger.debug(f"[FallbackFilter] No match for: {emp.name} - {emp.title}")

        candidates.sort(key=lambda x: x.priority, reverse=True)
        result = candidates[:self.max_key_persons]
        logger.info(f"[FallbackFilter] Returning {len(result)} candidates from {len(candidates)} matches")
        return result

    def _fallback_include_all(self, employees: list[LinkedInEmployee]) -> list[KeyPersonCandidate]:
        """最终兜底: 当没有任何匹配时，返回所有有 LinkedIn URL 的员工"""
        candidates = []
        for emp in employees:
            if emp.linkedin_url:
                candidates.append(KeyPersonCandidate(
                    name=emp.name,
                    title=emp.title or "Unknown",
                    linkedin_url=emp.linkedin_url,
                    priority=1,
                    reason="Included as fallback (no title match)"
                ))

        result = candidates[:self.max_key_persons]
        logger.info(f"[FallbackIncludeAll] Returning {len(result)} employees with LinkedIn URLs")
        return result

    async def _get_person_with_retry(self, linkedin_url: str) -> Optional[LinkedInPersonProfile]:
        """获取个人资料 (带重试)"""
        for attempt in range(self.config.brightdata.max_retries):
            try:
                profile = await self.brightdata_client.get_person_profile(linkedin_url)
                if profile:
                    return profile
            except Exception as e:
                logger.warning(f"Person profile fetch attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(1)

        return None

    def _serialize_linkedin_data(self, data: LinkedInData) -> dict:
        """序列化 LinkedIn 数据用于缓存"""
        return {
            "company_profile": self._serialize_company_profile(data.company_profile),
            "key_persons": [self._serialize_person_profile(p) for p in data.key_persons],
            "all_employees": [self._serialize_employee(e) for e in data.all_employees],
            "company_linkedin_url": data.company_linkedin_url,
            "collection_status": data.collection_status,
        }

    def _deserialize_linkedin_data(self, data: dict) -> LinkedInData:
        """反序列化缓存的 LinkedIn 数据"""
        return LinkedInData(
            company_profile=self._deserialize_company_profile(data.get("company_profile")),
            key_persons=[self._deserialize_person_profile(p) for p in data.get("key_persons", [])],
            all_employees=[self._deserialize_employee(e) for e in data.get("all_employees", [])],
            company_linkedin_url=data.get("company_linkedin_url"),
            collection_status=data.get("collection_status", "complete"),
        )

    @staticmethod
    def _serialize_company_profile(profile: Optional[LinkedInCompanyProfile]) -> Optional[dict]:
        if not profile:
            return None
        return {
            "name": profile.name,
            "linkedin_url": profile.linkedin_url,
            "description": profile.description,
            "industry": profile.industry,
            "company_size": profile.company_size,
            "headquarters": profile.headquarters,
            "founded": profile.founded,
            "website": profile.website,
        }

    @staticmethod
    def _deserialize_company_profile(data: Optional[dict]) -> Optional[LinkedInCompanyProfile]:
        if not data:
            return None
        return LinkedInCompanyProfile(**data)

    @staticmethod
    def _serialize_person_profile(profile: LinkedInPersonProfile) -> dict:
        return {
            "name": profile.name,
            "linkedin_url": profile.linkedin_url,
            "title": profile.title,
            "company": profile.company,
            "location": profile.location,
            "summary": profile.summary,
            "experience": profile.experience,
            "education": profile.education,
            "skills": profile.skills,
            "email": profile.email,
            "phone": profile.phone,
        }

    @staticmethod
    def _deserialize_person_profile(data: dict) -> LinkedInPersonProfile:
        return LinkedInPersonProfile(**data)

    @staticmethod
    def _serialize_employee(emp: LinkedInEmployee) -> dict:
        return {
            "name": emp.name,
            "title": emp.title,
            "linkedin_url": emp.linkedin_url,
            "profile_image": emp.profile_image,
        }

    @staticmethod
    def _deserialize_employee(data: dict) -> LinkedInEmployee:
        return LinkedInEmployee(**data)

    def _get_empty_result(self) -> LinkedInData:
        """返回空结果 (用于错误时返回)"""
        return LinkedInData(
            collection_status="failed",
            error_message="Collection failed"
        )


# 便捷函数
async def collect_linkedin_data(seed: SeedData, config=None) -> LinkedInData:
    """收集 LinkedIn 数据的便捷函数"""
    collector = LinkedInCollector(config)
    return await collector.collect(seed)
