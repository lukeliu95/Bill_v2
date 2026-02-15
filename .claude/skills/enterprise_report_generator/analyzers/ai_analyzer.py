"""
AI 分析引擎

使用 Gemini API 将收集的原始数据转换为结构化的三层报告
"""
import asyncio
import logging
import json
import uuid
from datetime import datetime
from typing import Optional

from ..models import (
    SeedData,
    CollectedData,
    EnterpriseReport,
    ReportMeta,
    DataFreshness,
    Layer1BasicInfo,
    Layer2SalesApproach,
    Layer3Signals,
    Representative,
    EmployeeCount,
    Capital,
    Address,
    Product,
    Tags,
    ApproachSummary,
    Timing,
    Organization,
    DecisionFlow,
    KeyPerson,
    ApproachStrategy,
    FirstContactScript,
    OpportunityScore,
    OpportunityFactor,
    NewsItem,
    FundingEvent,
    HiringSignal,
    InvestmentInterest,
    DataSource,
)
from ..models.tag_vocabulary import validate_tags, get_scale_tag_by_employee_count
from ..utils.gemini_client import GeminiClient
from ..utils.gbizinfo_client import format_capital
from ..prompts import (
    BASIC_INFO_SYSTEM,
    build_basic_info_prompt,
    SALES_APPROACH_SYSTEM,
    build_sales_approach_prompt,
    SIGNALS_SYSTEM,
    build_signals_prompt,
    build_social_media_section,
)

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """
    AI 分析引擎

    将收集的原始数据通过 Gemini API 分析，生成结构化的三层报告
    """

    def __init__(self):
        self.errors: list[str] = []

    async def analyze(self, collected_data: CollectedData) -> EnterpriseReport:
        """
        分析收集的数据，生成完整报告

        Args:
            collected_data: 所有收集器的汇总输出

        Returns:
            EnterpriseReport
        """
        self.errors = []
        seed = collected_data.seed

        logger.info(f"[AIAnalyzer] 开始分析: {seed.company_name}")

        # Step 1: 分析基本信息
        layer1 = await self._analyze_basic_info(seed, collected_data.basic_info)

        # Step 2: 分析销售路径 (依赖 layer1)
        layer2 = await self._analyze_sales_approach(layer1, collected_data.sales_intel)

        # Step 3: 分析商机信号 (依赖 layer1，含社交媒体数据)
        layer3 = await self._analyze_signals(layer1, collected_data.signals, collected_data.social_media)

        # 构建完整报告
        now = datetime.now()
        report = EnterpriseReport(
            meta=ReportMeta(
                report_id=str(uuid.uuid4()),
                generated_at=now,
                last_updated=now,
                data_freshness=DataFreshness(
                    basic_info=collected_data.collected_at,
                    sales_approach=now,
                    signals=now,
                ),
                quality_score=self._calculate_quality_score(layer1, layer2, layer3),
            ),
            layer1_basic_info=layer1,
            layer2_sales_approach=layer2,
            layer3_signals=layer3,
        )

        logger.info(f"[AIAnalyzer] 分析完成，质量分数: {report.meta.quality_score}")

        return report

    async def _analyze_basic_info(
        self,
        seed: SeedData,
        basic_info_raw,
    ) -> Layer1BasicInfo:
        """分析基本信息"""
        logger.info("[AIAnalyzer] 分析基本信息...")

        # 准备输入数据
        gbizinfo_data = basic_info_raw.gbizinfo_data if basic_info_raw else None
        website_content = basic_info_raw.website_content if basic_info_raw else None

        # 先尝试从 gBizINFO 直接提取结构化数据
        layer1 = self._extract_from_gbizinfo(seed, gbizinfo_data)

        # 如果有官网内容，使用 AI 补充分析
        if website_content or (gbizinfo_data and not layer1.business_overview):
            prompt = build_basic_info_prompt(
                seed_data=seed.model_dump(),
                gbizinfo_data=gbizinfo_data,
                website_content=website_content,
            )

            async with GeminiClient() as client:
                ai_result, error = await client.generate_json(
                    prompt=prompt,
                    system_instruction=BASIC_INFO_SYSTEM,
                )

                if error:
                    self.errors.append(f"基本信息AI分析失败: {error}")
                    logger.warning(f"基本信息AI分析失败: {error}")
                elif ai_result:
                    # 合并 AI 分析结果
                    layer1 = self._merge_basic_info(layer1, ai_result)

        # 添加数据来源
        layer1.data_sources.append(DataSource(
            field="basic_info",
            source="gBizINFO API" if gbizinfo_data else "官网爬取",
            url=seed.website_url,
            fetched_at=datetime.now(),
        ))

        return layer1

    async def _analyze_sales_approach(
        self,
        layer1: Layer1BasicInfo,
        sales_intel_raw,
    ) -> Layer2SalesApproach:
        """分析销售路径"""
        logger.info("[AIAnalyzer] 分析销售路径...")

        # 默认结果
        layer2 = Layer2SalesApproach()

        if not sales_intel_raw:
            self.errors.append("无销售情报数据")
            return layer2

        # 构建 prompt
        prompt = build_sales_approach_prompt(
            basic_info=layer1.model_dump(),
            sales_intel_raw=sales_intel_raw.model_dump(),
        )

        async with GeminiClient() as client:
            ai_result, error = await client.generate_json(
                prompt=prompt,
                system_instruction=SALES_APPROACH_SYSTEM,
            )

            if error:
                self.errors.append(f"销售路径AI分析失败: {error}")
                logger.warning(f"销售路径AI分析失败: {error}")
                return layer2

            if ai_result:
                layer2 = self._parse_sales_approach(ai_result)

        return layer2

    async def _analyze_signals(
        self,
        layer1: Layer1BasicInfo,
        signals_raw,
        social_media_raw=None,
    ) -> Layer3Signals:
        """分析商机信号"""
        logger.info("[AIAnalyzer] 分析商机信号...")

        # 默认结果
        layer3 = Layer3Signals()

        if not signals_raw:
            self.errors.append("无商机信号数据")
            return layer3

        # 构建 prompt
        prompt = build_signals_prompt(
            basic_info=layer1.model_dump(),
            signals_raw=signals_raw.model_dump(),
        )

        # 如果有社交媒体数据，追加到 prompt
        if social_media_raw:
            social_section = build_social_media_section(social_media_raw.model_dump())
            if social_section:
                prompt += "\n\n" + social_section

        async with GeminiClient() as client:
            ai_result, error = await client.generate_json(
                prompt=prompt,
                system_instruction=SIGNALS_SYSTEM,
            )

            if error:
                self.errors.append(f"商机信号AI分析失败: {error}")
                logger.warning(f"商机信号AI分析失败: {error}")
                return layer3

            if ai_result:
                layer3 = self._parse_signals(ai_result)

        return layer3

    def _extract_from_gbizinfo(
        self,
        seed: SeedData,
        gbizinfo_data: dict | None,
    ) -> Layer1BasicInfo:
        """从 gBizINFO 数据直接提取结构化信息"""
        data = gbizinfo_data or {}

        # 员工数
        employee_count = None
        if data.get("employee_number"):
            employee_count = EmployeeCount(
                value=data["employee_number"],
                source="gBizINFO",
            )

        # 资本金
        capital = None
        if data.get("capital_stock"):
            capital = Capital(
                value=data["capital_stock"],
                display=format_capital(data["capital_stock"]),
            )

        # 地址解析
        address = None
        location = data.get("location") or seed.address
        if location:
            address = Address(
                full=location,
                prefecture=self._extract_prefecture(location),
            )

        # 代表人
        representative = None
        if data.get("representative_name"):
            representative = Representative(
                name=data["representative_name"],
                title=data.get("representative_position", "代表取締役"),
            )

        # 成立日期
        established = None
        if data.get("date_of_establishment"):
            established = data["date_of_establishment"]
        elif data.get("founding_year"):
            established = f"{data['founding_year']}年"

        # 自动生成规模标签
        scale_tags = []
        if employee_count and employee_count.value:
            auto_tag = get_scale_tag_by_employee_count(employee_count.value)
            if auto_tag:
                scale_tags.append(auto_tag)

        return Layer1BasicInfo(
            company_name=data.get("name") or seed.company_name,
            company_name_kana=data.get("kana"),
            corporate_number=seed.corporate_number,
            established=established,
            representative=representative,
            employee_count=employee_count,
            capital=capital,
            address=address,
            website=data.get("company_url") or seed.website_url,
            business_overview=data.get("business_summary"),
            tags=Tags(scale=scale_tags),
            data_sources=[],
        )

    def _merge_basic_info(
        self,
        layer1: Layer1BasicInfo,
        ai_result: dict,
    ) -> Layer1BasicInfo:
        """合并 AI 分析结果到基本信息"""
        # 业务概要
        if ai_result.get("business_overview") and not layer1.business_overview:
            layer1.business_overview = ai_result["business_overview"]

        # 产品
        if ai_result.get("main_products"):
            for p in ai_result["main_products"]:
                layer1.main_products.append(Product(
                    name=p.get("name", ""),
                    category=p.get("category", "Other"),
                    description=p.get("description"),
                    target_market=p.get("target_market", "B2B"),
                ))

        # 标签 (合并并验证)
        if ai_result.get("tags"):
            ai_tags = ai_result["tags"]
            new_scale = ai_tags.get("scale", [])
            new_industry = ai_tags.get("industry", [])
            new_chars = ai_tags.get("characteristics", [])

            # 验证标签
            valid, invalid = validate_tags(new_scale, new_industry, new_chars)
            if invalid:
                logger.warning(f"AI生成了无效标签: {invalid}")

            # 合并
            layer1.tags.scale = list(set(layer1.tags.scale + [t for t in new_scale if t in valid]))[:3]
            layer1.tags.industry = list(set(layer1.tags.industry + [t for t in new_industry if t in valid]))[:3]
            layer1.tags.characteristics = list(set(layer1.tags.characteristics + [t for t in new_chars if t in valid]))[:3]

        # 其他字段补充
        if ai_result.get("established") and not layer1.established:
            layer1.established = ai_result["established"]

        if ai_result.get("representative") and not layer1.representative:
            rep = ai_result["representative"]
            rep_name = rep.get("name") or ""
            if rep_name:  # 只在有名字时创建
                layer1.representative = Representative(
                    name=rep_name,
                    title=rep.get("title") or "代表取締役",
                )

        if ai_result.get("employee_count") and not layer1.employee_count:
            ec = ai_result["employee_count"]
            layer1.employee_count = EmployeeCount(
                value=ec.get("value"),
                as_of=ec.get("as_of"),
                source=ec.get("source", "官网"),
            )

        return layer1

    def _parse_sales_approach(self, ai_result: dict) -> Layer2SalesApproach:
        """解析销售路径 AI 结果"""
        layer2 = Layer2SalesApproach()

        # Summary
        if ai_result.get("summary"):
            s = ai_result["summary"]
            layer2.summary = ApproachSummary(
                difficulty=s.get("difficulty", 3),
                difficulty_label=s.get("difficulty_label", "中"),
                recommended_channel=s.get("recommended_channel"),
                decision_speed=s.get("decision_speed"),
                overview=s.get("overview"),
            )

        # Timing
        if ai_result.get("timing"):
            t = ai_result["timing"]
            layer2.timing = Timing(
                is_good_timing=t.get("is_good_timing", False),
                reasons=t.get("reasons", []),
                recommended_period=t.get("recommended_period"),
            )

        # Organization
        if ai_result.get("organization"):
            o = ai_result["organization"]
            decision_flow = None
            if o.get("decision_flow"):
                df = o["decision_flow"]
                decision_flow = DecisionFlow(
                    small_deal=df.get("small_deal"),
                    medium_deal=df.get("medium_deal"),
                    large_deal=df.get("large_deal"),
                )
            # 清理组织结构类型
            structure_type = self._normalize_structure_type(o.get("structure_type", "不明"))
            layer2.organization = Organization(
                structure_type=structure_type,
                description=o.get("description"),
                decision_flow=decision_flow,
            )

        # Key Persons
        if ai_result.get("key_persons"):
            for kp in ai_result["key_persons"]:
                # 处理 source 字段，确保是有效值
                source = kp.get("source")
                if source not in ("linkedin", "search", "team_page", "manual"):
                    source = None

                layer2.key_persons.append(KeyPerson(
                    name=kp.get("name", ""),
                    title=kp.get("title"),
                    department=kp.get("department"),
                    background=kp.get("background"),
                    approach_hint=kp.get("approach_hint"),
                    linkedin_search_query=kp.get("linkedin_search_query"),
                    confidence=self._normalize_confidence(kp.get("confidence", "low")),
                    # 联系方式
                    email=kp.get("email"),
                    phone=kp.get("phone"),
                    # LinkedIn 扩展字段
                    linkedin_url=kp.get("linkedin_url"),
                    linkedin_summary=kp.get("linkedin_summary"),
                    skills=kp.get("skills"),
                    source=source,
                ))

        # Approach Strategy
        if ai_result.get("approach_strategy"):
            a = ai_result["approach_strategy"]
            first_contact = None
            if a.get("first_contact_script"):
                fc = a["first_contact_script"]
                first_contact = FirstContactScript(
                    subject_template=fc.get("subject_template"),
                    body_template=fc.get("body_template"),
                )
            layer2.approach_strategy = ApproachStrategy(
                recommended_method=a.get("recommended_method"),
                first_contact_script=first_contact,
                talking_points=a.get("talking_points", []),
                pitfalls_to_avoid=a.get("pitfalls_to_avoid", []),
            )

        return layer2

    def _parse_signals(self, ai_result: dict) -> Layer3Signals:
        """解析商机信号 AI 结果"""
        layer3 = Layer3Signals()

        # Opportunity Score
        if ai_result.get("opportunity_score"):
            os = ai_result["opportunity_score"]
            factors = []
            for f in os.get("factors", []):
                factors.append(OpportunityFactor(
                    factor=f.get("factor", ""),
                    impact=f.get("impact", "positive"),
                    weight=f.get("weight", 0.1),
                ))
            layer3.opportunity_score = OpportunityScore(
                value=os.get("value", 50),
                label=os.get("label", "中"),
                factors=factors,
            )

        # Recent News
        if ai_result.get("recent_news"):
            for n in ai_result["recent_news"]:
                layer3.recent_news.append(NewsItem(
                    date=n.get("date"),
                    type=self._normalize_news_type(n.get("type", "其他")),
                    title=n.get("title", ""),
                    summary=n.get("summary"),
                    implication=n.get("implication"),
                    source=n.get("source"),
                    url=n.get("url"),
                ))

        # Funding History
        if ai_result.get("funding_history"):
            for f in ai_result["funding_history"]:
                layer3.funding_history.append(FundingEvent(
                    round=f.get("round"),
                    date=f.get("date"),
                    amount=f.get("amount"),
                    lead_investor=f.get("lead_investor"),
                    source=f.get("source"),
                ))

        # Hiring Signals
        if ai_result.get("hiring_signals"):
            for h in ai_result["hiring_signals"]:
                layer3.hiring_signals.append(HiringSignal(
                    position_type=self._normalize_position_type(h.get("position_type", "其他")),
                    description=h.get("description"),
                    implication=h.get("implication"),
                ))

        # Investment Interests
        if ai_result.get("investment_interests"):
            for i in ai_result["investment_interests"]:
                layer3.investment_interests.append(InvestmentInterest(
                    category=self._normalize_investment_category(i.get("category", "其他")),
                    confidence=i.get("confidence", "low"),
                    reasoning=i.get("reasoning"),
                ))

        return layer3

    @staticmethod
    def _normalize_structure_type(value: str) -> str:
        """标准化组织结构类型"""
        if not value:
            return "不明"

        # 移除括号及其内容
        import re
        value = re.sub(r'[（(][^）)]*[）)]', '', value).strip()

        # 映射表
        mapping = {
            "扁平": "扁平",
            "フラット": "扁平",
            "flat": "扁平",
            "层级": "层级",
            "階層": "层级",
            "hierarchical": "层级",
            "矩阵": "矩阵",
            "マトリックス": "矩阵",
            "matrix": "矩阵",
        }

        # 尝试精确匹配
        if value in mapping:
            return mapping[value]

        # 尝试部分匹配
        for key, mapped in mapping.items():
            if key in value.lower():
                return mapped

        return "不明"

    @staticmethod
    def _normalize_confidence(value: str) -> str:
        """标准化可信度"""
        if not value:
            return "low"

        value = value.lower().strip()
        if value in ["high", "高"]:
            return "high"
        elif value in ["medium", "中", "mid"]:
            return "medium"
        return "low"

    @staticmethod
    def _normalize_position_type(value: str) -> str:
        """标准化职位类型"""
        if not value:
            return "其他"

        value_lower = value.lower().strip()
        # 销售相关
        if "销售" in value or "sales" in value_lower or "営業" in value:
            return "销售"
        # 工程师相关
        if "工程" in value or "engineer" in value_lower or "エンジニア" in value or "开发" in value or "dev" in value_lower:
            return "工程师"
        # 营销相关
        if "营销" in value or "marketing" in value_lower or "マーケ" in value:
            return "营销"

        return "其他"

    @staticmethod
    def _normalize_investment_category(value: str) -> str:
        """标准化投资领域类别"""
        if not value:
            return "其他"

        value_lower = value.lower().strip()
        # 销售支持
        if "销售" in value or "sales" in value_lower or "営業" in value:
            return "销售支持"
        # 营销
        if "营销" in value or "marketing" in value_lower or "マーケ" in value or "广告" in value or "PR" in value:
            return "营销"
        # 招聘
        if "招聘" in value or "hiring" in value_lower or "採用" in value or "人材" in value or "人才" in value:
            return "招聘"
        # 基础设施
        if "基础设施" in value or "infrastructure" in value_lower or "インフラ" in value or "IT" in value:
            return "基础设施"

        return "其他"

    @staticmethod
    def _normalize_news_type(value: str) -> str:
        """标准化新闻类型"""
        if not value:
            return "其他"

        value_lower = value.lower().strip()
        # 融资相关
        if "融资" in value or "funding" in value_lower or "資金調達" in value or "調達" in value:
            return "融资"
        # 业务合作
        if "合作" in value or "partnership" in value_lower or "提携" in value or "協業" in value:
            return "业务合作"
        # 人事变动
        if "人事" in value or "任命" in value or "就任" in value or "personnel" in value_lower:
            return "人事变动"
        # 新产品
        if "产品" in value or "製品" in value or "product" in value_lower or "リリース" in value or "発表" in value or "服务" in value:
            return "新产品"

        return "其他"

    def _calculate_quality_score(
        self,
        layer1: Layer1BasicInfo,
        layer2: Layer2SalesApproach,
        layer3: Layer3Signals,
    ) -> int:
        """
        计算报告质量分数

        分数计算:
        - 基本信息完整性: 30分
        - 销售信息有用性: 40分
        - 商机信号新鲜度: 30分
        """
        score = 0

        # Layer 1: 基本信息完整性 (30分)
        l1_score = 0
        if layer1.company_name:
            l1_score += 5
        if layer1.representative:
            l1_score += 5
        if layer1.employee_count and layer1.employee_count.value:
            l1_score += 5
        if layer1.business_overview:
            l1_score += 5
        if layer1.main_products:
            l1_score += 5
        if layer1.tags.industry:
            l1_score += 5
        score += min(l1_score, 30)

        # Layer 2: 销售信息有用性 (40分)
        l2_score = 0
        if layer2.summary:
            l2_score += 10
        if layer2.key_persons:
            l2_score += 15
        if layer2.approach_strategy:
            l2_score += 10
        if layer2.organization and layer2.organization.structure_type != "不明":
            l2_score += 5
        score += min(l2_score, 40)

        # Layer 3: 商机信号新鲜度 (30分)
        l3_score = 0
        if layer3.opportunity_score:
            l3_score += 10
        if layer3.recent_news:
            l3_score += 10
        if layer3.hiring_signals:
            l3_score += 5
        if layer3.funding_history:
            l3_score += 5
        score += min(l3_score, 30)

        # 减分: 错误
        score -= len(self.errors) * 5

        return max(0, min(100, score))

    @staticmethod
    def _extract_prefecture(location: str) -> Optional[str]:
        """从地址中提取都道府县"""
        prefectures = [
            "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
            "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
            "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
            "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
            "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
            "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
            "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
        ]

        for pref in prefectures:
            if pref in location:
                return pref

        return None


# ============================================================
# 便捷函数
# ============================================================

async def analyze_collected_data(collected_data: CollectedData) -> EnterpriseReport:
    """
    分析收集数据的便捷函数

    Args:
        collected_data: 收集的数据

    Returns:
        EnterpriseReport
    """
    analyzer = AIAnalyzer()
    return await analyzer.analyze(collected_data)


if __name__ == "__main__":
    # 测试需要先有收集的数据
    print("AIAnalyzer 模块加载成功")
    print("请通过 main.py 进行完整流程测试")
