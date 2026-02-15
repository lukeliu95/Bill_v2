"""
企业营业报告 - Pydantic 数据模型定义

基于规格文档第四章定义的数据结构
"""
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


# ============================================================
# 通用类型
# ============================================================

class DataSource(BaseModel):
    """数据来源记录"""
    field: str = Field(..., description="字段名")
    source: str = Field(..., description="数据来源")
    url: Optional[str] = Field(None, description="来源URL")
    fetched_at: datetime = Field(default_factory=datetime.now, description="获取时间")


# ============================================================
# Layer 1: 企业基本信息
# ============================================================

class Representative(BaseModel):
    """代表人信息"""
    name: str = Field(..., description="代表人姓名")
    title: str = Field(default="代表取締役", description="职务")


class EmployeeCount(BaseModel):
    """员工数信息"""
    value: Optional[int] = Field(None, description="员工数")
    as_of: Optional[str] = Field(None, description="数据时点")
    source: Optional[str] = Field(None, description="数据来源")


class Capital(BaseModel):
    """资本金信息"""
    value: Optional[int] = Field(None, description="资本金(日元)")
    display: Optional[str] = Field(None, description="显示格式(如: 9,000万円)")


class Address(BaseModel):
    """地址信息"""
    full: str = Field(..., description="完整地址")
    prefecture: Optional[str] = Field(None, description="都道府县")
    city: Optional[str] = Field(None, description="市区町村")


class Product(BaseModel):
    """产品信息"""
    name: str = Field(..., description="产品名称")
    category: Literal["SaaS", "Hardware", "Service", "Other"] = Field(
        default="Other", description="产品类别"
    )
    description: Optional[str] = Field(None, description="产品描述")
    target_market: Literal["B2B", "B2C", "Both"] = Field(
        default="B2B", description="目标市场"
    )


class Tags(BaseModel):
    """企业标签"""
    scale: list[str] = Field(default_factory=list, description="规模标签")
    industry: list[str] = Field(default_factory=list, description="行业标签")
    characteristics: list[str] = Field(default_factory=list, description="特征标签")


class Layer1BasicInfo(BaseModel):
    """第一层: 企业基本信息"""
    company_name: str = Field(..., description="企业名称")
    company_name_kana: Optional[str] = Field(None, description="企业名称假名")
    corporate_number: str = Field(..., description="法人番号(13位)")
    established: Optional[str] = Field(None, description="成立日期(YYYY年M月)")
    representative: Optional[Representative] = Field(None, description="代表人")
    employee_count: Optional[EmployeeCount] = Field(None, description="员工数")
    capital: Optional[Capital] = Field(None, description="资本金")
    address: Optional[Address] = Field(None, description="所在地")
    website: Optional[str] = Field(None, description="官网URL")
    business_overview: Optional[str] = Field(None, description="业务概要(100-300字)")
    main_products: list[Product] = Field(default_factory=list, description="主要产品")
    tags: Tags = Field(default_factory=Tags, description="企业标签")
    data_sources: list[DataSource] = Field(default_factory=list, description="数据来源")


# ============================================================
# Layer 2: 销售接触指南
# ============================================================

class ApproachSummary(BaseModel):
    """接触概要"""
    difficulty: int = Field(..., ge=1, le=5, description="销售难度(1-5)")
    difficulty_label: Literal["低", "中", "高"] = Field(..., description="难度标签")
    recommended_channel: Optional[str] = Field(None, description="推荐接触渠道")
    decision_speed: Optional[str] = Field(None, description="决策速度")
    overview: Optional[str] = Field(None, description="概述(100-200字)")


class Timing(BaseModel):
    """接触时机"""
    is_good_timing: bool = Field(default=False, description="是否为好时机")
    reasons: list[str] = Field(default_factory=list, description="理由")
    recommended_period: Optional[str] = Field(None, description="推荐接触时期")


class DecisionFlow(BaseModel):
    """决策流程"""
    small_deal: Optional[str] = Field(None, description="小额决策流程(月额10万円以下)")
    medium_deal: Optional[str] = Field(None, description="中额决策流程(月额10-50万円)")
    large_deal: Optional[str] = Field(None, description="大额决策流程(月额50万円以上)")


class Organization(BaseModel):
    """组织结构"""
    structure_type: Literal["扁平", "层级", "矩阵", "不明"] = Field(
        default="不明", description="组织结构类型"
    )
    description: Optional[str] = Field(None, description="组织描述")
    decision_flow: Optional[DecisionFlow] = Field(None, description="决策流程")


class KeyPerson(BaseModel):
    """关键人物"""
    name: str = Field(..., description="姓名")
    title: Optional[str] = Field(None, description="职务")
    department: Optional[str] = Field(None, description="部门")
    background: Optional[str] = Field(None, description="经历概要")
    approach_hint: Optional[str] = Field(None, description="接触建议")
    linkedin_search_query: Optional[str] = Field(None, description="LinkedIn搜索词")
    confidence: Literal["high", "medium", "low"] = Field(
        default="low", description="信息可信度"
    )
    # 联系方式
    email: Optional[str] = Field(None, description="邮箱地址")
    phone: Optional[str] = Field(None, description="电话号码")
    # LinkedIn 扩展字段
    linkedin_url: Optional[str] = Field(None, description="LinkedIn 个人主页 URL")
    linkedin_summary: Optional[str] = Field(None, description="LinkedIn 个人简介")
    skills: Optional[list[str]] = Field(None, description="技能列表")
    source: Optional[Literal["search", "linkedin", "team_page", "manual"]] = Field(
        None, description="数据来源"
    )


