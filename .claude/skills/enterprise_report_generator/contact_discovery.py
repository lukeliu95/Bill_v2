"""
联系方式发现 - CLI 入口

独立运行联系方式发现，可用于测试或单独查询联系方式。

用法:
    python3 -m enterprise_report_generator.contact_discovery \
        --company "Sparticle株式会社" \
        --number "4120001222866" \
        --url "https://www.sparticle.com/ja"
"""
import asyncio
import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import get_config
from .models import SeedData
from .collectors.contact_discovery_collector import ContactDiscoveryCollector
from .collectors.contact_models import ContactDiscoveryRaw

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def export_contacts_md(
    result: ContactDiscoveryRaw,
    seed: SeedData,
    output_dir: Path,
) -> Path:
    """将联系方式结果导出为 Markdown"""
    ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    company_dir = output_dir / seed.company_name / "contacts"
    company_dir.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append(f"# 連絡先情報: {seed.company_name}")
    lines.append(f"\n> 採集時間: {ts}")
    lines.append(f"> データソース: {', '.join(result.sources_used)}")
    lines.append("")

    # 推奨コンタクトルート
    if result.recommended_routes:
        lines.append("## 推奨コンタクトルート")
        lines.append("")
        for route in result.recommended_routes:
            prob_map = {"high": "高", "medium": "中", "low": "低"}
            prob = prob_map.get(route.success_probability, "不明")
            lines.append(f"### {route.rank}. {route.route_type} (成功率: {prob})")
            lines.append(f"- チャネル: {route.channel}")
            if route.target_person:
                lines.append(f"- ターゲット: {route.target_person}")
            lines.append(f"- 詳細: {route.detail}")
            lines.append("")

    # 企業連絡先
    ci = result.company_contacts
    if any([ci.main_phone, ci.main_email, ci.contact_form_url]):
        lines.append("## 企業連絡先")
        lines.append("")
        if ci.main_phone:
            lines.append(f"- 代表電話: {ci.main_phone}")
        if ci.main_email:
            lines.append(f"- 代表メール: {ci.main_email}")
        if ci.contact_form_url:
            lines.append(f"- 問い合わせフォーム: {ci.contact_form_url}")
        if ci.ir_email:
            lines.append(f"- IR: {ci.ir_email}")
        if ci.pr_email:
            lines.append(f"- 広報: {ci.pr_email}")
        if ci.recruit_email:
            lines.append(f"- 採用: {ci.recruit_email}")
        lines.append("")

    # 発見した連絡人
    if result.key_persons:
        lines.append(f"## キーパーソン (計{len(result.key_persons)}名)")
        lines.append("")
        for i, p in enumerate(result.key_persons, 1):
            lines.append(f"### {i}. {p.name}")
            if p.title:
                lines.append(f"- 役職: {p.title}")
            if p.department:
                lines.append(f"- 部門: {p.department}")
            if p.email:
                lines.append(f"- メール: {p.email}")
            if p.phone:
                lines.append(f"- 電話: {p.phone}")
            if p.linkedin_url:
                lines.append(f"- LinkedIn: {p.linkedin_url}")
            if p.twitter_url:
                lines.append(f"- X/Twitter: {p.twitter_url}")
            lines.append(f"- ソース: {p.source} (信頼度: {p.confidence})")
            if p.notes:
                lines.append(f"- 備考: {p.notes}")
            lines.append("")

    # エラー
    if result.errors:
        lines.append("## 採集エラー")
        lines.append("")
        for err in result.errors:
            lines.append(f"- {err}")
        lines.append("")

    filepath = company_dir / f"{ts}_連絡先情報.md"
    filepath.write_text("\n".join(lines), encoding="utf-8")
    return filepath


def main():
    """CLI 入口"""
    parser = argparse.ArgumentParser(
        description="企業連絡先自動発見ツール"
    )
    parser.add_argument("--company", "-c", required=True, help="企業名称")
    parser.add_argument("--number", "-n", required=True, help="法人番号 (13桁)")
    parser.add_argument("--url", "-u", required=True, help="公式サイトURL")
    parser.add_argument("--no-cache", action="store_true", help="キャッシュ無効")
    parser.add_argument("--max-linkedin", type=int, default=3, help="LinkedIn検索上限")

    args = parser.parse_args()

    seed = SeedData(
        company_name=args.company,
        corporate_number=args.number,
        website_url=args.url,
    )

    config = get_config()

    async def run():
        collector = ContactDiscoveryCollector(
            use_cache=not args.no_cache,
            max_linkedin_lookups=args.max_linkedin,
        )
        result = await collector.run(seed)

        # 导出
        filepath = export_contacts_md(result, seed, config.output_dir)
        print(f"\n連絡先情報を出力しました: {filepath}")
        print(f"  キーパーソン: {len(result.key_persons)}名")
        print(f"  推奨ルート: {len(result.recommended_routes)}件")
        print(f"  データソース: {', '.join(result.sources_used)}")
        if result.errors:
            print(f"  エラー: {len(result.errors)}件")

    asyncio.run(run())


if __name__ == "__main__":
    main()
