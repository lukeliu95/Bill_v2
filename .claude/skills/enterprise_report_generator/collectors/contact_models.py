"""
联系方式发现 - 数据模型

ContactDiscoveryCollector 的输入输出模型
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field


class DiscoveredContact(BaseModel):
    """发现的联系人"""
    name: str = Field(..., description="姓名")
    title: Optional[str] = Field(None, description="职位")
    department: Optional[str] = Field(None, description="部门")
    email: Optional[str] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, description="电话")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn URL")
    twitter_url: Optional[str] = Field(None, description="X/Twitter URL")
    source: str = Field(..., description="数据来源 (linkedin/wantedly/prtimes/website/search)")
    confidence: Literal["high", "medium", "low"] = Field(default="low", description="可信度")
    notes: Optional[str] = Field(None, description="备注")


class CompanyContactInfo(BaseModel):
    """企业联系信息"""
    main_phone: Optional[str] = Field(None, description="代表電話")
    main_email: Optional[str] = Field(None, description="代表メール")
    contact_form_url: Optional[str] = Field(None, description="問い合わせフォームURL")
    ir_email: Optional[str] = Field(None, description="IR メール")
    pr_email: Optional[str] = Field(None, description="広報メール")
    recruit_email: Optional[str] = Field(None, description="採用メール")
    address: Optional[str] = Field(None, description="所在地")


class ContactRoute(BaseModel):
    """推奨接触路線"""
    rank: int = Field(..., description="优先顺位 (1=最推荐)")
    route_type: str = Field(..., description="路線タイプ (経営層直接/現場キーマン/HR経由/SNS/フォーム)")
    target_person: Optional[str] = Field(None, description="目标联系人")
    channel: str = Field(..., description="接触渠道 (メール/LinkedIn/電話/フォーム/SNS)")
    detail: str = Field(..., description="具体操作说明")
    success_probability: Literal["high", "medium", "low"] = Field(
        default="medium", description="成功率预估"
    )


class ContactDiscoveryRaw(BaseModel):
    """联系方式发现收集器输出 (原始数据)"""
    key_persons: list[DiscoveredContact] = Field(default_factory=list, description="发现的关键联系人")
    company_contacts: CompanyContactInfo = Field(default_factory=CompanyContactInfo, description="企业联系信息")
    recommended_routes: list[ContactRoute] = Field(default_factory=list, description="推奨接触路線")
    wantedly_results: list[dict] = Field(default_factory=list, description="Wantedly 搜索结果")
    prtimes_results: list[dict] = Field(default_factory=list, description="PR TIMES PR联系人结果")
    website_contact_content: Optional[str] = Field(None, description="官网联系页面内容")
    sources_used: list[str] = Field(default_factory=list, description="使用的数据源")
    errors: list[str] = Field(default_factory=list, description="收集过程中的错误")
