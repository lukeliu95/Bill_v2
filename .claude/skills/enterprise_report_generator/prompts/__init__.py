"""
AI Prompts
"""
from .basic_info_prompt import (
    SYSTEM_INSTRUCTION as BASIC_INFO_SYSTEM,
    build_basic_info_prompt,
)
from .sales_approach_prompt import (
    SYSTEM_INSTRUCTION as SALES_APPROACH_SYSTEM,
    build_sales_approach_prompt,
)
from .signals_prompt import (
    SYSTEM_INSTRUCTION as SIGNALS_SYSTEM,
    build_signals_prompt,
)
from .linkedin_filter_prompt import (
    get_linkedin_filter_prompt,
    get_contact_approach_prompt,
)
from .social_media_prompt import (
    SOCIAL_MEDIA_SYSTEM,
    build_social_media_section,
)

__all__ = [
    "BASIC_INFO_SYSTEM",
    "build_basic_info_prompt",
    "SALES_APPROACH_SYSTEM",
    "build_sales_approach_prompt",
    "SIGNALS_SYSTEM",
    "build_signals_prompt",
    # LinkedIn
    "get_linkedin_filter_prompt",
    "get_contact_approach_prompt",
    # Social Media
    "SOCIAL_MEDIA_SYSTEM",
    "build_social_media_section",
]
