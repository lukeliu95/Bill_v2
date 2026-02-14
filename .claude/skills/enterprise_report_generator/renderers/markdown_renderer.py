"""
企业营业报告 Markdown 渲染器

将 EnterpriseReport 模型转换为结构化 Markdown 文档
"""
from ..models import EnterpriseReport


def render_markdown(report: EnterpriseReport) -> str:
    """
    将报告渲染为 Markdown 格式

    Args:
        report: 企业报告模型

    Returns:
        Markdown 字符串
    """
    sections = [
        _render_header(report),
        _render_layer1(report),
        _render_layer2(report),
        _render_layer3(report),
        _render_footer(report),
    ]
    return "\n".join(sections)


# ============================================================
# Header
# ============================================================

def _render_header(report: EnterpriseReport) -> str:
    meta = report.meta
    l1 = report.layer1_basic_info
    generated = meta.generated_at.strftime("%Y-%m-%d %H:%M:%S")

    return f"""# 企業営業報告書: {l1.company_name}

> 生成日時: {generated}
> 品質スコア: {meta.quality_score}/100
> レポートID: {meta.report_id}

---
"""


# ============================================================
# Layer 1: 企業基本情報
# ============================================================

def _render_layer1(report: EnterpriseReport) -> str:
    l1 = report.layer1_basic_info
    lines = ["## 1. 企業基本情報", ""]

    # 基本情報テーブル
    rows = [
        ("企業名", l1.company_name),
        ("フリガナ", l1.company_name_kana),
        ("法人番号", l1.corporate_number),
        ("設立日", l1.established),
        ("代表者", f"{l1.representative.name} ({l1.representative.title})" if l1.representative else None),
        ("従業員数", f"{l1.employee_count.value}名" + (f" ({l1.employee_count.source})" if l1.employee_count.source else "") if l1.employee_count and l1.employee_count.value else None),
        ("所在地", l1.address.full if l1.address else None),
        ("公式サイト", l1.website),
    ]

    lines.append("| 項目 | 内容 |")
    lines.append("|------|------|")
    for label, value in rows:
        if value:
            lines.append(f"| {label} | {value} |")
    lines.append("")

    # 事業概要
    if l1.business_overview:
        lines.append("### 事業概要")
        lines.append("")
        lines.append(l1.business_overview)
        lines.append("")

    # 主要プロダクト
    if l1.main_products:
        lines.append("### 主要プロダクト")
        lines.append("")
        for p in l1.main_products:
            market = f" / {p.target_market}" if p.target_market else ""
            lines.append(f"- **{p.name}** ({p.category}{market})")
            if p.description:
                lines.append(f"  {p.description}")
        lines.append("")

    # タグ
    tags = l1.tags
    all_tags = tags.scale + tags.industry + tags.characteristics
    if all_tags:
        lines.append("### タグ")
        lines.append("")
        lines.append(" ".join(f"`{t}`" for t in all_tags))
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


# ============================================================
# Layer 2: 営業アプローチガイド
# ============================================================

