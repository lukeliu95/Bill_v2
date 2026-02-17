#!/usr/bin/env python3
"""
企业检索模块 — SQLite + FTS5 三层漏斗
替代原有的 10000 行扫描方式，支持 579 万行全量检索

使用方式:
  python3 scripts/enterprise_search.py --icp .features/find-customer/data/xxx.md
  python3 scripts/enterprise_search.py --query '{"prefectureIds":[13],"minEmployeeNumber":10}' --keywords "AI,SaaS"
"""

import sqlite3
import json
import re
import os
import sys
import argparse
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "enterprises.db")

# 都道府県コード → 名称
PREFECTURE_MAP = {
    1: "北海道", 2: "青森", 3: "岩手", 4: "宮城", 5: "秋田", 6: "山形", 7: "福島",
    8: "茨城", 9: "栃木", 10: "群馬", 11: "埼玉", 12: "千葉", 13: "東京", 14: "神奈川",
    15: "新潟", 16: "富山", 17: "石川", 18: "福井", 19: "山梨", 20: "長野",
    21: "岐阜", 22: "静岡", 23: "愛知", 24: "三重", 25: "滋賀", 26: "京都",
    27: "大阪", 28: "兵庫", 29: "奈良", 30: "和歌山",
    31: "鳥取", 32: "島根", 33: "岡山", 34: "広島", 35: "山口",
    36: "徳島", 37: "香川", 38: "愛媛", 39: "高知",
    40: "福岡", 41: "佐賀", 42: "長崎", 43: "熊本", 44: "大分", 45: "宮崎", 46: "鹿児島", 47: "沖縄"
}

# 负向硬排除关键词
HARD_EXCLUDE = ["受託", "派遣", "SES", "人材紹介", "請負", "常駐", "人材派遣"]

# 正向信号（关键词 → 分数）
POSITIVE_SIGNALS = {
    "SaaS": 5,
    "プロダクト": 4,
    "自社サービス": 4, "自社開発": 4,
    "プラットフォーム": 3,
    "アプリ": 3,
    "クラウド": 2,
    "AI": 2, "人工知能": 2, "機械学習": 2,
    "DX": 2, "デジタルトランスフォーメーション": 2,
    "データ分析": 2, "データ活用": 2, "ビッグデータ": 2,
    "IoT": 2,
    "セキュリティ": 1,
}

# 负向信号（减分但不排除）
NEGATIVE_SIGNALS = {
    "コンサルティング": -2, "コンサル": -2,
    "マーケティング支援": -2, "広告運用": -2, "広告代理": -2,
    "制作": -1, "Web制作": -1,
    "人材": -1, "採用支援": -1, "HR": -1,
    "運用・保守": -1, "運用保守": -1,
}

# 行业宽匹配关键词（必须命中 ≥1 才进入候选池）
INDUSTRY_KEYWORDS = {
    "IT": ["IT", "ソフトウェア", "システム", "クラウド", "Web", "デジタル", "AI",
           "テクノロジー", "DX", "エンジニアリング", "アプリ", "データ", "SaaS",
           "プラットフォーム", "プロダクト", "ソリューション", "IoT", "セキュリティ",
           "ネットワーク", "インターネット", "テック"],
    "製造": ["製造", "メーカー", "工場", "生産"],
    "卸売小売": ["卸売", "小売", "商社", "販売", "流通"],
    "建設": ["建設", "工事", "建築", "土木"],
    "金融": ["銀行", "証券", "保険", "金融", "ファイナンス"],
    "不動産": ["不動産", "賃貸", "物件"],
    "専門サービス": ["コンサル", "法律", "会計", "広告", "デザイン", "調査"],
    "運輸": ["運輸", "物流", "配送", "倉庫"],
    "医療福祉": ["医療", "病院", "介護", "福祉"],
}


