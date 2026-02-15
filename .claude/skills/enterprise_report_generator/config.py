"""
企业营业报告生成器 - 配置管理
"""
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# 项目根目录（.claude/skills/enterprise_report_generator/ → 往上3级到 Bill_v2/）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# 显式加载项目根目录的 .env
load_dotenv(PROJECT_ROOT / ".env")


@dataclass
class SerperConfig:
    """Serper API 配置"""
    api_key: str = field(default_factory=lambda: os.getenv("SERPER_API_KEY", ""))
    base_url: str = "https://google.serper.dev"
    timeout: int = 30
    max_retries: int = 3


@dataclass
class GBizInfoConfig:
    """gBizINFO API 配置"""
    api_token: str = field(default_factory=lambda: os.getenv("GBIZINFO_API_TOKEN", ""))
    base_url: str = "https://info.gbiz.go.jp/hojin/v1"
    timeout: int = 30
    max_retries: int = 3


@dataclass
class GeminiConfig:
    """Gemini API 配置"""
    api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    model_name: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL_NAME", "gemini-3-pro-preview"))
    timeout: int = 60
    max_retries: int = 3
    temperature: float = 0.3  # 较低温度确保输出稳定


@dataclass
class CrawlerConfig:
    """Crawl4AI 爬虫配置"""
    timeout: int = 30
    max_retries: int = 2
    delay_between_requests: float = 2.0  # 同一域名请求间隔(秒)
    respect_robots_txt: bool = True
    user_agent: str = "Mozilla/5.0 (compatible; EnterpriseReportBot/1.0)"


@dataclass
class BrightDataConfig:
    """Bright Data MCP 配置 (LinkedIn + 社交媒体数据采集)"""
    api_key: str = field(default_factory=lambda: os.getenv("BRIGHT_DATA_API_KEY", ""))
    user_id: str = field(default_factory=lambda: os.getenv("BRIGHT_DATA_USER_ID", ""))
    mcp_server_url: str = "https://mcp.brightdata.com/sse"
    timeout: int = 60
    max_retries: int = 3
    # LinkedIn 配置
    max_employees_per_request: int = 50
    max_key_persons: int = 10
    # 社交媒体配置
    enable_social_media: bool = True
    max_posts_per_platform: int = 5
    social_platforms: list = field(default_factory=lambda: [
        "instagram", "facebook", "tiktok", "twitter", "youtube", "reddit"
    ])

    @property
    def mcp_url_with_token(self) -> str:
        """返回带 token 的 MCP Server URL"""
        if self.api_key:
            return f"{self.mcp_server_url}?token={self.api_key}&pro=1"
        return self.mcp_server_url


@dataclass
class NewsEnrichmentConfig:
    """新闻全文爬取配置"""
    enabled: bool = True                      # 是否启用新闻全文爬取
    max_articles: int = 10                    # 最多爬取文章数
    max_content_length: int = 5000            # 单篇最大字数
    concurrency: int = 3                      # 并发数
    timeout: float = 15.0                     # 单篇超时(秒)
    delay_between_requests: float = 1.5       # 请求间隔(秒)


@dataclass
class CacheConfig:
    """缓存配置"""
    enabled: bool = True
    cache_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "cache")

    # TTL (秒)
    basic_info_ttl: int = 30 * 24 * 60 * 60      # 30天
    website_content_ttl: int = 7 * 24 * 60 * 60   # 7天
    search_results_ttl: int = 24 * 60 * 60        # 24小时
    ai_analysis_ttl: int = 7 * 24 * 60 * 60       # 7天
    linkedin_ttl: int = 7 * 24 * 60 * 60          # 7天 (LinkedIn 数据)


@dataclass
class Config:
    """主配置类"""
    serper: SerperConfig = field(default_factory=SerperConfig)
    gbizinfo: GBizInfoConfig = field(default_factory=GBizInfoConfig)
    gemini: GeminiConfig = field(default_factory=GeminiConfig)
    crawler: CrawlerConfig = field(default_factory=CrawlerConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    brightdata: BrightDataConfig = field(default_factory=BrightDataConfig)
    news_enrichment: NewsEnrichmentConfig = field(default_factory=NewsEnrichmentConfig)

    # 日志级别
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    # 输出目录
    output_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "output")

    def validate(self, require_linkedin: bool = False) -> list[str]:
        """验证配置完整性，返回缺失项列表

        Args:
            require_linkedin: 是否要求 LinkedIn 相关配置
        """
        missing = []

        if not self.serper.api_key:
            missing.append("SERPER_API_KEY")
        if not self.gbizinfo.api_token:
            missing.append("GBIZINFO_API_TOKEN")
        if not self.gemini.api_key:
            missing.append("GEMINI_API_KEY")

        # LinkedIn 配置 (可选)
        if require_linkedin:
            if not self.brightdata.api_key:
                missing.append("BRIGHT_DATA_API_KEY")
            if not self.brightdata.user_id:
                missing.append("BRIGHT_DATA_USER_ID")

        return missing

    def has_linkedin_config(self) -> bool:
        """检查是否配置了 LinkedIn 数据采集"""
        return bool(self.brightdata.api_key and self.brightdata.user_id)

    def has_social_media_config(self) -> bool:
        """检查是否配置了社交媒体数据采集"""
        return (
            bool(self.brightdata.api_key)
            and self.brightdata.enable_social_media
            and bool(self.brightdata.social_platforms)
        )

    def ensure_dirs(self):
        """确保必要目录存在"""
        self.cache.cache_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


# 全局配置实例
config = Config()


def get_config() -> Config:
    """获取配置实例"""
    return config


if __name__ == "__main__":
    # 测试配置加载
    cfg = get_config()
    missing = cfg.validate()

    if missing:
        print(f"警告: 缺少以下核心环境变量: {missing}")
    else:
        print("核心配置加载成功!")

    print("\n配置状态:")
    print(f"  - Serper API: {'已配置' if cfg.serper.api_key else '未配置'}")
    print(f"  - gBizINFO API: {'已配置' if cfg.gbizinfo.api_token else '未配置'}")
    print(f"  - Gemini API: {'已配置' if cfg.gemini.api_key else '未配置'}")
    print(f"  - Gemini Model: {cfg.gemini.model_name}")
    print(f"  - Bright Data API: {'已配置' if cfg.brightdata.api_key else '未配置'}")
    print(f"  - Bright Data User: {'已配置' if cfg.brightdata.user_id else '未配置'}")

    if cfg.has_linkedin_config():
        print("\n✓ LinkedIn 数据采集已启用")
        print(f"  - MCP URL: {cfg.brightdata.mcp_server_url}")
    else:
        print("\n⚠ LinkedIn 数据采集未配置 (可选功能)")

    if cfg.has_social_media_config():
        print(f"\n✓ 社交媒体数据采集已启用")
        print(f"  - 平台: {', '.join(cfg.brightdata.social_platforms)}")
        print(f"  - 每平台最大帖子数: {cfg.brightdata.max_posts_per_platform}")
    else:
        print("\n⚠ 社交媒体数据采集未启用")
