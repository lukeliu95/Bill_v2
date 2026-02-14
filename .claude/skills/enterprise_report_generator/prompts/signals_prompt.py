"""
商机信号分析 Prompt

用于分析企业动态和评估商机
"""

SYSTEM_INSTRUCTION = """你是一位B2B销售情报专家。你的任务是分析企业的近期动态，评估销售商机。

规则：
1. 对每条新闻进行分类（融资/业务合作/人事变动/新产品/其他）
2. 用1-2句话说明每条新闻"对销售人员的意义"
3. 商机分数要基于具体因素，不要随意打分
4. 投资意向推测要有合理依据
5. 输出必须是有效的JSON格式
"""


def build_signals_prompt(
    basic_info: dict,
    signals_raw: dict,
) -> str:
    """
    构建商机信号分析的Prompt

    Args:
        basic_info: 第一层基本信息
        signals_raw: 商机信号收集器的原始输出

    Returns:
        完整的Prompt字符串
    """
    prompt = f"""
## 任务
分析收集到的新闻和招聘信息，评估商机信号。

## 企业基本信息
- 企业名: {basic_info.get('company_name', '不明')}
- 业务: {basic_info.get('business_overview', '不明')[:200] if basic_info.get('business_overview') else '不明'}

## 收集到的商机信息

### 新闻搜索结果
{_format_news_results(signals_raw.get('news_search_results', []))}

### 融资相关搜索结果
{_format_news_results(signals_raw.get('funding_search_results', []))}

### PR TIMES 新闻稿
{_format_news_results(signals_raw.get('pr_times_results', []))}

### 招聘信息搜索结果
{_format_hiring_results(signals_raw.get('hiring_search_results', []))}

{_format_full_articles_section(signals_raw.get('news_full_content', []))}

## 分析要求

1. **新闻分类与解读**
   - 对每条相关新闻分类
   - 说明对销售的意义

2. **融资历史整理**
   - 如果有融资信息，整理成结构化数据

3. **招聘信号分析**
   - 分析招聘岗位类型
   - 推测业务扩展方向

4. **商机评分** (0-100)
   评分因素权重参考：
   - 近期融资完成: +20~30分
   - 积极招聘: +10~20分
   - 新产品/服务发布: +10~15分
   - 业务合作发布: +5~10分
   - 负面新闻: -10~20分
   - 无近期动态: -5~10分

5. **投资意向推测** (最多4个领域)
   - 销售支持 / 营销 / 招聘 / 基础设施 / 其他
   - 说明推测依据

## 输出格式

```json
{{
  "opportunity_score": {{
    "value": 数字0-100,
    "label": "低/中/高",
    "factors": [
      {{
        "factor": "因素说明",
        "impact": "positive/negative",
        "weight": 权重数字0-1
      }}
    ]
  }},
  "recent_news": [
    {{
      "date": "YYYY年M月（如能确定）",
      "type": "融资/业务合作/人事变动/新产品/其他",
      "title": "新闻标题",
      "summary": "新闻摘要",
      "implication": "对销售的意义",
      "source": "来源",
      "url": "URL"
    }}
  ],
  "funding_history": [
    {{
      "round": "轮次（Seed/Pre-A/Series A/B/C...）",
      "date": "日期",
      "amount": "金额",
      "lead_investor": "领投方",
      "source": "来源"
    }}
  ],
  "hiring_signals": [
    {{
      "position_type": "销售/工程师/营销/其他",
      "description": "招聘描述",
      "implication": "对销售的含义"
    }}
  ],
  "investment_interests": [
    {{
      "category": "销售支持/营销/招聘/基础设施/其他",
      "confidence": "high/medium/low",
      "reasoning": "推测依据"
    }}
  ]
}}
```

注意：
- 如果没有找到相关新闻，recent_news 返回空数组
- 如果没有融资信息，funding_history 返回空数组
- opportunity_score 的 label 规则：0-39为"低"，40-69为"中"，70-100为"高"

请直接返回JSON，不要包含markdown代码块标记。
"""
    return prompt


def _format_news_results(results: list) -> str:
    """格式化新闻搜索结果"""
    if not results:
        return "（无结果）"

    lines = []
    for i, item in enumerate(results[:15], 1):
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        link = item.get("link", "")
        source = item.get("source", "")

        lines.append(f"{i}. {title}")
        if snippet:
            lines.append(f"   {snippet[:200]}")
        if link:
            lines.append(f"   URL: {link}")
        if source:
            lines.append(f"   来源: {source}")
        lines.append("")

    return "\n".join(lines)


def _format_full_articles_section(articles: list) -> str:
    """格式化新闻全文内容段落（仅在有内容时显示）"""
    if not articles:
        return ""

    lines = ["### 新闻全文内容（已爬取）"]
    for i, article in enumerate(articles, 1):
        title = article.get("title", "无标题")
        url = article.get("url", "")
        content = article.get("content", "")
        # 截断过长内容
        if len(content) > 3000:
            content = content[:3000] + "\n... (内容已截断)"

        lines.append(f"\n**{i}. {title}**")
        if url:
            lines.append(f"URL: {url}")
        lines.append(f"\n{content}")

    lines.append("\n注意：上面的新闻全文比搜索摘要更准确，请优先参考全文内容进行分析。")
    return "\n".join(lines)


def _format_hiring_results(results: list) -> str:
    """格式化招聘搜索结果"""
    if not results:
        return "（无招聘信息）"

    lines = []
    for i, item in enumerate(results[:10], 1):
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        source = item.get("source", "other")

        lines.append(f"{i}. [{source}] {title}")
        if snippet:
            lines.append(f"   {snippet[:150]}")
        lines.append("")

    return "\n".join(lines)
