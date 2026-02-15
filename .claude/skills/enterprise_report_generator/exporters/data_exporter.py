"""
企业知识库导出器

将采集的原始数据按维度导出为 Markdown 文件，形成可被 agent 挖掘的企业知识库。

目录结构:
    output/{company_name}/
    ├── company/   公司信息
    ├── people/    人物档案
    ├── news/      新闻动态
    ├── signals/   商机信号
    ├── website/   官网内容
    └── report_*.md  AI 整合报告
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..models import CollectedData, EnterpriseReport, SeedData

logger = logging.getLogger(__name__)


class DataExporter:
    """企业知识库导出器"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def export(
        self,
        collected_data: CollectedData,
        report: EnterpriseReport,
        timestamp: Optional[datetime] = None,
    ) -> Path:
        """
        导出企业知识库

        Args:
            collected_data: 采集的原始数据
            report: AI 分析报告
            timestamp: 时间戳 (默认当前时间)

        Returns:
            企业目录路径
        """
        ts = timestamp or datetime.now()
        ts_hour = ts.strftime("%Y-%m-%d-%H")
        seed = collected_data.seed

        # 创建企业目录
        company_dir = self.output_dir / seed.company_name
        for subdir in ["company", "people", "news", "signals", "website", "social_media"]:
            (company_dir / subdir).mkdir(parents=True, exist_ok=True)

        # 导出各维度
        self._export_company(company_dir / "company", ts_hour, collected_data, report)
        self._export_people(company_dir / "people", ts_hour, collected_data, report)
        self._export_news(company_dir / "news", ts_hour, collected_data, report)
        self._export_signals(company_dir / "signals", ts_hour, collected_data, report)
        self._export_website(company_dir / "website", ts_hour, collected_data)
        self._export_social_media(company_dir / "social_media", ts_hour, collected_data)

        # 复制 AI 整合报告到企业目录
        from ..renderers import render_markdown
        report_content = render_markdown(report)
        report_path = company_dir / f"report_{ts_hour}.md"
        report_path.write_text(report_content, encoding="utf-8")

        logger.info(f"企业知识库已导出: {company_dir}")
        return company_dir

    # ================================================================
    # 公司信息
    # ================================================================

    def _export_company(
        self, dest: Path, ts: str,
        data: CollectedData, report: EnterpriseReport,
    ):
        """导出公司维度数据"""
        seed = data.seed
        l1 = report.layer1_basic_info
        l2 = report.layer2_sales_approach
        lines = []

        lines.append(f"# 公司信息: {seed.company_name}")
        lines.append(f"\n> 采集时间: {ts}")
        lines.append(f"> 数据来源: gBizINFO / 官网爬取 / Google搜索 / LinkedIn")
        lines.append("")

        # --- 基本信息 ---
        lines.append("## 基本信息")
        lines.append("")
        lines.append(f"- 企业名称: {l1.company_name}")
        if l1.company_name_kana:
            lines.append(f"- 読み仮名: {l1.company_name_kana}")
        lines.append(f"- 法人番号: {l1.corporate_number}")
        if l1.established:
            lines.append(f"- 设立日: {l1.established}")
        if l1.representative:
            lines.append(f"- 代表者: {l1.representative.name} ({l1.representative.title})")
        if l1.employee_count and l1.employee_count.value:
            emp_info = f"{l1.employee_count.value}名"
            if l1.employee_count.as_of:
                emp_info += f" ({l1.employee_count.as_of})"
            lines.append(f"- 従業員数: {emp_info}")
        if l1.address:
            lines.append(f"- 所在地: {l1.address.full}")
        if l1.website:
            lines.append(f"- 公式サイト: {l1.website}")
        lines.append("")

        # --- 事业概要 ---
        if l1.business_overview:
            lines.append("## 事业概要")
            lines.append("")
            lines.append(l1.business_overview)
            lines.append("")

        # --- 产品服务 ---
        if l1.main_products:
            lines.append("## 产品与服务")
            lines.append("")
            for p in l1.main_products:
                lines.append(f"### {p.name}")
                lines.append(f"- 类别: {p.category}")
                lines.append(f"- 目标市场: {p.target_market}")
                if p.description:
                    lines.append(f"- 描述: {p.description}")
                lines.append("")

        # --- 标签 ---
        tags = l1.tags
        all_tags = tags.scale + tags.industry + tags.characteristics
        if all_tags:
            lines.append("## 标签")
            lines.append("")
            lines.append(", ".join(all_tags))
            lines.append("")

        # --- 组织结构 (来自 AI 分析) ---
        if l2.organization:
            org = l2.organization
            lines.append("## 组织结构")
            lines.append("")
            lines.append(f"- 结构类型: {org.structure_type}")
            if org.description:
                lines.append(f"- 描述: {org.description}")
            if org.decision_flow:
                df = org.decision_flow
                lines.append("")
                lines.append("### 决策流程")
                if df.small_deal:
                    lines.append(f"- 小额 (月额10万円以下): {df.small_deal}")
                if df.medium_deal:
                    lines.append(f"- 中额 (月額10-50万円): {df.medium_deal}")
                if df.large_deal:
                    lines.append(f"- 大额 (月額50万円以上): {df.large_deal}")
            lines.append("")

        # --- LinkedIn 公司主页 (原始数据) ---
        if data.sales_intel and data.sales_intel.linkedin_profiles:
            lp = data.sales_intel.linkedin_profiles
            company_profile = lp.get("company_profile", {})
            if company_profile:
                lines.append("## LinkedIn 公司主页")
                lines.append("")
                if company_profile.get("description"):
                    lines.append(f"描述: {company_profile['description']}")
                    lines.append("")
                for key in ["industry", "company_size", "headquarters", "founded"]:
                    if company_profile.get(key):
                        lines.append(f"- {key}: {company_profile[key]}")
                if company_profile.get("url"):
                    lines.append(f"- URL: {company_profile['url']}")
                lines.append("")

        # --- gBizINFO 原始数据 ---
        if data.basic_info and data.basic_info.gbizinfo_data:
            gb = data.basic_info.gbizinfo_data
            lines.append("## gBizINFO 政府登记数据")
            lines.append("")
            for key, val in gb.items():
                if val and key not in ("corporateNumber", "name"):
                    lines.append(f"- {key}: {val}")
            lines.append("")

        filepath = dest / f"{ts}_公司信息.md"
        filepath.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"  公司信息: {filepath}")

    # ================================================================
    # 人物档案
    # ================================================================

    def _export_people(
        self, dest: Path, ts: str,
        data: CollectedData, report: EnterpriseReport,
    ):
        """导出人物维度数据"""
        seed = data.seed
        l2 = report.layer2_sales_approach
        lines = []

        lines.append(f"# 人物档案: {seed.company_name}")
        lines.append(f"\n> 采集时间: {ts}")
        lines.append(f"> 数据来源: LinkedIn (Bright Data) / Google搜索 / gBizINFO")
        lines.append("")

        # --- 从 AI 报告中的关键人物 ---
        if l2.key_persons:
            lines.append(f"## 关键人物 (共{len(l2.key_persons)}人)")
            lines.append("")

            for i, kp in enumerate(l2.key_persons, 1):
                lines.append(f"### {i}. {kp.name}")
                lines.append("")
                if kp.title:
                    lines.append(f"- 职位: {kp.title}")
                if kp.department:
                    lines.append(f"- 部门: {kp.department}")
                if kp.confidence:
                    lines.append(f"- 信息可信度: {kp.confidence}")
                if kp.source:
                    lines.append(f"- 数据来源: {kp.source}")
                if kp.email:
                    lines.append(f"- メール: {kp.email}")
                if kp.phone:
                    lines.append(f"- 電話: {kp.phone}")
                if kp.linkedin_url:
                    lines.append(f"- LinkedIn: {kp.linkedin_url}")
                if kp.linkedin_summary:
                    lines.append(f"- LinkedIn简介: {kp.linkedin_summary}")
                if kp.skills:
                    lines.append(f"- 技能: {', '.join(kp.skills)}")
                if kp.background:
                    lines.append(f"- 经历: {kp.background}")
                if kp.approach_hint:
                    lines.append(f"- 接触建议: {kp.approach_hint}")
                lines.append("")

        # --- LinkedIn 采集的全部员工原始数据 ---
        if data.sales_intel and data.sales_intel.linkedin_profiles:
            lp = data.sales_intel.linkedin_profiles
            all_employees = lp.get("all_employees", [])
            key_persons_raw = lp.get("key_persons", [])

            if all_employees:
                lines.append(f"## LinkedIn 员工列表 (原始数据, 共{len(all_employees)}人)")
                lines.append("")
                for emp in all_employees:
                    name = emp.get("title") or emp.get("name") or "不明"
                    subtitle = emp.get("subtitle") or ""
                    lines.append(f"- {name} | {subtitle}")
                    if emp.get("url"):
                        lines.append(f"  LinkedIn: {emp['url']}")
                lines.append("")

            if key_persons_raw:
                lines.append(f"## LinkedIn 关键人物详细资料 (共{len(key_persons_raw)}人)")
                lines.append("")
                for person in key_persons_raw:
                    name = person.get("name") or person.get("title") or "不明"
                    lines.append(f"### {name}")
                    lines.append("")

                    # 基本信息
                    for field in ["headline", "location", "about", "current_company_name"]:
                        if person.get(field):
                            lines.append(f"- {field}: {person[field]}")

                    # 经历
                    experience = person.get("experience", [])
                    if experience:
                        lines.append("")
                        lines.append("#### 职业经历")
                        for exp in experience:
                            if isinstance(exp, dict):
                                title = exp.get("title", "")
                                company = exp.get("company", "")
                                duration = exp.get("duration", "")
                                lines.append(f"- {title} @ {company} ({duration})")
                                if exp.get("description"):
                                    lines.append(f"  {exp['description']}")

                    # 教育
                    education = person.get("education", [])
                    if education:
                        lines.append("")
                        lines.append("#### 教育背景")
                        for edu in education:
                            if isinstance(edu, dict):
                                school = edu.get("school", "")
                                degree = edu.get("degree", "")
                                lines.append(f"- {school} - {degree}")

                    # 技能
                    skills = person.get("skills", [])
                    if skills:
                        lines.append("")
                        skill_names = []
                        for s in skills:
                            if isinstance(s, dict):
                                skill_names.append(s.get("name", str(s)))
                            else:
                                skill_names.append(str(s))
                        lines.append(f"技能: {', '.join(skill_names)}")

                    if person.get("url"):
                        lines.append(f"\nLinkedIn URL: {person['url']}")
                    lines.append("")

        # --- Google 搜索发现的高管信息 ---
        if data.sales_intel and data.sales_intel.executives_search_results:
            lines.append("## Google 搜索: 高管相关结果")
            lines.append("")
            for result in data.sales_intel.executives_search_results:
                title = result.get("title", "")
                snippet = result.get("snippet", "")
                link = result.get("link", "")
                lines.append(f"- **{title}**")
                if snippet:
                    lines.append(f"  {snippet}")
                if link:
                    lines.append(f"  URL: {link}")
                lines.append("")

        filepath = dest / f"{ts}_人物档案.md"
        filepath.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"  人物档案: {filepath}")

    # ================================================================
    # 新闻动态
    # ================================================================

    def _export_news(
        self, dest: Path, ts: str,
        data: CollectedData, report: EnterpriseReport,
    ):
        """导出新闻维度数据"""
        seed = data.seed
        l3 = report.layer3_signals
        lines = []

        lines.append(f"# 新闻动态: {seed.company_name}")
        lines.append(f"\n> 采集时间: {ts}")
        lines.append(f"> 数据来源: Google News / PR TIMES / 新闻全文爬取")
        lines.append("")

        # --- AI 分析后的新闻摘要 ---
        if l3.recent_news:
            lines.append(f"## AI 分析新闻摘要 (共{len(l3.recent_news)}条)")
            lines.append("")
            for news in l3.recent_news:
                date_str = news.date or "日期不明"
                lines.append(f"### [{date_str}] {news.title}")
                lines.append("")
                lines.append(f"- 类型: {news.type}")
                if news.source:
                    lines.append(f"- 来源: {news.source}")
                if news.url:
                    lines.append(f"- URL: {news.url}")
                if news.summary:
                    lines.append(f"- 摘要: {news.summary}")
                if news.implication:
                    lines.append(f"- 营业含义: {news.implication}")
                lines.append("")

        # --- 新闻搜索原始结果 ---
        if data.signals and data.signals.news_search_results:
            lines.append(f"## Google News 搜索结果 (原始, 共{len(data.signals.news_search_results)}条)")
            lines.append("")
            for item in data.signals.news_search_results:
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                link = item.get("link", "")
                date = item.get("date", "")
                source = item.get("source", "")
                lines.append(f"### {title}")
                if date:
                    lines.append(f"- 日期: {date}")
                if source:
                    lines.append(f"- 来源: {source}")
                if link:
                    lines.append(f"- URL: {link}")
                if snippet:
                    lines.append(f"- 摘要: {snippet}")
                lines.append("")

        # --- PR TIMES 结果 ---
        if data.signals and data.signals.pr_times_results:
            lines.append(f"## PR TIMES (共{len(data.signals.pr_times_results)}条)")
            lines.append("")
            for item in data.signals.pr_times_results:
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                link = item.get("link", "")
                lines.append(f"- **{title}**")
                if snippet:
                    lines.append(f"  {snippet}")
                if link:
                    lines.append(f"  URL: {link}")
                lines.append("")

        # --- 新闻全文内容 ---
        if data.signals and data.signals.news_full_content:
            lines.append(f"## 新闻全文 (共{len(data.signals.news_full_content)}篇)")
            lines.append("")
            for article in data.signals.news_full_content:
                title = article.get("title", "无标题")
                url = article.get("url", "")
                content = article.get("content", "")
                crawled_at = article.get("crawled_at", "")

                lines.append(f"### {title}")
                lines.append("")
                if url:
                    lines.append(f"URL: {url}")
                if crawled_at:
                    lines.append(f"爬取时间: {crawled_at}")
                lines.append("")
                if content:
                    # 保留全文，这是最有价值的原始数据
                    lines.append("```")
                    lines.append(content[:5000])  # 单篇最长5000字
                    if len(content) > 5000:
                        lines.append(f"\n... (全文 {len(content)} 字，已截断)")
                    lines.append("```")
                lines.append("")

        filepath = dest / f"{ts}_新闻动态.md"
        filepath.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"  新闻动态: {filepath}")

    # ================================================================
    # 商机信号
    # ================================================================

    def _export_signals(
        self, dest: Path, ts: str,
        data: CollectedData, report: EnterpriseReport,
    ):
        """导出商机信号维度数据"""
        seed = data.seed
        l3 = report.layer3_signals
        lines = []

        lines.append(f"# 商机信号: {seed.company_name}")
        lines.append(f"\n> 采集时间: {ts}")
        lines.append(f"> 数据来源: Google搜索 / INITIAL / 招聘网站 / AI分析")
        lines.append("")

        # --- 商机评分 ---
        if l3.opportunity_score:
            score = l3.opportunity_score
            lines.append("## 商机评分")
            lines.append("")
            lines.append(f"- 分数: {score.value}/100 ({score.label})")
            if score.factors:
                lines.append("")
                lines.append("### 评分因子")
                for f in score.factors:
                    direction = "正面" if f.impact == "positive" else "负面"
                    lines.append(f"- [{direction}, 权重{f.weight}] {f.factor}")
            lines.append("")

        # --- 融资历史 ---
        if l3.funding_history:
            lines.append("## 融资历史")
            lines.append("")
            for f in l3.funding_history:
                lines.append(f"- {f.date or '日期不明'}: {f.round or '轮次不明'}")
                if f.amount:
                    lines.append(f"  金额: {f.amount}")
                if f.lead_investor:
                    lines.append(f"  投资方: {f.lead_investor}")
                if f.source:
                    lines.append(f"  来源: {f.source}")
            lines.append("")

        # --- 融资搜索原始结果 ---
        if data.signals and data.signals.funding_search_results:
            lines.append(f"## 融资搜索结果 (原始, 共{len(data.signals.funding_search_results)}条)")
            lines.append("")
            for item in data.signals.funding_search_results:
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                link = item.get("link", "")
                lines.append(f"- **{title}**")
                if snippet:
                    lines.append(f"  {snippet}")
                if link:
                    lines.append(f"  URL: {link}")
                lines.append("")

        # --- 招聘信号 ---
        if l3.hiring_signals:
            lines.append("## 招聘信号")
            lines.append("")
            for h in l3.hiring_signals:
                lines.append(f"- 岗位类型: {h.position_type}")
                if h.description:
                    lines.append(f"  描述: {h.description}")
                if h.implication:
                    lines.append(f"  含义: {h.implication}")
                lines.append("")

        # --- 招聘搜索原始结果 ---
        if data.signals and data.signals.hiring_search_results:
            lines.append(f"## 招聘搜索结果 (原始, 共{len(data.signals.hiring_search_results)}条)")
            lines.append("")
            for item in data.signals.hiring_search_results:
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                link = item.get("link", "")
                lines.append(f"- **{title}**")
                if snippet:
                    lines.append(f"  {snippet}")
                if link:
                    lines.append(f"  URL: {link}")
                lines.append("")

        # --- 投资意向 ---
        if l3.investment_interests:
            lines.append("## 投资意向分析")
            lines.append("")
            for inv in l3.investment_interests:
                lines.append(f"### {inv.category}")
                lines.append(f"- 可信度: {inv.confidence}")
                if inv.reasoning:
                    lines.append(f"- 推断依据: {inv.reasoning}")
                lines.append("")

        # --- 销售评估 ---
        l2 = report.layer2_sales_approach
        if l2.summary:
            s = l2.summary
            lines.append("## 销售难度评估")
            lines.append("")
            lines.append(f"- 难度: {s.difficulty}/5 ({s.difficulty_label})")
            if s.recommended_channel:
                lines.append(f"- 推荐渠道: {s.recommended_channel}")
            if s.decision_speed:
                lines.append(f"- 决策速度: {s.decision_speed}")
            if s.overview:
                lines.append(f"- 概述: {s.overview}")
            lines.append("")

        if l2.timing:
            t = l2.timing
            lines.append("## 接触时机")
            lines.append("")
            status = "好时机" if t.is_good_timing else "非最佳时机"
            lines.append(f"- 当前状态: {status}")
            if t.reasons:
                for r in t.reasons:
                    lines.append(f"- 理由: {r}")
            if t.recommended_period:
                lines.append(f"- 推荐时期: {t.recommended_period}")
            lines.append("")

        filepath = dest / f"{ts}_商机信号.md"
        filepath.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"  商机信号: {filepath}")

    # ================================================================
    # 官网内容
    # ================================================================

    def _export_website(
        self, dest: Path, ts: str,
        data: CollectedData,
    ):
        """导出官网维度数据"""
        seed = data.seed
        lines = []

        lines.append(f"# 官网内容: {seed.company_name}")
        lines.append(f"\n> 采集时间: {ts}")
        lines.append(f"> URL: {seed.website_url}")
        lines.append("")

        # --- 爬取的官网内容 ---
        if data.basic_info and data.basic_info.website_content:
            lines.append("## 官网爬取内容")
            lines.append("")
            lines.append(data.basic_info.website_content)
            lines.append("")
        else:
            lines.append("## 官网爬取内容")
            lines.append("")
            lines.append("(未能获取官网内容)")
            lines.append("")

        # --- 组织搜索结果 (官网相关的搜索) ---
        if data.sales_intel and data.sales_intel.organization_search_results:
            lines.append(f"## 组织信息搜索结果 (共{len(data.sales_intel.organization_search_results)}条)")
            lines.append("")
            for item in data.sales_intel.organization_search_results:
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                link = item.get("link", "")
                lines.append(f"- **{title}**")
                if snippet:
                    lines.append(f"  {snippet}")
                if link:
                    lines.append(f"  URL: {link}")
                lines.append("")

        filepath = dest / f"{ts}_官网内容.md"
        filepath.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"  官网内容: {filepath}")

    # ================================================================
    # 社交媒体
    # ================================================================

    def _export_social_media(
        self, dest: Path, ts: str,
        data: CollectedData,
    ):
        """导出社交媒体维度数据"""
        seed = data.seed
        sm = data.social_media
        if not sm:
            return

        lines = []
        lines.append(f"# ソーシャルメディア概要: {seed.company_name}")
        lines.append(f"\n> 採集時間: {ts}")
        lines.append(f"> データソース: BrightData Social Media API")
        lines.append("")

        platform_names = {
            "instagram": "Instagram",
            "facebook": "Facebook",
            "tiktok": "TikTok",
            "twitter": "X/Twitter",
            "youtube": "YouTube",
            "reddit": "Reddit",
        }

        has_data = False
        for platform_key, platform_label in platform_names.items():
            platform_data = getattr(sm, platform_key, None)
            if not platform_data:
                continue

            has_data = True
            lines.append(f"## {platform_label}")
            lines.append("")

            # Profile
            profile = platform_data.get("profile")
            if profile:
                if profile.get("name"):
                    lines.append(f"- アカウント名: {profile['name']}")
                if profile.get("username"):
                    lines.append(f"- ユーザー名: @{profile['username']}")
                if profile.get("followers") is not None:
                    lines.append(f"- フォロワー数: {profile['followers']:,}")
                if profile.get("following") is not None:
                    lines.append(f"- フォロー数: {profile['following']:,}")
                if profile.get("posts_count") is not None:
                    lines.append(f"- 投稿数: {profile['posts_count']:,}")
                if profile.get("verified"):
                    lines.append(f"- 認証済み: はい")
                if profile.get("description"):
                    lines.append(f"- プロフィール: {profile['description'][:300]}")
                if profile.get("url"):
                    lines.append(f"- URL: {profile['url']}")
                lines.append("")

            # Posts
            posts = platform_data.get("posts", [])
            if posts:
                lines.append(f"### 最近の投稿 ({len(posts)}件)")
                lines.append("")
                for i, post in enumerate(posts, 1):
                    title = post.get("title") or (post.get("content", "")[:80] if post.get("content") else "(内容なし)")
                    date = post.get("date", "日付不明")
                    lines.append(f"#### {i}. {title}")
                    lines.append(f"- 日付: {date}")
                    if post.get("likes") is not None:
                        lines.append(f"- いいね: {post['likes']:,}")
                    if post.get("comments") is not None:
                        lines.append(f"- コメント: {post['comments']:,}")
                    if post.get("shares") is not None:
                        lines.append(f"- シェア: {post['shares']:,}")
                    if post.get("views") is not None:
                        lines.append(f"- 再生数: {post['views']:,}")
                    if post.get("url"):
                        lines.append(f"- URL: {post['url']}")
                    lines.append("")

        # エラー
        if sm.errors:
            lines.append("## 採集エラー")
            lines.append("")
            for err in sm.errors:
                lines.append(f"- {err}")
            lines.append("")

        if not has_data and not sm.errors:
            lines.append("(ソーシャルメディアアカウントが見つかりませんでした)")
            lines.append("")

        filepath = dest / f"{ts}_ソーシャルメディア.md"
        filepath.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"  ソーシャルメディア: {filepath}")
