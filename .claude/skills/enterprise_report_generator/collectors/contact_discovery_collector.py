"""
联系方式发现收集器

自动搜索企业关键人物的联系方式：
1. 复用 SalesIntel 的 LinkedIn 员工数据 → BrightData Person Profile 获取 email/phone
2. Serper 搜索: 役員/CTO/営業部長 + 連絡先
3. Wantedly 搜索
4. PR TIMES 搜索 → PR 联系人
5. 官网 /contact/、/about/ 页面爬取 → 电话/邮箱/表单URL
6. 交叉验证去重 → 生成推奨コンタクトルート
"""
import asyncio
import logging
import re
from typing import Optional
from urllib.parse import urljoin

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

from .base_collector import BaseCollector
from .contact_models import (
    ContactDiscoveryRaw,
    DiscoveredContact,
    CompanyContactInfo,
    ContactRoute,
)
from ..models import SeedData, SalesIntelRaw
from ..utils.serper_client import SerperClient
from ..utils.brightdata_client import BrightDataClient
from ..config import get_config

logger = logging.getLogger(__name__)

# 邮箱正则
EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
    re.IGNORECASE
)

# 日本电话正则 (03-xxxx-xxxx, 0120-xxx-xxx, 050-xxxx-xxxx, 070/080/090-xxxx-xxxx)
PHONE_PATTERN = re.compile(
    r'(?:0\d{1,4}[-\s]?\d{1,4}[-\s]?\d{3,4})',
)

# 排除的邮箱域名（通用服务商，不是企业邮箱）
EXCLUDED_EMAIL_DOMAINS = {
    "example.com", "test.com", "gmail.com", "yahoo.co.jp", "yahoo.com",
    "hotmail.com", "outlook.com", "icloud.com",
    "wantedly.com", "prtimes.jp", "facebook.com", "twitter.com",
}

# 官网联系页面候选路径
CONTACT_PAGE_PATHS = [
    "/contact", "/contact/", "/inquiry", "/inquiry/",
    "/お問い合わせ", "/お問合せ",
    "/company/contact", "/about/contact",
]

# 关于页面候选路径
ABOUT_PAGE_PATHS = [
    "/about", "/about/", "/company", "/company/",
    "/about-us", "/corporate", "/corporate/",
    "/会社概要", "/企業情報",
]


