"""
企业营业报告自动生成系统 - 主入口

完整流程:
1. 接收种子数据
2. 并行收集基本信息、销售情报、商机信号
3. AI 分析生成三层报告
4. 质量检查
5. 输出 JSON + Markdown 报告
"""
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import get_config
from .models import SeedData, CollectedData, EnterpriseReport
from .collectors import (
    BasicInfoCollector,
    SalesIntelCollector,
    SignalCollector,
    SocialMediaCollector,
)
from .analyzers import AIAnalyzer
from .validators.quality_checker import QualityChecker, QualityCheckResult
from .exporters import DataExporter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    报告生成器

    编排整个报告生成流程
    """

    def __init__(self, use_cache: bool = True):
        """
        初始化报告生成器

        Args:
            use_cache: 是否使用缓存
        """
        self.use_cache = use_cache
        self.config = get_config()

        # 验证配置
        missing = self.config.validate()
        if missing:
            logger.warning(f"缺少配置项: {missing}")

        # 确保目录存在
        self.config.ensure_dirs()

    async def generate(
        self,
        seed: SeedData,
        save_to_file: bool = True,
    ) -> tuple[EnterpriseReport, QualityCheckResult]:
        """
        生成企业报告

        Args:
            seed: 种子数据
            save_to_file: 是否保存到文件

        Returns:
            (报告, 质量检查结果)
        """
        start_time = datetime.now()
        logger.info(f"=== 开始生成报告: {seed.company_name} ===")

        # Step 1: 并行收集数据
        logger.info("Step 1: 收集数据...")
        collected_data = await self._collect_data(seed)

        # Step 2: AI 分析
        logger.info("Step 2: AI 分析...")
        analyzer = AIAnalyzer()
        report = await analyzer.analyze(collected_data)

        # Step 3: 质量检查
        logger.info("Step 3: 质量检查...")
        checker = QualityChecker()
        quality_result = checker.check(report)

        # Step 4: 导出企业知识库（5个维度MD + 1个合并报告，统一放在企业名文件夹下）
        if save_to_file:
            logger.info("Step 4: 导出报告...")
            exporter = DataExporter(self.config.output_dir)
            kb_path = exporter.export(collected_data, report)
            logger.info(f"报告已导出: {kb_path}")

        # 完成
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"=== 报告生成完成 ===")
        logger.info(f"  质量分数: {report.meta.quality_score}")
        logger.info(f"  检查通过: {quality_result.passed}")
        logger.info(f"  警告数: {len(quality_result.warnings)}")
        logger.info(f"  总耗时: {duration:.2f}s")

        return report, quality_result

    async def _collect_data(self, seed: SeedData) -> CollectedData:
        """
        并行收集所有数据

        Args:
            seed: 种子数据

        Returns:
            CollectedData
        """
        # 创建收集器
        basic_collector = BasicInfoCollector(use_cache=self.use_cache)
        sales_collector = SalesIntelCollector(use_cache=self.use_cache)
        signal_collector = SignalCollector(use_cache=self.use_cache)

        # 基础3个并行任务
        tasks = [
            basic_collector.run(seed),
            sales_collector.run(seed),
            signal_collector.run(seed),
        ]
        collector_names = ["BasicInfo", "SalesIntel", "Signal"]

        # 如果启用社交媒体采集，添加第4个并行任务
        if self.config.has_social_media_config():
            social_collector = SocialMediaCollector(use_cache=self.use_cache)
            tasks.append(social_collector.run(seed))
            collector_names.append("SocialMedia")

        # 并行执行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        basic_info = results[0] if not isinstance(results[0], Exception) else None
        sales_intel = results[1] if not isinstance(results[1], Exception) else None
        signals = results[2] if not isinstance(results[2], Exception) else None
        social_media = None
        if len(results) > 3:
            social_media = results[3] if not isinstance(results[3], Exception) else None

        # 记录错误
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"{collector_names[i]} 收集失败: {result}")

        return CollectedData(
            seed=seed,
            basic_info=basic_info,
            sales_intel=sales_intel,
            signals=signals,
            social_media=social_media,
            collected_at=datetime.now(),
        )


# ============================================================
# 便捷函数
# ============================================================

async def generate_report(
    company_name: str,
    corporate_number: str,
    website_url: str,
    address: Optional[str] = None,
    use_cache: bool = True,
    save_to_file: bool = True,
) -> tuple[EnterpriseReport, QualityCheckResult]:
    """
    生成企业报告的便捷函数

    Args:
        company_name: 企业名称
        corporate_number: 法人番号 (13位)
        website_url: 官网 URL
        address: 地址 (可选)
        use_cache: 是否使用缓存
        save_to_file: 是否保存文件

    Returns:
        (报告, 质量检查结果)
    """
    seed = SeedData(
        company_name=company_name,
        corporate_number=corporate_number,
        website_url=website_url,
        address=address,
    )

    generator = ReportGenerator(use_cache=use_cache)
    return await generator.generate(seed, save_to_file=save_to_file)


# ============================================================
# CLI 入口
# ============================================================

def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="企业营业报告自动生成系统"
    )
    parser.add_argument(
        "--company", "-c",
        required=True,
        help="企业名称"
    )
    parser.add_argument(
        "--number", "-n",
        required=True,
        help="法人番号 (13位)"
    )
    parser.add_argument(
        "--url", "-u",
        required=True,
        help="官网 URL"
    )
    parser.add_argument(
        "--address", "-a",
        default=None,
        help="地址 (可选)"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="不使用缓存"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="不保存到文件"
    )
    args = parser.parse_args()

    # 运行
    async def run():
        report, quality = await generate_report(
            company_name=args.company,
            corporate_number=args.number,
            website_url=args.url,
            address=args.address,
            use_cache=not args.no_cache,
            save_to_file=not args.no_save,
        )

        # 打印质量信息
        print(f"\n--- 质量检查 ---")
        print(f"通过: {quality.passed}")
        print(f"分数: {quality.score}")
        if quality.warnings:
            print(f"警告: {quality.warnings}")
        if quality.errors:
            print(f"错误: {quality.errors}")

    asyncio.run(run())


if __name__ == "__main__":
    main()
