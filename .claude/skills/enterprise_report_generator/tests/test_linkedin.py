"""
LinkedIn 模块端到端测试

测试 LinkedIn 数据采集功能
"""
import asyncio
import os
import sys
from pathlib import Path

# 确保可以导入项目模块
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from enterprise_report_generator.config import get_config
from enterprise_report_generator.models import SeedData
from enterprise_report_generator.collectors.linkedin_collector import (
    LinkedInCollector,
    LinkedInData,
    collect_linkedin_data,
)
from enterprise_report_generator.utils.brightdata_client import BrightDataClient


def print_section(title: str):
    """打印分隔线"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


async def test_config():
    """测试配置"""
    print_section("1. 配置检查")

    config = get_config()

    print(f"Bright Data API Key: {'已配置' if config.brightdata.api_key else '未配置'}")
    print(f"Bright Data User ID: {'已配置' if config.brightdata.user_id else '未配置'}")
    print(f"LinkedIn 采集: {'已启用' if config.has_linkedin_config() else '未启用'}")

    if not config.has_linkedin_config():
        print("\n⚠️  警告: Bright Data 未配置，LinkedIn 测试将跳过")
        print("    请在 .env 文件中配置 BRIGHT_DATA_API_KEY 和 BRIGHT_DATA_USER_ID")
        return False

    print("\n✓ 配置检查通过")
    return True


async def test_brightdata_client():
    """测试 Bright Data 客户端"""
    print_section("2. Bright Data 客户端测试")

    config = get_config()
    if not config.has_linkedin_config():
        print("⏭️  跳过 (未配置 Bright Data)")
        return

    client = BrightDataClient(config)

    # 测试公司资料获取
    test_url = "https://www.linkedin.com/company/sparticle"
    print(f"测试获取公司资料: {test_url}")

    try:
        profile = await client.get_company_profile(test_url)

        if profile:
            print(f"\n✓ 公司资料获取成功")
            print(f"  - 公司名: {profile.name}")
            print(f"  - 行业: {profile.industry}")
            print(f"  - 规模: {profile.company_size}")
            print(f"  - 员工数: {len(profile.employees)}")

            if profile.employees:
                print(f"\n  员工列表 (前5人):")
                for emp in profile.employees[:5]:
                    print(f"    - {emp.name}: {emp.title}")
        else:
            print("✗ 公司资料获取失败")

    except Exception as e:
        print(f"✗ 异常: {e}")


async def test_linkedin_collector():
    """测试 LinkedIn 收集器"""
    print_section("3. LinkedIn 收集器测试")

    config = get_config()
    if not config.has_linkedin_config():
        print("⏭️  跳过 (未配置 Bright Data)")
        return

    # 使用 Sparticle 作为测试用例
    seed = SeedData(
        company_name="Sparticle株式会社",
        corporate_number="4120001222866",
        website_url="https://www.sparticle.com/ja",
    )

    print(f"测试企业: {seed.company_name}")
    print(f"官网: {seed.website_url}")

    try:
        result = await collect_linkedin_data(seed, config)

        print(f"\n采集状态: {result.collection_status}")

        if result.collection_status == "complete":
            print(f"\n✓ LinkedIn 数据采集成功")

            if result.company_linkedin_url:
                print(f"  - 公司 LinkedIn: {result.company_linkedin_url}")

            if result.company_profile:
                print(f"  - 公司名: {result.company_profile.name}")
                print(f"  - 行业: {result.company_profile.industry}")

            print(f"  - 总员工数: {len(result.all_employees)}")
            print(f"  - 关键人物: {len(result.key_persons)}")

            if result.key_persons:
                print(f"\n  关键人物列表:")
                for person in result.key_persons:
                    print(f"    - {person.name}: {person.title}")
                    if person.summary:
                        print(f"      简介: {person.summary[:100]}...")

        elif result.collection_status == "partial":
            print(f"⚠️  部分采集成功")
            print(f"  - 员工数: {len(result.all_employees)}")

        else:
            print(f"✗ 采集失败: {result.error_message}")

    except Exception as e:
        print(f"✗ 异常: {e}")
        import traceback
        traceback.print_exc()


async def test_sales_intel_with_linkedin():
    """测试集成到 SalesIntelCollector"""
    print_section("4. SalesIntelCollector 集成测试")

    config = get_config()

    from enterprise_report_generator.collectors.sales_intel_collector import (
        collect_sales_intel
    )

    seed = SeedData(
        company_name="Sparticle株式会社",
        corporate_number="4120001222866",
        website_url="https://www.sparticle.com/ja",
    )

    print(f"测试企业: {seed.company_name}")
    print(f"LinkedIn 采集: {'启用' if config.has_linkedin_config() else '禁用'}")

    try:
        result = await collect_sales_intel(
            seed,
            use_cache=False,
            enable_linkedin=config.has_linkedin_config()
        )

        print(f"\n✓ 销售情报收集完成")
        print(f"  - 高管搜索结果: {len(result.executives_search_results)} 条")
        print(f"  - 组织搜索结果: {len(result.organization_search_results)} 条")
        print(f"  - 团队页面: {'有' if result.team_page_content else '无'}")
        print(f"  - LinkedIn 搜索: {'有' if result.linkedin_data else '无'}")
        print(f"  - LinkedIn 深度采集: {'有' if result.linkedin_profiles else '无'}")

        if result.linkedin_profiles:
            profiles = result.linkedin_profiles
            print(f"\n  LinkedIn 深度采集详情:")
            print(f"    - 采集状态: {profiles.get('collection_status')}")
            print(f"    - 员工数: {profiles.get('employee_count', 0)}")
            print(f"    - 关键人物: {len(profiles.get('key_persons', []))}")

        if result.errors:
            print(f"\n  错误: {result.errors}")

    except Exception as e:
        print(f"✗ 异常: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主测试流程"""
    print("\n" + "="*60)
    print("  LinkedIn 模块端到端测试")
    print("="*60)

    # 1. 配置检查
    config_ok = await test_config()

    # 2. Bright Data 客户端测试
    if config_ok:
        await test_brightdata_client()

    # 3. LinkedIn 收集器测试
    if config_ok:
        await test_linkedin_collector()

    # 4. SalesIntelCollector 集成测试
    await test_sales_intel_with_linkedin()

    print_section("测试完成")


if __name__ == "__main__":
    asyncio.run(main())
