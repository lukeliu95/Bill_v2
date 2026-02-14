"""
销售路径分析 Prompt

用于生成销售接触策略和关键人物分析
"""

SYSTEM_INSTRUCTION = """你是一位拥有10年以上经验的B2B销售顾问。请以指导新销售人员的立场进行回答。

规则：
1. 基于推测的信息必须明确标注为"推测"
2. 不包含个人的私人联系方式（个人邮箱、手机号码）
3. LinkedIn 数据处理规则:
   - 如果有 LinkedIn 深度采集数据（关键人物详细资料），优先使用
   - 直接使用采集到的 linkedin_url，设置 source="linkedin"，confidence="high"
   - 从 LinkedIn summary 和 experience 提取 background
   - 从 LinkedIn skills 提取技能列表
   - 无深度数据时，提供 linkedin_search_query 供手动搜索
4. 关键人物信息的 confidence 字段要诚实评估：
   - high: 有 LinkedIn 深度采集数据或明确的公开信息支持
   - medium: 从上下文可以合理推断
   - low: 主要基于推测
5. source 字段标注数据来源:
   - linkedin: 来自 LinkedIn 深度采集
   - search: 来自搜索引擎结果
   - team_page: 来自公司团队页面
   - manual: 需要手动验证
6. 输出必须是有效的JSON格式
"""


def build_sales_approach_prompt(
    basic_info: dict,
    sales_intel_raw: dict,
) -> str:
    """
    构建销售路径分析的Prompt

    Args:
        basic_info: 第一层基本信息
        sales_intel_raw: 销售情报收集器的原始输出

    Returns:
        完整的Prompt字符串
    """
    prompt = f"""
## 任务
根据收集到的信息，制定针对该企业的销售接触策略。

## 企业基本信息
{_format_basic_info(basic_info)}

## 收集到的销售情报

### 高管搜索结果
{_format_search_results(sales_intel_raw.get('executives_search_results', []))}

### 组织结构搜索结果
{_format_search_results(sales_intel_raw.get('organization_search_results', []))}

### LinkedIn 数据
{_format_linkedin_data(sales_intel_raw.get('linkedin_profiles') or sales_intel_raw.get('linkedin_data', {}))}

### 团队页面内容
{_format_team_content(sales_intel_raw.get('team_page_content'))}

## 分析要求

请完成以下分析：

1. **销售难度评估** (1-5分)
   - 1分: 非常容易接触
   - 3分: 中等难度
   - 5分: 非常困难
   - 说明评估理由

2. **组织结构判定**
   - 类型: 扁平/层级/矩阵/不明
   - 不同金额的决策流程推测

3. **关键人物识别** (最多3名)
   - 职务、部门、经历背景
   - 接触建议
   - LinkedIn 信息（如有深度采集数据则直接使用）
   - 信息可信度 (high/medium/low)
   - 数据来源标注

4. **接触策略建议**
   - 推荐的接触方法
   - 首次联系邮件模板
   - 谈话要点
   - 应避免的事项

5. **时机判定**
   - 现在是否是好的接触时机
   - 理由说明

## 输出格式

```json
{{
  "summary": {{
    "difficulty": 数字1-5,
    "difficulty_label": "低/中/高",
    "recommended_channel": "推荐的接触渠道",
    "decision_speed": "决策速度描述",
    "overview": "100-200字的接触概述"
  }},
  "timing": {{
    "is_good_timing": true/false,
    "reasons": ["理由1", "理由2"],
    "recommended_period": "推荐接触时期（可选）"
  }},
  "organization": {{
    "structure_type": "扁平/层级/矩阵/不明",
    "description": "组织结构描述",
    "decision_flow": {{
      "small_deal": "月额10万円以下的决策流程",
      "medium_deal": "月额10-50万円的决策流程",
      "large_deal": "月额50万円以上的决策流程"
    }}
  }},
  "key_persons": [
    {{
      "name": "姓名",
      "title": "职务",
      "department": "部门",
      "background": "经历概要",
      "approach_hint": "接触建议",
      "linkedin_search_query": "LinkedIn搜索词（无URL时使用）",
      "confidence": "high/medium/low",
      "linkedin_url": "LinkedIn个人主页URL（从深度采集数据获取，无则null）",
      "linkedin_summary": "LinkedIn简介摘要（从深度采集数据提取，无则null）",
      "skills": ["技能1", "技能2"],
      "source": "linkedin/search/team_page/manual"
    }}
  ],
  "approach_strategy": {{
    "recommended_method": "推荐接触方法",
    "first_contact_script": {{
      "subject_template": "邮件主题模板",
      "body_template": "邮件正文模板（含{{company_name}}等占位符）"
    }},
    "talking_points": ["要点1", "要点2", "要点3"],
    "pitfalls_to_avoid": ["避免事项1", "避免事项2"]
  }}
}}
```

请直接返回JSON，不要包含markdown代码块标记。
"""
    return prompt