class FirstContactScript(BaseModel):
    """首次接触话术"""
    subject_template: Optional[str] = Field(None, description="邮件主题模板")
    body_template: Optional[str] = Field(None, description="邮件正文模板")


class ApproachStrategy(BaseModel):
    """接触策略"""
    recommended_method: Optional[str] = Field(None, description="推荐接触方法")
    first_contact_script: Optional[FirstContactScript] = Field(None, description="首次接触话术")
    talking_points: list[str] = Field(default_factory=list, description="谈话要点")
    pitfalls_to_avoid: list[str] = Field(default_factory=list, description="应避免事项")


class Layer2Visibility(BaseModel):
    """第二层可见性配置"""
    public_fields: list[str] = Field(
        default=["summary", "timing", "organization.structure_type"],
        description="公开字段"
    )
    locked_fields: list[str] = Field(
        default=["key_persons", "approach_strategy", "organization.decision_flow"],
        description="付费解锁字段"
    )


class Layer2SalesApproach(BaseModel):
    """第二层: 销售接触指南"""
    summary: Optional[ApproachSummary] = Field(None, description="接触概要")
    timing: Optional[Timing] = Field(None, description="接触时机")
    organization: Optional[Organization] = Field(None, description="组织结构")
    key_persons: list[KeyPerson] = Field(default_factory=list, description="关键人物")
    approach_strategy: Optional[ApproachStrategy] = Field(None, description="接触策略")
    visibility: Layer2Visibility = Field(default_factory=Layer2Visibility)


# ============================================================
# Layer 3: 商机信号
# ============================================================

class OpportunityFactor(BaseModel):
    """商机评估因素"""
    factor: str = Field(..., description="因素名称")
    impact: Literal["positive", "negative"] = Field(..., description="影响方向")
    weight: float = Field(..., ge=0, le=1, description="权重")


class OpportunityScore(BaseModel):
    """商机评分"""
    value: int = Field(..., ge=0, le=100, description="商机分数(0-100)")
    label: Literal["低", "中", "高"] = Field(..., description="分数标签")
    factors: list[OpportunityFactor] = Field(default_factory=list, description="评估因素")


class NewsItem(BaseModel):
    """新闻条目"""
    date: Optional[str] = Field(None, description="日期(YYYY年M月)")
    type: Literal["融资", "业务合作", "人事变动", "新产品", "其他"] = Field(
        default="其他", description="新闻类型"
    )
    title: str = Field(..., description="标题")
    summary: Optional[str] = Field(None, description="摘要")
    implication: Optional[str] = Field(None, description="对销售的含义")
    source: Optional[str] = Field(None, description="来源")
    url: Optional[str] = Field(None, description="URL")


class FundingEvent(BaseModel):
    """融资事件"""
    round: Optional[str] = Field(None, description="轮次(Seed/Pre-A/Series A/B/C...)")
    date: Optional[str] = Field(None, description="日期")
    amount: Optional[str] = Field(None, description="金额")
    lead_investor: Optional[str] = Field(None, description="领投方")
    source: Optional[str] = Field(None, description="来源")


class HiringSignal(BaseModel):
    """招聘信号"""
    position_type: Literal["销售", "工程师", "营销", "其他"] = Field(
        default="其他", description="岗位类型"
    )
    description: Optional[str] = Field(None, description="描述")
    implication: Optional[str] = Field(None, description="含义")


class InvestmentInterest(BaseModel):
    """投资意向"""
    category: Literal["销售支持", "营销", "招聘", "基础设施", "其他"] = Field(
        ..., description="投资领域"
    )
    confidence: Literal["high", "medium", "low"] = Field(
        default="low", description="可信度"
    )
    reasoning: Optional[str] = Field(None, description="推断依据")


class Layer3Visibility(BaseModel):
    """第三层可见性配置"""
    public_fields: list[str] = Field(
        default=["opportunity_score.value", "recent_news", "hiring_signals"],
        description="公开字段"
    )
    locked_fields: list[str] = Field(
        default=["investment_interests", "opportunity_score.factors"],
        description="付费解锁字段"
    )


class Layer3Signals(BaseModel):
    """第三层: 商机信号"""
    opportunity_score: Optional[OpportunityScore] = Field(None, description="商机评分")
    recent_news: list[NewsItem] = Field(default_factory=list, description="近期新闻")
    funding_history: list[FundingEvent] = Field(default_factory=list, description="融资历史")
    hiring_signals: list[HiringSignal] = Field(default_factory=list, description="招聘信号")
    investment_interests: list[InvestmentInterest] = Field(
        default_factory=list, description="投资意向"
    )
    visibility: Layer3Visibility = Field(default_factory=Layer3Visibility)


