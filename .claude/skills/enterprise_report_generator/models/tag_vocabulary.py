"""
企业营业报告 - 标签词库定义

AI从词库中选择标签，不自由生成
"""
from typing import Literal

# ============================================================
# 规模标签 (Scale Tags)
# ============================================================

SCALE_TAGS = [
    "#个人事业",
    "#10人以下",
    "#10-50人规模",
    "#50-100人规模",
    "#100-500人规模",
    "#500-1000人规模",
    "#1000人以上",
    "#种子轮",
    "#已完成Pre-A轮",
    "#A轮",
    "#B轮及以后",
    "#上市公司",
]

ScaleTag = Literal[
    "#个人事业",
    "#10人以下",
    "#10-50人规模",
    "#50-100人规模",
    "#100-500人规模",
    "#500-1000人规模",
    "#1000人以上",
    "#种子轮",
    "#已完成Pre-A轮",
    "#A轮",
    "#B轮及以后",
    "#上市公司",
]


# ============================================================
# 行业标签 (Industry Tags)
# ============================================================

INDUSTRY_TAGS = [
    "#SaaS",
    "#生成式AI",
    "#HR-Tech",
    "#FinTech",
    "#MarTech",
    "#EC",
    "#制造业",
    "#咨询",
    "#广告代理",
    "#人才介绍",
    "#房地产",
    "#医疗/保健",
    "#教育/EdTech",
    "#物流",
    "#零售",
]

IndustryTag = Literal[
    "#SaaS",
    "#生成式AI",
    "#HR-Tech",
    "#FinTech",
    "#MarTech",
    "#EC",
    "#制造业",
    "#咨询",
    "#广告代理",
    "#人才介绍",
    "#房地产",
    "#医疗/保健",
    "#教育/EdTech",
    "#物流",
    "#零售",
]


# ============================================================
# 特征标签 (Characteristics Tags)
# ============================================================

CHARACTERISTICS_TAGS = [
    "#急剧增长中",
    "#稳定增长",
    "#技术导向",
    "#销售导向",
    "#全球化展开",
    "#国内特化",
    "#初创企业",
    "#老牌企业",
    "#外资系",
    "#大企业子公司",
    "#IPO准备中",
    "#M&A积极",
]

CharacteristicsTag = Literal[
    "#急剧增长中",
    "#稳定增长",
    "#技术导向",
    "#销售导向",
    "#全球化展开",
    "#国内特化",
    "#初创企业",
    "#老牌企业",
    "#外资系",
    "#大企业子公司",
    "#IPO准备中",
    "#M&A积极",
]


# ============================================================
# 辅助函数
# ============================================================

def get_all_tags() -> dict[str, list[str]]:
    """获取所有标签词库"""
    return {
        "scale": SCALE_TAGS,
        "industry": INDUSTRY_TAGS,
        "characteristics": CHARACTERISTICS_TAGS,
    }


def validate_tags(
    scale: list[str],
    industry: list[str],
    characteristics: list[str]
) -> tuple[list[str], list[str]]:
    """
    验证标签是否在词库中

    Returns:
        (valid_tags, invalid_tags)
    """
    valid = []
    invalid = []

    for tag in scale:
        if tag in SCALE_TAGS:
            valid.append(tag)
        else:
            invalid.append(tag)

    for tag in industry:
        if tag in INDUSTRY_TAGS:
            valid.append(tag)
        else:
            invalid.append(tag)

    for tag in characteristics:
        if tag in CHARACTERISTICS_TAGS:
            valid.append(tag)
        else:
            invalid.append(tag)

    return valid, invalid


def get_scale_tag_by_employee_count(count: int | None) -> str | None:
    """根据员工数自动选择规模标签"""
    if count is None:
        return None

    if count == 1:
        return "#个人事业"
    elif count < 10:
        return "#10人以下"
    elif count < 50:
        return "#10-50人规模"
    elif count < 100:
        return "#50-100人规模"
    elif count < 500:
        return "#100-500人规模"
    elif count < 1000:
        return "#500-1000人规模"
    else:
        return "#1000人以上"


def get_tags_prompt_section() -> str:
    """生成用于AI Prompt的标签词库说明"""
    return f"""
## 标签词库

从以下预定义标签中选择，每个类别最多3个标签。不要创建新标签。

### 规模标签 (scale)
{', '.join(SCALE_TAGS)}

### 行业标签 (industry)
{', '.join(INDUSTRY_TAGS)}

### 特征标签 (characteristics)
{', '.join(CHARACTERISTICS_TAGS)}
"""


# ============================================================
# 新闻类型
# ============================================================

NEWS_TYPES = [
    "融资",
    "业务合作",
    "人事变动",
    "新产品",
    "其他",
]

NewsType = Literal["融资", "业务合作", "人事变动", "新产品", "其他"]


# ============================================================
# 投资意向类别
# ============================================================

INVESTMENT_CATEGORIES = [
    "销售支持",
    "营销",
    "招聘",
    "基础设施",
    "其他",
]

InvestmentCategory = Literal["销售支持", "营销", "招聘", "基础设施", "其他"]


# ============================================================
# 招聘岗位类型
# ============================================================

POSITION_TYPES = [
    "销售",
    "工程师",
    "营销",
    "其他",
]

PositionType = Literal["销售", "工程师", "营销", "其他"]


if __name__ == "__main__":
    # 测试
    print("=== 标签词库 ===")
    for category, tags in get_all_tags().items():
        print(f"\n{category}: {len(tags)} 个标签")
        for tag in tags:
            print(f"  {tag}")

    print("\n=== 员工数标签测试 ===")
    for count in [1, 5, 30, 80, 200, 800, 2000]:
        tag = get_scale_tag_by_employee_count(count)
        print(f"  {count}人 → {tag}")