def _format_basic_info(info: dict) -> str:
    """格式化基本信息"""
    lines = []

    if info.get("company_name"):
        lines.append(f"- 企业名: {info['company_name']}")
    if info.get("business_overview"):
        lines.append(f"- 业务概要: {info['business_overview']}")
    if info.get("employee_count"):
        ec = info["employee_count"]
        if isinstance(ec, dict) and ec.get("value"):
            lines.append(f"- 员工数: {ec['value']}人")
    if info.get("tags"):
        tags = info["tags"]
        all_tags = tags.get("scale", []) + tags.get("industry", []) + tags.get("characteristics", [])
        if all_tags:
            lines.append(f"- 标签: {', '.join(all_tags)}")
    if info.get("main_products"):
        products = [p.get("name", "") for p in info["main_products"] if p.get("name")]
        if products:
            lines.append(f"- 主要产品: {', '.join(products)}")

    return "\n".join(lines) if lines else "（基本信息不足）"


def _format_search_results(results: list) -> str:
    """格式化搜索结果"""
    if not results:
        return "（无搜索结果）"

    lines = []
    for i, item in enumerate(results[:10], 1):
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        lines.append(f"{i}. {title}")
        if snippet:
            lines.append(f"   {snippet[:200]}")
        lines.append("")

    return "\n".join(lines)


def _format_linkedin_data(data: dict) -> str:
    """格式化 LinkedIn 数据（支持深度采集）"""
    if not data:
        return "（无LinkedIn数据）"

    lines = []

    # 处理 LinkedIn 深度采集数据 (linkedin_profiles)
    if data.get("company_profile") or data.get("key_persons"):
        # 公司 LinkedIn 资料
        company = data.get("company_profile", {})
        if company:
            lines.append("#### 公司 LinkedIn 资料")
            if company.get("name"):
                lines.append(f"- 公司名: {company['name']}")
            if company.get("industry"):
                lines.append(f"- 行业: {company['industry']}")
            if company.get("company_size"):
                lines.append(f"- 规模: {company['company_size']}")
            if company.get("description"):
                desc = company["description"][:300]
                lines.append(f"- 描述: {desc}...")
            lines.append("")

        # 关键人物 LinkedIn 详细资料
        key_persons = data.get("key_persons", [])
        if key_persons:
            lines.append("#### 关键人物 LinkedIn 详细资料")
            for i, person in enumerate(key_persons[:5], 1):
                lines.append(f"\n**{i}. {person.get('name', 'Unknown')}**")
                if person.get("title"):
                    lines.append(f"- 职位: {person['title']}")
                if person.get("company"):
                    lines.append(f"- 公司: {person['company']}")
                if person.get("location"):
                    lines.append(f"- 地点: {person['location']}")
                if person.get("summary"):
                    summary = person["summary"][:200]
                    lines.append(f"- 简介: {summary}...")
                if person.get("skills"):
                    skills = ", ".join(person["skills"][:5])
                    lines.append(f"- 技能: {skills}")
                if person.get("experience"):
                    lines.append("- 经历:")
                    for exp in person["experience"][:2]:
                        if isinstance(exp, dict):
                            exp_title = exp.get("title", "")
                            exp_company = exp.get("company", "")
                            lines.append(f"  - {exp_title} @ {exp_company}")
                        elif isinstance(exp, str):
                            lines.append(f"  - {exp[:100]}")
                if person.get("linkedin_url"):
                    lines.append(f"- LinkedIn: {person['linkedin_url']}")

        if lines:
            return "\n".join(lines)

    # 兜底: 处理旧格式的 LinkedIn 搜索数据
    results = data.get("results", [])
    if not results:
        return "（无LinkedIn搜索结果）"

    for item in results[:5]:
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        lines.append(f"- {title}")
        if snippet:
            lines.append(f"  {snippet[:150]}")

    return "\n".join(lines)


def _format_team_content(content: str | None) -> str:
    """格式化团队页面内容"""
    if not content:
        return "（无团队页面数据）"

    # 限制长度
    max_length = 5000
    if len(content) > max_length:
        content = content[:max_length] + "\n\n... (内容已截断)"

    return content
