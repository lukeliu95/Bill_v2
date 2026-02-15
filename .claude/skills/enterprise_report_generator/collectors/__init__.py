"""
数据收集器
"""
from .base_collector import BaseCollector, CollectorResult
from .basic_info_collector import BasicInfoCollector, collect_basic_info
from .sales_intel_collector import SalesIntelCollector, collect_sales_intel
from .signal_collector import SignalCollector, collect_signals
from .linkedin_collector import (
    LinkedInCollector,
    LinkedInData,
    KeyPersonCandidate,
    collect_linkedin_data,
)
from .social_media_collector import (
    SocialMediaCollector,
    collect_social_media,
)

__all__ = [
    "BaseCollector",
    "CollectorResult",
    "BasicInfoCollector",
    "collect_basic_info",
    "SalesIntelCollector",
    "collect_sales_intel",
    "SignalCollector",
    "collect_signals",
    # LinkedIn
    "LinkedInCollector",
    "LinkedInData",
    "KeyPersonCandidate",
    "collect_linkedin_data",
    # Social Media
    "SocialMediaCollector",
    "collect_social_media",
]
