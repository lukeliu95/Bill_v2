"""
基本信息解析 Prompt

用于从收集的原始数据中提取结构化的企业基本信息
"""

from ..models.tag_vocabulary import get_tags_prompt_section

SYSTEM_INSTRUCTION = """你是一位精通日本B2B市场的商业分析师。你的任务是分析企业信息并生成结构化数据。

规则：
1. 只使用提供的数据，不要编造信息
2. 如果某个字段无法从数据中确定，设为 null
3. 标签必须从预定义词库中选择
4. 业务概要控制在100-300字
5. 输出必须是有效的JSON格式
"""


def build_basic_info_prompt(
    seed_data: dict,
    gbizinfo_data: dict | None,
    website_content: str | None,
) -> str:
    """
    构建基本信息解析的Prompt

    Args:
        seed_data: 种子数据
        gbizinfo_data: gBizINFO API 返回数据
        website_content: 官网爬取内容

    Returns:
        完整的Prompt字符串
    """
    prompt = f"""
## 任务
分析以下企业信息，生成结构化的基本信息JSON。

## 输入数据

### 种子数据
- 企业名: {seed_data.get('company_name', '不明')}
- 法人番号: {seed_data.get('corporate_number', '不明')}
- 官网URL: {seed_data.get('website_url', '不明')}

### gBizINFO 数据
{_format_gbizinfo(gbizinfo_data)}

### 官网内容
{_format_website_content(website_content)}

{get_tags_prompt_section()}

## 输出格式

请返回以下JSON结构：

```json
{{
  "company_name": "正式企业名称",
  "company_name_kana": "假名读音（如有）",
  "established": "YYYY年M月 格式的成立日期",
  "representative": {{
    "name": "代表人姓名",
    "title": "职务名称"
  }},
  "employee_count": {{
    "value": 数字,
    "as_of": "数据时点说明",
    "source": "数据来源"
  }},
  "capital": {{
    "value": 数字（日元）,
    "display": "显示格式（如：9,000万円）"
  }},
  "address": {{
    "full": "完整地址",
    "prefecture": "都道府县",
    "city": "市区町村"
  }},
  "business_overview": "100-300字的业务概要描述",
  "main_products": [
    {{
      "name": "产品名称",
      "category": "SaaS/Hardware/Service/Other",
      "description": "产品描述",
      "target_market": "B2B/B2C/Both"
    }}
  ],
  "tags": {{
    "scale": ["从规模标签中选择，最多3个"],
    "industry": ["从行业标签中选择，最多3个"],
    "characteristics": ["从特征标签中选择，最多3个"]
  }}
}}
```

请直接返回JSON，不要包含markdown代码块标记。
"""
    return prompt


def _format_gbizinfo(data: dict | None) -> str:
    """格式化 gBizINFO 数据"""
    if not data:
        return "（无数据）"

    lines = []
    field_names = {
        "name": "企业名",
        "kana": "假名",
        "location": "所在地",
        "representative_name": "代表人",
        "representative_position": "代表人职务",
        "capital_stock": "资本金",
        "employee_number": "员工数",
        "founding_year": "创业年",
        "date_of_establishment": "成立日",
        "business_summary": "业务概要",
        "company_url": "官网",
        "status": "状态",
    }

    for key, label in field_names.items():
        value = data.get(key)
        if value:
            lines.append(f"- {label}: {value}")

    return "\n".join(lines) if lines else "（无数据）"


def _format_website_content(content: str | None) -> str:
    """格式化官网内容"""
    if not content:
        return "（无数据）"

    # 限制长度，避免token过多
    max_length = 8000
    if len(content) > max_length:
        content = content[:max_length] + "\n\n... (内容已截断)"

    return content
