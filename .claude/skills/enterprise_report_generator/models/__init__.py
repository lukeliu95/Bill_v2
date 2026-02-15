"""
数据模型
"""
from .report_schema import (
    # 输入
    SeedData,
    # 中间数据
    BasicInfoRaw,
    SalesIntelRaw,
    SignalsRaw,
    SocialMediaRaw,
    CollectedData,
    # 报告结构
    EnterpriseReport,
    ReportMeta,
    DataFreshness,
    Layer1BasicInfo,
    Layer2SalesApproach,
    Layer3Signals,
    # 子结构
    Representative,
    EmployeeCount,
    Capital,
    Address,
    Product,
    Tags,
    KeyPerson,
    NewsItem,
    FundingEvent,
    HiringSignal,
    OpportunityScore,
    OpportunityFactor,
    InvestmentInterest,
    DataSource,
    # Layer2 子结构
    ApproachSummary,
    Timing,
    Organization,
    DecisionFlow,
    ApproachStrategy,
    FirstContactScript,
)
from .tag_vocabulary import (
    SCALE_TAGS,
    INDUSTRY_TAGS,
    CHARACTERISTICS_TAGS,
    get_all_tags,
    validate_tags,
    get_scale_tag_by_employee_count,
    get_tags_prompt_section,
)

__all__ = [
    # 输入
    "SeedData",
    # 中间数据
    "BasicInfoRaw",
    "SalesIntelRaw",
    "SignalsRaw",
    "SocialMediaRaw",
    "CollectedData",
    # 报告结构
    "EnterpriseReport",
    "ReportMeta",
    "DataFreshness",
    "Layer1BasicInfo",
    "Layer2SalesApproach",
    "Layer3Signals",
    # 子结构
    "Representative",
    "EmployeeCount",
    "Capital",
    "Address",
    "Product",
    "Tags",
    "KeyPerson",
    "NewsItem",
    "FundingEvent",
    "HiringSignal",
    "OpportunityScore",
    "OpportunityFactor",
    "InvestmentInterest",
    "DataSource",
    # Layer2 子结构
    "ApproachSummary",
    "Timing",
    "Organization",
    "DecisionFlow",
    "ApproachStrategy",
    "FirstContactScript",
    # 标签
    "SCALE_TAGS",
    "INDUSTRY_TAGS",
    "CHARACTERISTICS_TAGS",
    "get_all_tags",
    "validate_tags",
    "get_scale_tag_by_employee_count",
    "get_tags_prompt_section",
]
