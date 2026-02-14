"""
端到端测试

使用 Sparticle株式会社 作为测试用例
"""
import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from enterprise_report_generator.main import generate_report
from enterprise_report_generator.models import SeedData
from enterprise_report_generator.config import get_config


# 测试用例: Sparticle株式会社
TEST_SEED = {
    "company_name": "Sparticle株式会社",
    "corporate_number": "4120001222866",
    "website_url": "https://www.sparticle.com/ja",
    "address": "東京都中央区日本橋小伝馬町6-12",
}


async def test_full_pipeline():
    """测试完整流程"""
    print("=" * 60)
    print("企业营业报告生成系统 - 端到端测试")
    print("=" * 60)
    print(f"\n测试企业: {TEST_SEED['company_name']}")
    print(f"法人番号: {TEST_SEED['corporate_number']}")
    print(f"官网: {TEST_SEED['website_url']}")
    print()

    # 检查配置
    config = get_config()
    missing = config.validate()
    if missing:
        print(f"⚠️  缺少配置: {missing}")
        print("请确保 .env 文件中配置了所有必要的 API Key")
        return

    print("✓ 配置检查通过")
    print()

    # 生成报告
    print("开始生成报告...")
    print("-" * 40)

    try:
        report, quality = await generate_report(
            company_name=TEST_SEED["company_name"],
            corporate_number=TEST_SEED["corporate_number"],
            website_url=TEST_SEED["website_url"],
            address=TEST_SEED["address"],
            use_cache=False,  # 测试时不使用缓存
            save_to_file=True,
        )

        print("-" * 40)
        print("\n✓ 报告生成完成!")
        print()

        # 打印报告摘要
        print("=" * 60)
        print("报告摘要")
        print("=" * 60)

        # Layer 1
        print("\n【第一层: 基本信息】")
        l1 = report.layer1_basic_info
        print(f"  企业名: {l1.company_name}")
        print(f"  法人番号: {l1.corporate_number}")
        if l1.representative:
            print(f"  代表人: {l1.representative.name} ({l1.representative.title})")
        if l1.employee_count and l1.employee_count.value:
            print(f"  员工数: {l1.employee_count.value}人")
        if l1.capital:
            print(f"  资本金: {l1.capital.display}")
        if l1.business_overview:
            overview = l1.business_overview[:100] + "..." if len(l1.business_overview) > 100 else l1.business_overview
            print(f"  业务概要: {overview}")
        if l1.main_products:
            products = [p.name for p in l1.main_products[:3]]
            print(f"  主要产品: {', '.join(products)}")
        if l1.tags.industry:
            print(f"  行业标签: {', '.join(l1.tags.industry)}")

        # Layer 2
        print("\n【第二层: 销售指南】")
        l2 = report.layer2_sales_approach
        if l2.summary:
            print(f"  销售难度: {l2.summary.difficulty}/5 ({l2.summary.difficulty_label})")
            print(f"  推荐渠道: {l2.summary.recommended_channel}")
        if l2.timing:
            timing_str = "是" if l2.timing.is_good_timing else "否"
            print(f"  当前是好时机: {timing_str}")
            if l2.timing.reasons:
                print(f"  理由: {l2.timing.reasons[0]}")
        if l2.key_persons:
            print(f"  关键人物: {len(l2.key_persons)}人")
            for kp in l2.key_persons[:2]:
                print(f"    - {kp.name} ({kp.title}) [可信度: {kp.confidence}]")

        # Layer 3
        print("\n【第三层: 商机信号】")
        l3 = report.layer3_signals
        if l3.opportunity_score:
            print(f"  商机分数: {l3.opportunity_score.value}/100 ({l3.opportunity_score.label})")
        print(f"  近期新闻: {len(l3.recent_news)}条")
        print(f"  融资记录: {len(l3.funding_history)}条")
        print(f"  招聘信号: {len(l3.hiring_signals)}条")
        if l3.investment_interests:
            interests = [i.category for i in l3.investment_interests[:3]]
            print(f"  投资意向: {', '.join(interests)}")

        # 质量检查
        print("\n【质量检查】")
        print(f"  质量分数: {report.meta.quality_score}/100")
        print(f"  检查通过: {'是' if quality.passed else '否'}")
        if quality.warnings:
            print(f"  警告: {len(quality.warnings)}项")
            for w in quality.warnings[:3]:
                print(f"    - {w}")
        if quality.errors:
            print(f"  错误: {len(quality.errors)}项")
            for e in quality.errors:
                print(f"    - {e}")

        # 保存位置
        print(f"\n报告ID: {report.meta.report_id}")
        print(f"生成时间: {report.meta.generated_at}")

        # 导出完整 JSON 示例
        print("\n" + "=" * 60)
        print("完整 JSON 结构 (前2000字符)")
        print("=" * 60)
        json_str = report.to_json(indent=2)
        print(json_str[:2000])
        if len(json_str) > 2000:
            print(f"\n... (共 {len(json_str)} 字符)")

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


async def test_collectors_only():
    """仅测试数据收集器"""
    from enterprise_report_generator.collectors import (
        collect_basic_info,
        collect_sales_intel,
        collect_signals,
    )

    print("测试数据收集器...")

    seed = SeedData(**TEST_SEED)

    # 测试基本信息收集
    print("\n1. 测试 BasicInfoCollector...")
    basic = await collect_basic_info(seed, use_cache=False)
    print(f"   gBizINFO: {'✓' if basic.gbizinfo_data else '✗'}")
    print(f"   官网内容: {'✓' if basic.website_content else '✗'}")
    print(f"   错误: {basic.errors}")

    # 测试销售情报收集
    print("\n2. 测试 SalesIntelCollector...")
    sales = await collect_sales_intel(seed, use_cache=False)
    print(f"   高管搜索: {len(sales.executives_search_results)}条")
    print(f"   组织搜索: {len(sales.organization_search_results)}条")
    print(f"   团队页面: {'✓' if sales.team_page_content else '✗'}")
    print(f"   错误: {sales.errors}")

    # 测试商机信号收集
    print("\n3. 测试 SignalCollector...")
    signals = await collect_signals(seed, use_cache=False)
    print(f"   新闻搜索: {len(signals.news_search_results)}条")
    print(f"   融资搜索: {len(signals.funding_search_results)}条")
    print(f"   招聘搜索: {len(signals.hiring_search_results)}条")
    print(f"   PR TIMES: {len(signals.pr_times_results)}条")
    print(f"   错误: {signals.errors}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="端到端测试")
    parser.add_argument(
        "--collectors-only",
        action="store_true",
        help="仅测试数据收集器"
    )

    args = parser.parse_args()

    if args.collectors_only:
        asyncio.run(test_collectors_only())
    else:
        asyncio.run(test_full_pipeline())