class ContactDiscoveryCollector(BaseCollector[ContactDiscoveryRaw]):
    """
    联系方式发现收集器

    自动搜索企业关键人物的联系方式，输出推奨コンタクトルート
    """

    name = "ContactDiscoveryCollector"
    cache_category = "contact_discovery"

    def __init__(
        self,
        use_cache: bool = True,
        sales_intel_data: Optional[SalesIntelRaw] = None,
        max_linkedin_lookups: int = 3,
    ):
        """
        初始化

        Args:
            use_cache: 是否使用缓存
            sales_intel_data: SalesIntel 已采集数据（复用 LinkedIn 员工列表）
            max_linkedin_lookups: 最多查询几个 LinkedIn 个人资料
        """
        super().__init__(use_cache)
        self.sales_intel_data = sales_intel_data
        self.max_linkedin_lookups = max_linkedin_lookups
        self._config = get_config()

    async def collect(self, seed: SeedData) -> ContactDiscoveryRaw:
        """执行联系方式发现"""
        result = ContactDiscoveryRaw()
        all_contacts: list[DiscoveredContact] = []
        company_contacts = CompanyContactInfo()

        # 并行执行多个搜索任务
        tasks = [
            self._search_executives(seed.company_name),
            self._search_wantedly(seed.company_name),
            self._search_prtimes(seed.company_name),
            self._crawl_contact_pages(seed.website_url),
        ]

        # 如果有 LinkedIn 员工数据，并行查询关键人物的详细资料
        linkedin_task = self._lookup_linkedin_persons(seed.company_name)
        tasks.append(linkedin_task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理高管搜索结果
        if not isinstance(results[0], Exception) and results[0]:
            exec_contacts = results[0]
            all_contacts.extend(exec_contacts)
            result.sources_used.append("serper_executive_search")

        # 处理 Wantedly 结果
        if not isinstance(results[1], Exception) and results[1]:
            wantedly_contacts, wantedly_raw = results[1]
            all_contacts.extend(wantedly_contacts)
            result.wantedly_results = wantedly_raw
            result.sources_used.append("wantedly")

        # 处理 PR TIMES 结果
        if not isinstance(results[2], Exception) and results[2]:
            pr_contacts, pr_raw = results[2]
            all_contacts.extend(pr_contacts)
            result.prtimes_results = pr_raw
            result.sources_used.append("prtimes")

        # 处理官网联系页面
        if not isinstance(results[3], Exception) and results[3]:
            web_contacts, web_company, web_content = results[3]
            all_contacts.extend(web_contacts)
            company_contacts = web_company
            result.website_contact_content = web_content
            result.sources_used.append("website_contact")

        # 处理 LinkedIn 个人资料
        if not isinstance(results[4], Exception) and results[4]:
            linkedin_contacts = results[4]
            all_contacts.extend(linkedin_contacts)
            result.sources_used.append("linkedin_person_profile")

        # 处理异常
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                error_msg = f"Task {i} failed: {str(r)}"
                self.add_error(error_msg)
                result.errors.append(error_msg)

        # 去重合并联系人
        result.key_persons = self._deduplicate_contacts(all_contacts)
        result.company_contacts = company_contacts

        # 生成推奨コンタクトルート
        result.recommended_routes = self._build_contact_routes(
            result.key_persons, company_contacts
        )

        return result

    def _get_empty_result(self) -> ContactDiscoveryRaw:
        return ContactDiscoveryRaw()

    def _deserialize(self, data: dict) -> ContactDiscoveryRaw:
        return ContactDiscoveryRaw(**data)

    # ================================================================
    # 搜索任务
    # ================================================================

    async def _search_executives(self, company_name: str) -> list[DiscoveredContact]:
        """Serper 搜索企业高管联系方式"""
        contacts = []
        queries = [
            f'"{company_name}" 役員 OR CTO OR 営業部長 連絡先 OR メール',
            f'"{company_name}" 代表取締役 OR CEO OR 社長',
        ]

        async with SerperClient() as serper:
            for query in queries:
                try:
                    resp = await serper.search(query, num_results=5)
                    for r in resp.results:
                        # 从搜索结果摘要中提取邮箱/电话
                        emails = self._extract_emails(r.snippet + " " + r.title)
                        phones = self._extract_phones(r.snippet)

                        if emails or phones:
                            contacts.append(DiscoveredContact(
                                name=self._extract_person_name(r.title, r.snippet),
                                title=self._extract_title(r.title, r.snippet),
                                email=emails[0] if emails else None,
                                phone=phones[0] if phones else None,
                                source="search",
                                confidence="low",
                                notes=f"From: {r.link}",
                            ))
                except Exception as e:
                    self.add_error(f"Executive search failed: {e}")

        return contacts

    async def _search_wantedly(
        self, company_name: str
    ) -> tuple[list[DiscoveredContact], list[dict]]:
        """Wantedly 搜索企业成员"""
        contacts = []
        raw_results = []

        try:
            async with SerperClient() as serper:
                resp = await serper.search(
                    f'"{company_name}" site:wantedly.com',
                    num_results=5,
                )
                for r in resp.results:
                    raw_results.append({
                        "title": r.title,
                        "link": r.link,
                        "snippet": r.snippet,
                    })
                    # Wantedly 页面通常有人物名和职位
                    name = self._extract_person_name(r.title, r.snippet)
                    if name and name != "不明":
                        contacts.append(DiscoveredContact(
                            name=name,
                            title=self._extract_title(r.title, r.snippet),
                            source="wantedly",
                            confidence="medium",
                            notes=f"Wantedly: {r.link}",
                        ))
        except Exception as e:
            self.add_error(f"Wantedly search failed: {e}")

        return contacts, raw_results

    async def _search_prtimes(
        self, company_name: str
    ) -> tuple[list[DiscoveredContact], list[dict]]:
        """PR TIMES 搜索 → 提取 PR 联系人"""
        contacts = []
        raw_results = []

        try:
            async with SerperClient() as serper:
                resp = await serper.search(
                    f'"{company_name}" site:prtimes.jp 問い合わせ先',
                    num_results=5,
                )
                for r in resp.results:
                    raw_results.append({
                        "title": r.title,
                        "link": r.link,
                        "snippet": r.snippet,
                    })
                    # PR TIMES 摘要经常包含联系邮箱
                    emails = self._extract_emails(r.snippet)
                    phones = self._extract_phones(r.snippet)
                    if emails or phones:
                        contacts.append(DiscoveredContact(
                            name=self._extract_person_name(r.title, r.snippet),
                            title="広報担当",
                            email=emails[0] if emails else None,
                            phone=phones[0] if phones else None,
                            source="prtimes",
                            confidence="medium",
                            notes=f"PR TIMES: {r.link}",
                        ))
        except Exception as e:
            self.add_error(f"PR TIMES search failed: {e}")

        return contacts, raw_results

    async def _crawl_contact_pages(
        self, website_url: str
    ) -> tuple[list[DiscoveredContact], CompanyContactInfo, Optional[str]]:
        """爬取官网联系页面，提取电话/邮箱/表单URL"""
        contacts = []
        company_info = CompanyContactInfo()
        all_content = ""

        if not website_url:
            return contacts, company_info, None

        # 构建候选 URL
        base_url = website_url.rstrip("/")
        candidate_urls = [urljoin(base_url + "/", path.lstrip("/")) for path in CONTACT_PAGE_PATHS]

        try:
            browser_config = BrowserConfig(headless=True)
            crawl_config = CrawlerRunConfig(
                wait_until="domcontentloaded",
                page_timeout=15000,
            )

            async with AsyncWebCrawler(config=browser_config) as crawler:
                for url in candidate_urls[:4]:  # 最多尝试4个URL
                    try:
                        result = await asyncio.wait_for(
                            crawler.arun(url=url, config=crawl_config),
                            timeout=20,
                        )
                        if result.success and result.markdown:
                            content = result.markdown[:5000]
                            all_content += f"\n\n--- {url} ---\n{content}"

                            # 提取邮箱
                            emails = self._extract_emails(content)
                            for email in emails:
                                domain = email.split("@")[1].lower()
                                if domain in EXCLUDED_EMAIL_DOMAINS:
                                    continue
                                # 分类邮箱
                                email_lower = email.lower()
                                if any(k in email_lower for k in ["info", "contact", "support"]):
                                    company_info.main_email = company_info.main_email or email
                                elif any(k in email_lower for k in ["ir", "investor"]):
                                    company_info.ir_email = email
                                elif any(k in email_lower for k in ["pr", "press", "広報"]):
                                    company_info.pr_email = email
                                elif any(k in email_lower for k in ["recruit", "hr", "採用", "career"]):
                                    company_info.recruit_email = email
                                else:
                                    company_info.main_email = company_info.main_email or email

                            # 提取电话
                            phones = self._extract_phones(content)
                            if phones:
                                company_info.main_phone = company_info.main_phone or phones[0]

                            # 检测问い合わせフォーム
                            if any(kw in content.lower() for kw in ["問い合わせ", "お問合せ", "contact form", "inquiry"]):
                                company_info.contact_form_url = company_info.contact_form_url or url

                    except (asyncio.TimeoutError, Exception) as e:
                        logger.debug(f"Failed to crawl {url}: {e}")
                        continue

        except Exception as e:
            self.add_error(f"Website crawl failed: {e}")

        return contacts, company_info, all_content if all_content else None

    async def _lookup_linkedin_persons(self, company_name: str) -> list[DiscoveredContact]:
        """从已有 LinkedIn 员工数据中查询关键人物的详细联系方式"""
        contacts = []

        if not self._config.has_linkedin_config():
            return contacts

        # 从 SalesIntel 数据中获取关键人物的 LinkedIn URL
        linkedin_urls = []
        if self.sales_intel_data and self.sales_intel_data.linkedin_profiles:
            key_persons = self.sales_intel_data.linkedin_profiles.get("key_persons", [])
            for person in key_persons:
                url = person.get("url") or person.get("linkedin_url")
                if url:
                    linkedin_urls.append((person.get("name", "不明"), url))

        if not linkedin_urls:
            return contacts

        # 最多查询 N 个人
        client = BrightDataClient()
        for name, url in linkedin_urls[:self.max_linkedin_lookups]:
            try:
                profile = await client.get_person_profile(url)
                if profile:
                    contacts.append(DiscoveredContact(
                        name=profile.name or name,
                        title=profile.title,
                        email=profile.email,
                        phone=profile.phone,
                        linkedin_url=profile.linkedin_url,
                        source="linkedin",
                        confidence="high" if (profile.email or profile.phone) else "medium",
                        notes=f"LinkedIn: {profile.summary[:100]}" if profile.summary else None,
                    ))
            except Exception as e:
                self.add_error(f"LinkedIn lookup failed for {name}: {e}")

        return contacts

    # ================================================================
    # 工具方法
    # ================================================================

    def _extract_emails(self, text: str) -> list[str]:
        """从文本中提取邮箱地址"""
        if not text:
            return []
        emails = EMAIL_PATTERN.findall(text)
        # 去重 + 排除通用域名
        seen = set()
        result = []
        for email in emails:
            email_lower = email.lower()
            domain = email_lower.split("@")[1]
            if email_lower not in seen and domain not in EXCLUDED_EMAIL_DOMAINS:
                seen.add(email_lower)
                result.append(email)
        return result

    def _extract_phones(self, text: str) -> list[str]:
        """从文本中提取日本电话号码"""
        if not text:
            return []
        phones = PHONE_PATTERN.findall(text)
        # 去重
        seen = set()
        result = []
        for phone in phones:
            normalized = phone.replace("-", "").replace(" ", "")
            if normalized not in seen and len(normalized) >= 10:
                seen.add(normalized)
                result.append(phone)
        return result

    def _extract_person_name(self, title: str, snippet: str) -> str:
        """尝试从标题/摘要中提取人名"""
        # 日本人名模式：2-4个汉字 + 空格 + 2-4个汉字
        name_pattern = re.compile(r'([一-龥]{1,4})\s*([一-龥]{1,4})\s*(?:氏|さん|様)')
        for text in [title, snippet]:
            match = name_pattern.search(text)
            if match:
                return f"{match.group(1)} {match.group(2)}"

        # 英文名
        eng_pattern = re.compile(r'([A-Z][a-z]+)\s+([A-Z][a-z]+)')
        for text in [title, snippet]:
            match = eng_pattern.search(text)
            if match:
                return f"{match.group(1)} {match.group(2)}"

        return "不明"

    def _extract_title(self, title: str, snippet: str) -> Optional[str]:
        """尝试提取职位"""
        title_patterns = [
            r'(代表取締役|CEO|CTO|COO|CFO|CMO|VP|取締役|執行役員|部長|課長|マネージャー)',
            r'(営業部長|技術部長|経営企画|事業開発|広報|人事)',
        ]
        for text in [title, snippet]:
            for pattern in title_patterns:
                match = re.search(pattern, text)
                if match:
                    return match.group(1)
        return None

    def _deduplicate_contacts(self, contacts: list[DiscoveredContact]) -> list[DiscoveredContact]:
        """去重合并联系人"""
        if not contacts:
            return []

        # 按 name 分组
        by_name: dict[str, list[DiscoveredContact]] = {}
        for c in contacts:
            key = c.name.strip()
            if key == "不明":
                # 不明的按 email 去重
                if c.email:
                    key = c.email
                else:
                    continue  # 跳过既无名也无邮箱的
            if key not in by_name:
                by_name[key] = []
            by_name[key].append(c)

        # 合并同一人的信息
        merged = []
        confidence_order = {"high": 3, "medium": 2, "low": 1}

        for name, group in by_name.items():
            # 选择可信度最高的作为基础
            group.sort(key=lambda c: confidence_order.get(c.confidence, 0), reverse=True)
            base = group[0].model_copy()

            # 从其他记录补充缺失字段
            for other in group[1:]:
                if not base.email and other.email:
                    base.email = other.email
                if not base.phone and other.phone:
                    base.phone = other.phone
                if not base.title and other.title:
                    base.title = other.title
                if not base.linkedin_url and other.linkedin_url:
                    base.linkedin_url = other.linkedin_url
                if not base.twitter_url and other.twitter_url:
                    base.twitter_url = other.twitter_url
                if not base.department and other.department:
                    base.department = other.department

            merged.append(base)

        # 按可信度排序
        merged.sort(key=lambda c: confidence_order.get(c.confidence, 0), reverse=True)
        return merged

    def _build_contact_routes(
        self,
        contacts: list[DiscoveredContact],
        company_info: CompanyContactInfo,
    ) -> list[ContactRoute]:
        """构建推奨コンタクトルート"""
        routes = []
        rank = 1

        # 路线1: 有 email 的经营层
        for c in contacts:
            if c.email and c.title and any(
                t in (c.title or "") for t in ["代表", "CEO", "CTO", "取締役", "VP"]
            ):
                routes.append(ContactRoute(
                    rank=rank,
                    route_type="経営層直接",
                    target_person=f"{c.name} ({c.title})",
                    channel="メール",
                    detail=f"{c.email} 宛にメールを送信。{c.notes or ''}",
                    success_probability="high",
                ))
                rank += 1
                break

        # 路线2: LinkedIn InMail
        linkedin_contacts = [c for c in contacts if c.linkedin_url]
        if linkedin_contacts:
            c = linkedin_contacts[0]
            routes.append(ContactRoute(
                rank=rank,
                route_type="LinkedInアプローチ",
                target_person=f"{c.name} ({c.title or '役職不明'})",
                channel="LinkedIn",
                detail=f"LinkedIn InMail でコンタクト: {c.linkedin_url}",
                success_probability="medium",
            ))
            rank += 1

        # 路线3: 問い合わせフォーム
        if company_info.contact_form_url:
            routes.append(ContactRoute(
                rank=rank,
                route_type="フォーム経由",
                target_person=None,
                channel="フォーム",
                detail=f"公式問い合わせフォームから送信: {company_info.contact_form_url}",
                success_probability="medium",
            ))
            rank += 1

        # 路线4: 代表メール
        if company_info.main_email:
            routes.append(ContactRoute(
                rank=rank,
                route_type="代表メール",
                target_person=None,
                channel="メール",
                detail=f"代表メール: {company_info.main_email}",
                success_probability="low",
            ))
            rank += 1

        # 路线5: 代表電話
        if company_info.main_phone:
            routes.append(ContactRoute(
                rank=rank,
                route_type="電話アプローチ",
                target_person=None,
                channel="電話",
                detail=f"代表電話: {company_info.main_phone} に架電",
                success_probability="low",
            ))
            rank += 1

        # 如果完全没有路线，添加通用建议
        if not routes:
            routes.append(ContactRoute(
                rank=1,
                route_type="Web検索補完",
                target_person=None,
                channel="手動調査",
                detail="自動収集では十分な連絡先が見つかりませんでした。手動で深掘り調査を推奨します。",
                success_probability="low",
            ))

        return routes


# 便捷函数
async def collect_contact_discovery(
    seed: SeedData,
    sales_intel_data: Optional[SalesIntelRaw] = None,
    use_cache: bool = True,
) -> ContactDiscoveryRaw:
    """联系方式发现的便捷函数"""
    collector = ContactDiscoveryCollector(
        use_cache=use_cache,
        sales_intel_data=sales_intel_data,
    )
    return await collector.run(seed)
