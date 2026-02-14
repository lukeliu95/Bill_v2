"""
质量检查器

验证报告质量，过滤敏感信息
"""
import re
import logging
from typing import Optional
from dataclasses import dataclass, field

from ..models import EnterpriseReport

logger = logging.getLogger(__name__)


@dataclass
class QualityCheckResult:
    """质量检查结果"""
    passed: bool = True
    score: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    filtered_fields: list[str] = field(default_factory=list)


class QualityChecker:
    """
    质量检查器

    检查项:
    - 法人番号格式校验
    - 必填字段完整性
    - URL 有效性
    - 个人隐私信息过滤
    - 质量分数阈值
    """

    # 最低可公开质量分数
    MIN_QUALITY_SCORE = 60

    def __init__(self):
        self.result = QualityCheckResult()

    def check(self, report: EnterpriseReport) -> QualityCheckResult:
        """
        执行质量检查

        Args:
            report: 企业报告

        Returns:
            QualityCheckResult
        """
        self.result = QualityCheckResult()
        self.result.score = report.meta.quality_score

        # 1. 法人番号格式校验
        self._check_corporate_number(report.layer1_basic_info.corporate_number)

        # 2. 必填字段完整性
        self._check_required_fields(report)

        # 3. URL 有效性
        self._check_urls(report)

        # 4. 过滤敏感信息
        self._filter_sensitive_info(report)

        # 5. 质量分数阈值
        self._check_quality_score(report)

        # 设置最终结果
        self.result.passed = len(self.result.errors) == 0

        return self.result

    def _check_corporate_number(self, corporate_number: str):
        """校验法人番号格式"""
        if not corporate_number:
            self.result.errors.append("法人番号为空")
            return

        if len(corporate_number) != 13:
            self.result.errors.append(f"法人番号长度错误: {len(corporate_number)} (应为13位)")
            return

        if not corporate_number.isdigit():
            self.result.errors.append("法人番号包含非数字字符")
            return

        # 校验位检查 (可选，日本法人番号有校验位规则)
        # 这里简化处理，只检查格式

    def _check_required_fields(self, report: EnterpriseReport):
        """检查必填字段"""
        layer1 = report.layer1_basic_info

        if not layer1.company_name:
            self.result.errors.append("企业名称为空")

        if not layer1.corporate_number:
            self.result.errors.append("法人番号为空")

        # 警告级别的缺失
        if not layer1.business_overview:
            self.result.warnings.append("缺少业务概要")

        if not layer1.representative:
            self.result.warnings.append("缺少代表人信息")

    def _check_urls(self, report: EnterpriseReport):
        """检查 URL 有效性"""
        layer1 = report.layer1_basic_info

        if layer1.website:
            if not self._is_valid_url(layer1.website):
                self.result.warnings.append(f"官网URL格式无效: {layer1.website}")

        # 检查新闻链接
        for news in report.layer3_signals.recent_news:
            if news.url and not self._is_valid_url(news.url):
                self.result.warnings.append(f"新闻URL格式无效: {news.url}")

    def _filter_sensitive_info(self, report: EnterpriseReport):
        """过滤敏感信息"""
        # 检查并过滤个人邮箱
        self._filter_personal_emails(report)

        # 检查并过滤电话号码
        self._filter_phone_numbers(report)

        # 检查并过滤 LinkedIn 直接 URL
        self._filter_linkedin_urls(report)

    def _filter_personal_emails(self, report: EnterpriseReport):
        """过滤个人邮箱"""
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

        # 检查关键人物的接触建议
        for kp in report.layer2_sales_approach.key_persons:
            if kp.approach_hint and re.search(email_pattern, kp.approach_hint):
                kp.approach_hint = re.sub(email_pattern, "[邮箱已隐藏]", kp.approach_hint)
                self.result.filtered_fields.append(f"key_person.{kp.name}.approach_hint")

        # 检查接触策略
        strategy = report.layer2_sales_approach.approach_strategy
        if strategy and strategy.first_contact_script:
            if strategy.first_contact_script.body_template:
                body = strategy.first_contact_script.body_template
                if re.search(email_pattern, body):
                    strategy.first_contact_script.body_template = re.sub(
                        email_pattern, "[邮箱已隐藏]", body
                    )
                    self.result.filtered_fields.append("approach_strategy.body_template")

    def _filter_phone_numbers(self, report: EnterpriseReport):
        """过滤电话号码"""
        # 日本电话号码模式
        phone_patterns = [
            r'0\d{1,4}-\d{1,4}-\d{4}',  # 固定电话
            r'0[789]0-\d{4}-\d{4}',      # 手机
            r'\+81-\d{1,4}-\d{1,4}-\d{4}',  # 国际格式
        ]

        combined_pattern = '|'.join(phone_patterns)

        # 检查关键人物
        for kp in report.layer2_sales_approach.key_persons:
            if kp.approach_hint and re.search(combined_pattern, kp.approach_hint):
                kp.approach_hint = re.sub(combined_pattern, "[电话已隐藏]", kp.approach_hint)
                self.result.filtered_fields.append(f"key_person.{kp.name}.phone")

    def _filter_linkedin_urls(self, report: EnterpriseReport):
        """过滤 LinkedIn 直接 URL"""
        linkedin_url_pattern = r'https?://(www\.)?linkedin\.com/in/[a-zA-Z0-9-]+'

        for kp in report.layer2_sales_approach.key_persons:
            # 检查 approach_hint
            if kp.approach_hint and re.search(linkedin_url_pattern, kp.approach_hint):
                kp.approach_hint = re.sub(
                    linkedin_url_pattern,
                    "[LinkedIn URL已移除，请使用搜索查询]",
                    kp.approach_hint
                )
                self.result.filtered_fields.append(f"key_person.{kp.name}.linkedin_url")

            # 确保 linkedin_search_query 不是 URL
            if kp.linkedin_search_query and re.search(linkedin_url_pattern, kp.linkedin_search_query):
                # 转换为搜索查询
                kp.linkedin_search_query = f"{kp.name} {kp.title or ''}"
                self.result.filtered_fields.append(f"key_person.{kp.name}.linkedin_search_query")

    def _check_quality_score(self, report: EnterpriseReport):
        """检查质量分数"""
        if report.meta.quality_score < self.MIN_QUALITY_SCORE:
            self.result.warnings.append(
                f"质量分数 ({report.meta.quality_score}) 低于阈值 ({self.MIN_QUALITY_SCORE})"
            )

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """验证 URL 格式"""
        url_pattern = re.compile(
            r'^https?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE
        )
        return url_pattern.match(url) is not None


# ============================================================
# 便捷函数
# ============================================================

def check_report_quality(report: EnterpriseReport) -> QualityCheckResult:
    """
    检查报告质量的便捷函数

    Args:
        report: 企业报告

    Returns:
        QualityCheckResult
    """
    checker = QualityChecker()
    return checker.check(report)


if __name__ == "__main__":
    print("QualityChecker 模块加载成功")