def _render_layer2(report: EnterpriseReport) -> str:
    l2 = report.layer2_sales_approach
    lines = ["## 2. 営業アプローチガイド", ""]

    # 概要
    if l2.summary:
        s = l2.summary
        difficulty_bar = "●" * s.difficulty + "○" * (5 - s.difficulty)
        lines.append("### 概要")
        lines.append("")
        lines.append(f"- **営業難易度**: {difficulty_bar} ({s.difficulty}/5 — {s.difficulty_label})")
        if s.recommended_channel:
            lines.append(f"- **推奨チャネル**: {s.recommended_channel}")
        if s.decision_speed:
            lines.append(f"- **意思決定スピード**: {s.decision_speed}")
        lines.append("")
        if s.overview:
            lines.append(s.overview)
            lines.append("")

    # タイミング
    if l2.timing:
        t = l2.timing
        icon = "✅" if t.is_good_timing else "⚠️"
        lines.append(f"### アプローチタイミング {icon}")
        lines.append("")
        if t.is_good_timing:
            lines.append("**今がアプローチの好機です。**")
        else:
            lines.append("**現在はアプローチの適期ではありません。**")
        lines.append("")
        if t.reasons:
            for reason in t.reasons:
                lines.append(f"- {reason}")
            lines.append("")
        if t.recommended_period:
            lines.append(f"> 推奨時期: {t.recommended_period}")
            lines.append("")

    # 組織構造
    if l2.organization:
        org = l2.organization
        lines.append("### 組織構造")
        lines.append("")
        lines.append(f"**タイプ**: {org.structure_type}")
        lines.append("")
        if org.description:
            lines.append(org.description)
            lines.append("")

        if org.decision_flow:
            df = org.decision_flow
            lines.append("**意思決定フロー:**")
            lines.append("")
            if df.small_deal:
                lines.append(f"- 小規模案件（月額10万円以下）: {df.small_deal}")
            if df.medium_deal:
                lines.append(f"- 中規模案件（月額10-50万円）: {df.medium_deal}")
            if df.large_deal:
                lines.append(f"- 大規模案件（月額50万円以上）: {df.large_deal}")
            lines.append("")

    # キーパーソン
    if l2.key_persons:
        lines.append("### キーパーソン")
        lines.append("")
        for i, kp in enumerate(l2.key_persons, 1):
            title_str = f" — {kp.title}" if kp.title else ""
            lines.append(f"#### {i}. {kp.name}{title_str}")
            lines.append("")

            meta_parts = []
            if kp.department:
                meta_parts.append(f"部門: {kp.department}")
            if kp.confidence:
                conf_label = {"high": "高", "medium": "中", "low": "低"}.get(kp.confidence, kp.confidence)
                meta_parts.append(f"信頼度: {conf_label}")
            if kp.source:
                meta_parts.append(f"情報源: {kp.source}")
            if meta_parts:
                lines.append(f"*{' | '.join(meta_parts)}*")
                lines.append("")

            if kp.background:
                lines.append(f"**経歴**: {kp.background}")
                lines.append("")
            if kp.approach_hint:
                lines.append(f"**アプローチヒント**: {kp.approach_hint}")
                lines.append("")
            if kp.linkedin_url:
                lines.append(f"**LinkedIn**: {kp.linkedin_url}")
                lines.append("")
            if kp.skills:
                lines.append(f"**スキル**: {', '.join(kp.skills)}")
                lines.append("")

    # アプローチ戦略
    if l2.approach_strategy:
        strat = l2.approach_strategy
        lines.append("### アプローチ戦略")
        lines.append("")
        if strat.recommended_method:
            lines.append(f"**推奨方法**: {strat.recommended_method}")
            lines.append("")

        if strat.first_contact_script:
            fc = strat.first_contact_script
            lines.append("**初回コンタクトテンプレート:**")
            lines.append("")
            if fc.subject_template:
                lines.append(f"> 件名: {fc.subject_template}")
                lines.append("")
            if fc.body_template:
                lines.append("```")
                lines.append(fc.body_template)
                lines.append("```")
                lines.append("")

        if strat.talking_points:
            lines.append("**トークポイント:**")
            lines.append("")
            for tp in strat.talking_points:
                lines.append(f"- {tp}")
            lines.append("")

        if strat.pitfalls_to_avoid:
            lines.append("**注意事項（避けるべきこと）:**")
            lines.append("")
            for pit in strat.pitfalls_to_avoid:
                lines.append(f"- ⚠️ {pit}")
            lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


# ============================================================
# Layer 3: 商機シグナル
# ============================================================

