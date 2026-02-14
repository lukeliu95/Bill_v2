"""
企业营业报告自动生成系统

输入企业种子数据，自动生成面向B2B销售人员的三层结构化企业报告。
"""

__version__ = "0.1.0"
__author__ = "pSEO Team"

from .config import get_config, Config

__all__ = ["get_config", "Config", "__version__"]