# ============================================================
# 报告元数据
# ============================================================

class DataFreshness(BaseModel):
    """数据新鲜度"""
    basic_info: Optional[datetime] = Field(None)
    sales_approach: Optional[datetime] = Field(None)
    signals: Optional[datetime] = Field(None)


class ReportMeta(BaseModel):
    """报告元数据"""
    report_id: str = Field(..., description="报告ID")
    generated_at: datetime = Field(default_factory=datetime.now, description="生成时间")
    last_updated: datetime = Field(default_factory=datetime.now, description="最后更新")
    data_freshness: DataFreshness = Field(default_factory=DataFreshness)
    quality_score: int = Field(default=0, ge=0, le=100, description="质量分数(0-100)")


# ============================================================
# 完整报告
# ============================================================

class EnterpriseReport(BaseModel):
    """企业营业报告 - 完整结构"""
    meta: ReportMeta = Field(..., description="报告元数据")
    layer1_basic_info: Layer1BasicInfo = Field(..., description="第一层: 基本信息")
    layer2_sales_approach: Layer2SalesApproach = Field(
        default_factory=Layer2SalesApproach, description="第二层: 销售指南"
    )
    layer3_signals: Layer3Signals = Field(
        default_factory=Layer3Signals, description="第三层: 商机信号"
    )

    def to_json(self, indent: int = 2) -> str:
        """导出为JSON字符串"""
        return self.model_dump_json(indent=indent, exclude_none=True)

    def to_dict(self) -> dict:
        """导出为字典"""
        return self.model_dump(exclude_none=True)


# ============================================================
# 输入数据模型
# ============================================================

class SeedData(BaseModel):
    """种子数据 - 系统输入"""
    company_name: str = Field(..., description="企业名称")
    corporate_number: str = Field(..., min_length=13, max_length=13, description="法人番号")
    address: Optional[str] = Field(None, description="地址")
    website_url: str = Field(..., description="官网URL")


# ============================================================
# 收集器输出模型 (中间数据)
# ============================================================

class BasicInfoRaw(BaseModel):
    """基本信息收集器输出"""
    gbizinfo_data: Optional[dict] = Field(None, description="gBizINFO API 返回数据")
    website_content: Optional[str] = Field(None, description="官网爬取内容")
    company_page_url: Optional[str] = Field(None, description="公司简介页URL")
    errors: list[str] = Field(default_factory=list, description="收集过程中的错误")


class SalesIntelRaw(BaseModel):
    """销售情报收集器输出"""
    executives_search_results: list[dict] = Field(default_factory=list, description="高管搜索结果")
    organization_search_results: list[dict] = Field(default_factory=list, description="组织搜索结果")
    team_page_content: Optional[str] = Field(None, description="团队页面内容")
    linkedin_data: Optional[dict] = Field(None, description="LinkedIn 搜索数据")
    linkedin_profiles: Optional[dict] = Field(None, description="LinkedIn 深度采集数据 (Bright Data)")
    errors: list[str] = Field(default_factory=list, description="收集过程中的错误")


class SignalsRaw(BaseModel):
    """商机信号收集器输出"""
    news_search_results: list[dict] = Field(default_factory=list, description="新闻搜索结果")
    funding_search_results: list[dict] = Field(default_factory=list, description="融资搜索结果")
    pr_times_results: list[dict] = Field(default_factory=list, description="PR TIMES结果")
    hiring_search_results: list[dict] = Field(default_factory=list, description="招聘搜索结果")
    news_full_content: list[dict] = Field(
        default_factory=list,
        description="爬取的新闻全文内容 [{'url': str, 'title': str, 'content': str, 'crawled_at': str}]"
    )
    errors: list[str] = Field(default_factory=list, description="收集过程中的错误")


class SocialMediaRaw(BaseModel):
    """社交媒体数据收集器输出"""
    instagram: Optional[dict] = Field(None, description="Instagram 数据 (profile + recent posts)")
    facebook: Optional[dict] = Field(None, description="Facebook 数据 (page info + recent posts)")
    tiktok: Optional[dict] = Field(None, description="TikTok 数据 (profile + recent posts)")
    twitter: Optional[dict] = Field(None, description="X/Twitter 数据 (profile + recent posts)")
    youtube: Optional[dict] = Field(None, description="YouTube 数据 (channel + recent videos)")
    reddit: Optional[dict] = Field(None, description="Reddit 相关帖子")
    errors: list[str] = Field(default_factory=list, description="收集过程中的错误")


class CollectedData(BaseModel):
    """所有收集器的汇总输出"""
    seed: SeedData = Field(..., description="原始种子数据")
    basic_info: BasicInfoRaw = Field(default_factory=BasicInfoRaw)
    sales_intel: SalesIntelRaw = Field(default_factory=SalesIntelRaw)
    signals: SignalsRaw = Field(default_factory=SignalsRaw)
    social_media: Optional[SocialMediaRaw] = Field(None, description="社交媒体数据")
    collected_at: datetime = Field(default_factory=datetime.now)