def _render_layer3(report: EnterpriseReport) -> str:
    l3 = report.layer3_signals
    lines = ["## 3. 商機シグナル", ""]

    # 商機スコア
    if l3.opportunity_score:
        score = l3.opportunity_score
        bar_filled = score.value // 10
        bar_empty = 10 - bar_filled
        bar = "█" * bar_filled + "░" * bar_empty
        lines.append(f"### 商機スコア: {score.value}/100 ({score.label})")
        lines.append("")
        lines.append(f"`{bar}` {score.value}点")
        lines.append("")

        if score.factors:
            lines.append("**評価要因:**")
            lines.append("")
            lines.append("| 要因 | 影響 | 重み |")
            lines.append("|------|------|------|")
            for f in score.factors:
                impact_icon = "📈" if f.impact == "positive" else "📉"
                lines.append(f"| {f.factor} | {impact_icon} {f.impact} | {f.weight} |")
            lines.append("")

    # 最近のニュース
    if l3.recent_news:
        lines.append("### 最近のニュース")
        lines.append("")
        for news in l3.recent_news:
            type_icon = {
                "融资": "💰",
                "业务合作": "🤝",
                "人事变动": "👤",
                "新产品": "🚀",
                "其他": "📰",
            }.get(news.type, "📰")

            date_str = f" ({news.date})" if news.date else ""
            lines.append(f"#### {type_icon} {news.title}{date_str}")
            lines.append("")
            if news.summary:
                lines.append(f"{news.summary}")
                lines.append("")
            if news.implication:
                lines.append(f"> 💡 **営業への示唆**: {news.implication}")
                lines.append("")
            if news.url:
                lines.append(f"🔗 {news.url}")
                lines.append("")

    # 資金調達履歴
    if l3.funding_history:
        lines.append("### 資金調達履歴")
        lines.append("")
        lines.append("| ラウンド | 日付 | 金額 | リード投資家 | 情報源 |")
        lines.append("|----------|------|------|-------------|--------|")
        for f in l3.funding_history:
            lines.append(
                f"| {f.round or '-'} | {f.date or '-'} | {f.amount or '-'} "
                f"| {f.lead_investor or '-'} | {f.source or '-'} |"
            )
        lines.append("")

    # 採用シグナル
    if l3.hiring_signals:
        lines.append("### 採用シグナル")
        lines.append("")
        for h in l3.hiring_signals:
            type_label = {
                "销售": "営業",
                "工程师": "エンジニア",
                "营销": "マーケティング",
                "其他": "その他",
            }.get(h.position_type, h.position_type)
            lines.append(f"- **{type_label}**: {h.description or ''}")
            if h.implication:
                lines.append(f"  > {h.implication}")
        lines.append("")

    # 投資関心領域
    if l3.investment_interests:
        lines.append("### 投資関心領域")
        lines.append("")
        lines.append("| カテゴリ | 確信度 | 根拠 |")
        lines.append("|----------|--------|------|")
        for inv in l3.investment_interests:
            cat_label = {
                "销售支持": "営業支援",
                "营销": "マーケティング",
                "招聘": "採用",
                "基础设施": "インフラ",
                "其他": "その他",
            }.get(inv.category, inv.category)
            conf_label = {"high": "高", "medium": "中", "low": "低"}.get(inv.confidence, inv.confidence)
            lines.append(f"| {cat_label} | {conf_label} | {inv.reasoning or '-'} |")
        lines.append("")

    return "\n".join(lines)


# ============================================================
# Footer
# ============================================================

def _render_footer(report: EnterpriseReport) -> str:
    meta = report.meta
    freshness = meta.data_freshness
    lines = ["---", "", "## データ鮮度", ""]

    parts = []
    if freshness.basic_info:
        parts.append(f"- 基本情報: {freshness.basic_info.strftime('%Y-%m-%d %H:%M')}")
    if freshness.sales_approach:
        parts.append(f"- 営業アプローチ: {freshness.sales_approach.strftime('%Y-%m-%d %H:%M')}")
    if freshness.signals:
        parts.append(f"- 商機シグナル: {freshness.signals.strftime('%Y-%m-%d %H:%M')}")

    if parts:
        lines.extend(parts)
    else:
        lines.append("- データ鮮度情報なし")

    lines.append("")
    lines.append("---")
    lines.append(f"*本報告書は pSEOv1 企業営業報告自動生成システムにより自動生成されました。*")
    lines.append("")
    return "\n".join(lines)