def parse_icp_file(filepath):
    """从 ICP 画像 MD 文件中提取筛选条件 JSON"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取 JSON code block
    pattern = r'```json\s*\n(.*?)\n```'
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        print("错误: ICP 文件中找不到 JSON 筛选条件")
        sys.exit(1)

    return json.loads(match.group(1))


def build_where_clause(conditions):
    """
    Layer 1: 构建结构化 WHERE 子句
    返回 (sql_fragment, params)
    """
    clauses = []
    params = []

    # 都道府県
    prefecture_ids = conditions.get("prefectureIds", [])
    if prefecture_ids:
        placeholders = ','.join(['?'] * len(prefecture_ids))
        clauses.append(f"prefecture_code IN ({placeholders})")
        params.extend(prefecture_ids)

    # 従業員数
    min_emp = conditions.get("minEmployeeNumber")
    max_emp = conditions.get("maxEmployeeNumber")
    if min_emp is not None:
        clauses.append("employee_count >= ?")
        params.append(min_emp)
    if max_emp is not None:
        clauses.append("employee_count <= ?")
        params.append(max_emp)

    # 資本金
    min_cap = conditions.get("minCapitalStock")
    max_cap = conditions.get("maxCapitalStock")
    if min_cap is not None:
        clauses.append("capital >= ?")
        params.append(min_cap)
    if max_cap is not None:
        clauses.append("capital <= ?")
        params.append(max_cap)

    # 設立年月日
    min_est = conditions.get("minEstablishmentAt")
    max_est = conditions.get("maxEstablishmentAt")
    if min_est:
        clauses.append("(established_date >= ? OR established_date IS NULL OR established_date = '')")
        params.append(min_est)
    if max_est:
        clauses.append("(established_date <= ? OR established_date IS NULL OR established_date = '')")
        params.append(max_est)

    return " AND ".join(clauses) if clauses else "1=1", params


def get_positive_keywords(conditions):
    """根据 ICP 条件构建正向关键词列表"""
    keywords = set()
    category_codes = conditions.get("categoryCodes", [])

    # 从 categoryCodes 映射行业关键词
    code_to_industry = {
        "G": "IT", "E": "製造", "I": "卸売小売", "D": "建設",
        "J": "金融", "K": "不動産", "L": "専門サービス", "H": "運輸", "P": "医療福祉"
    }
    for code in category_codes:
        industry = code_to_industry.get(code)
        if industry and industry in INDUSTRY_KEYWORDS:
            keywords.update(INDUSTRY_KEYWORDS[industry])

    # 从 enhancedConditions 提取额外关键词
    enhanced = conditions.get("enhancedConditions", [])
    for cond in enhanced:
        if isinstance(cond, dict):
            kw = cond.get("keyword", cond.get("condition", ""))
            if kw:
                keywords.add(kw)

    # 如果没有指定任何行业，默认用 IT 关键词
    if not keywords:
        keywords.update(INDUSTRY_KEYWORDS["IT"])

    return list(keywords)


def score_enterprise(text, enhanced_conditions=None):
    """
    Layer 3: 对企业文本打分
    text = business_summary + business_type 拼接
    """
    if not text:
        return 0, []

    score = 0
    signals = []

    # 正向信号（每组只计一次）
    scored_groups = set()
    for keyword, points in POSITIVE_SIGNALS.items():
        if keyword in text and keyword not in scored_groups:
            score += points
            signals.append(f"+{points}:{keyword}")
            scored_groups.add(keyword)

    # 负向信号
    for keyword, points in NEGATIVE_SIGNALS.items():
        if keyword in text:
            score += points
            signals.append(f"{points}:{keyword}")

    # enhancedConditions 加权
    if enhanced_conditions:
        for cond in enhanced_conditions:
            if isinstance(cond, dict):
                kw = cond.get("keyword", cond.get("condition", ""))
                weight = cond.get("weight", 3)
                if kw and kw in text:
                    if weight >= 4:
                        bonus = 2
                        score += bonus
                        signals.append(f"+{bonus}:enhanced({kw})")
                    elif weight <= 2:
                        penalty = -1
                        score += penalty
                        signals.append(f"{penalty}:low_weight({kw})")

    return score, signals


def search(conditions, custom_keywords=None, limit=500):
    """
    三层漏斗检索

    参数:
        conditions: ICP JSON 筛选条件
        custom_keywords: 自定义正向关键词列表（覆盖自动推断）
        limit: Layer 1 最大返回行数（默认 500，避免内存爆炸）

    返回:
        {
            "high": [...],   # ★ 高匹配 (≥4)
            "medium": [...], # ◆ 中匹配 (1-3)
            "low": [...],    # ○ 低匹配 (≤0)
            "stats": {...}
        }
    """
    if not os.path.exists(DB_PATH):
        print(f"错误: 数据库不存在 {DB_PATH}")
        print("请先运行: python3 scripts/import_csv_to_sqlite.py")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # === Layer 1: 结构化过滤 ===
    where_clause, params = build_where_clause(conditions)

    # 先用结构化条件筛选，同时要求 business_summary 或 business_type 非空
    sql = f"""
        SELECT houjin_bangou, company_name, address, prefecture,
               employee_count, capital, representative,
               business_summary, business_type, website, established_date
        FROM enterprises
        WHERE {where_clause}
          AND (business_summary IS NOT NULL AND business_summary != ''
               OR business_type IS NOT NULL AND business_type != '')
    """
    cur.execute(sql, params)
    layer1_results = cur.fetchall()
    layer1_count = len(layer1_results)

    # === Layer 2: 关键词过滤（正向 + 负向排除） ===
    positive_keywords = custom_keywords or get_positive_keywords(conditions)

    layer2_results = []
    excluded_count = 0

    for row in layer1_results:
        text = (row["business_summary"] or "") + " " + (row["business_type"] or "")

        # 负向硬排除
        if any(kw in text for kw in HARD_EXCLUDE):
            excluded_count += 1
            continue

        # 正向关键词至少命中 1 个
        if positive_keywords and not any(kw in text for kw in positive_keywords):
            continue

        layer2_results.append(row)

    layer2_count = len(layer2_results)

    # === Layer 3: 评分排序 ===
    enhanced = conditions.get("enhancedConditions", [])
    scored_results = []

    for row in layer2_results:
        text = (row["business_summary"] or "") + " " + (row["business_type"] or "")
        score, signals = score_enterprise(text, enhanced)
        scored_results.append({
            "houjin_bangou": row["houjin_bangou"],
            "company_name": row["company_name"],
            "address": row["address"],
            "prefecture": row["prefecture"],
            "employee_count": row["employee_count"],
            "capital": row["capital"],
            "representative": row["representative"],
            "business_summary": row["business_summary"],
            "business_type": row["business_type"],
            "website": row["website"],
            "established_date": row["established_date"],
            "score": score,
            "signals": signals,
        })

    # 按分数降序，同分按员工数降序
    scored_results.sort(key=lambda x: (x["score"], x["employee_count"] or 0), reverse=True)

    # 分层
    high = [r for r in scored_results if r["score"] >= 4]
    medium = [r for r in scored_results if 1 <= r["score"] <= 3]
    low = [r for r in scored_results if r["score"] <= 0]

    conn.close()

    return {
        "high": high,
        "medium": medium,
        "low": low,
        "stats": {
            "layer1_count": layer1_count,
            "layer2_excluded": excluded_count,
            "layer2_count": layer2_count,
            "high_count": len(high),
            "medium_count": len(medium),
            "low_count": len(low),
            "total_matched": len(scored_results),
            "positive_keywords": positive_keywords,
        }
    }


def fts_search(query_text, prefecture_codes=None, min_emp=None, max_emp=None, limit=100):
    """
    FTS5 全文检索 — 用于语义/自由文本搜索
    当用户输入自然语言描述（如"AI関連の企業"）时使用

    参数:
        query_text: 搜索文本（自动拆分为 OR 查询）
        prefecture_codes: 都道府県コード列表（可选）
        min_emp/max_emp: 员工数范围（可选）
        limit: 最大返回数
    """
    if not os.path.exists(DB_PATH):
        print(f"错误: 数据库不存在 {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 构建 FTS5 查询（关键词用 OR 连接）
    terms = query_text.strip().split()
    fts_query = " OR ".join(terms)

    sql = """
        SELECT e.houjin_bangou, e.company_name, e.address, e.prefecture,
               e.employee_count, e.capital, e.representative,
               e.business_summary, e.business_type, e.website, e.established_date,
               rank
        FROM enterprises_fts fts
        JOIN enterprises e ON e.rowid = fts.rowid
        WHERE enterprises_fts MATCH ?
    """
    params = [fts_query]

    if prefecture_codes:
        placeholders = ','.join(['?'] * len(prefecture_codes))
        sql += f" AND e.prefecture_code IN ({placeholders})"
        params.extend(prefecture_codes)

    if min_emp is not None:
        sql += " AND e.employee_count >= ?"
        params.append(min_emp)

    if max_emp is not None:
        sql += " AND e.employee_count <= ?"
        params.append(max_emp)

    sql += " ORDER BY rank LIMIT ?"
    params.append(limit)

    cur = conn.cursor()
    cur.execute(sql, params)
    results = [dict(row) for row in cur.fetchall()]
    conn.close()

    return results


def format_markdown_report(results, conditions, output_path=None):
    """格式化输出 Markdown 报告"""
    now = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    stats = results["stats"]

    # 条件摘要
    prefecture_ids = conditions.get("prefectureIds", [])
    prefecture_names = [PREFECTURE_MAP.get(pid, str(pid)) for pid in prefecture_ids]

    lines = []
    lines.append("# 客户匹配结果")
    lines.append(f"> 匹配时间：{now}")
    lines.append(f"> 数据源：enterprises.db (SQLite + FTS5)")
    lines.append(f"> 匹配数：{stats['total_matched']} 件（高匹配 {stats['high_count']} 件 + 中匹配 {stats['medium_count']} 件 + 低匹配 {stats['low_count']} 件）")
    lines.append("")
    lines.append("## 筛选条件摘要")
    lines.append(f"- 地域：{', '.join(prefecture_names) if prefecture_names else '全国'}")
    lines.append(f"- 员工数：{conditions.get('minEmployeeNumber', '无下限')} ~ {conditions.get('maxEmployeeNumber', '无上限')}")
    lines.append(f"- 正向关键词：{', '.join(stats['positive_keywords'][:10])}{'...' if len(stats['positive_keywords']) > 10 else ''}")
    lines.append(f"- 硬排除词：{', '.join(HARD_EXCLUDE)}")
    lines.append(f"- Layer1 结构化过滤：{stats['layer1_count']:,} 件")
    lines.append(f"- Layer2 排除：{stats['layer2_excluded']} 件（硬排除）")
    lines.append(f"- Layer2 通过：{stats['layer2_count']} 件")
    lines.append("")

    # 高匹配
    lines.append(f"## ★ 高匹配（≥4分）— {stats['high_count']} 件")
    lines.append("")
    if results["high"]:
        lines.append("| # | 企業名 | 従業員数 | 評分 | 信号 | 事業内容 | ウェブサイト | 法人番号 |")
        lines.append("|---|--------|----------|------|------|----------|-------------|----------|")
        for i, r in enumerate(results["high"], 1):
            summary = (r["business_summary"] or "")[:60]
            signals = ", ".join(r["signals"][:3])
            website = r["website"] or ""
            lines.append(f"| {i} | {r['company_name']} | {r['employee_count'] or '-'} | {r['score']} | {signals} | {summary} | {website} | {r['houjin_bangou']} |")
    else:
        lines.append("（无）")
    lines.append("")

    # 中匹配
    lines.append(f"## ◆ 中匹配（1-3分）— {stats['medium_count']} 件")
    lines.append("")
    if results["medium"]:
        lines.append("| # | 企業名 | 従業員数 | 評分 | 信号 | 事業内容 | ウェブサイト | 法人番号 |")
        lines.append("|---|--------|----------|------|------|----------|-------------|----------|")
        for i, r in enumerate(results["medium"], 1):
            summary = (r["business_summary"] or "")[:60]
            signals = ", ".join(r["signals"][:3])
            website = r["website"] or ""
            lines.append(f"| {i} | {r['company_name']} | {r['employee_count'] or '-'} | {r['score']} | {signals} | {summary} | {website} | {r['houjin_bangou']} |")
    else:
        lines.append("（无）")
    lines.append("")

    # 低匹配（只显示数量）
    lines.append(f"## ○ 低匹配（≤0分）— {stats['low_count']} 件")
    lines.append("")
    if results["low"]:
        lines.append("| # | 企業名 | 従業員数 | 評分 | 事業内容 | 法人番号 |")
        lines.append("|---|--------|----------|------|----------|----------|")
        for i, r in enumerate(results["low"][:20], 1):  # 低匹配只显示前 20
            summary = (r["business_summary"] or "")[:60]
            lines.append(f"| {i} | {r['company_name']} | {r['employee_count'] or '-'} | {r['score']} | {summary} | {r['houjin_bangou']} |")
        if len(results["low"]) > 20:
            lines.append(f"\n> 低匹配共 {stats['low_count']} 件，仅显示前 20 件")
    else:
        lines.append("（无）")

    report = "\n".join(lines)

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"报告已保存: {output_path}")

    return report


def main():
    parser = argparse.ArgumentParser(description="企业检索 — SQLite + FTS5 三层漏斗")
    parser.add_argument("--icp", help="ICP 画像 MD 文件路径")
    parser.add_argument("--query", help="JSON 格式筛选条件（直接传入）")
    parser.add_argument("--keywords", help="自定义正向关键词（逗号分隔）")
    parser.add_argument("--fts", help="FTS5 全文搜索文本")
    parser.add_argument("--output", help="输出报告路径")
    parser.add_argument("--limit", type=int, default=500, help="最大返回数")

    args = parser.parse_args()

    # FTS 搜索模式
    if args.fts:
        results = fts_search(args.fts, limit=args.limit)
        print(f"FTS 搜索结果: {len(results)} 件")
        for r in results[:20]:
            print(f"  {r['company_name']} | {r['employee_count']} | {r['business_summary'][:50] if r['business_summary'] else ''}")
        return

    # 三层漏斗模式
    if args.icp:
        conditions = parse_icp_file(args.icp)
    elif args.query:
        conditions = json.loads(args.query)
    else:
        print("错误: 请指定 --icp 或 --query 参数")
        sys.exit(1)

    custom_keywords = args.keywords.split(",") if args.keywords else None

    # 执行检索
    results = search(conditions, custom_keywords=custom_keywords, limit=args.limit)
    stats = results["stats"]

    print(f"\n=== 检索结果 ===")
    print(f"Layer 1 (结构化过滤): {stats['layer1_count']:,} 件")
    print(f"Layer 2 (关键词过滤): {stats['layer2_count']} 件 (排除 {stats['layer2_excluded']})")
    print(f"Layer 3 (评分排序):")
    print(f"  ★ 高匹配: {stats['high_count']} 件")
    print(f"  ◆ 中匹配: {stats['medium_count']} 件")
    print(f"  ○ 低匹配: {stats['low_count']} 件")

    # 输出报告
    if args.output:
        format_markdown_report(results, conditions, args.output)
    else:
        # 默认输出到 .features/customer-match/data/
        now = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        default_path = os.path.join(BASE_DIR, ".features", "customer-match", "data", f"{now}.md")
        format_markdown_report(results, conditions, default_path)


if __name__ == "__main__":
    main()
