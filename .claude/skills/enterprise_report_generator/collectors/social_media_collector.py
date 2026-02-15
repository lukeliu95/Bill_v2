"""
社交媒体数据收集器

通过 Serper 搜索企业社交账号 URL，再通过 BrightData 采集各平台数据。
各平台并行采集，单平台失败不影响其他。
"""
import asyncio
import logging
from typing import Optional
from dataclasses import dataclass

from .base_collector import BaseCollector
from ..models import SeedData, SocialMediaRaw
from ..utils.brightdata_client import BrightDataClient, SocialProfile, SocialPost
from ..config import get_config

logger = logging.getLogger(__name__)

# 平台 → 搜索域名映射
PLATFORM_DOMAINS = {
    "instagram": "instagram.com",
    "facebook": "facebook.com",
    "tiktok": "tiktok.com",
    "twitter": "x.com",
    "youtube": "youtube.com",
    "reddit": "reddit.com",
}


def _clean_url(platform: str, url: str) -> tuple[str, bool]:
    """清洗 URL，返回 (cleaned_url, is_profile_url)

    修正搜索结果中 URL 格式不合要求的问题：
    - 去除查询参数（?tl=ja 等）
    - TikTok: 视频URL → 提取 profile URL
    - Reddit: 确保是 subreddit 或 profile URL
    """
    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(url)
    # 去除查询参数和 fragment
    clean = urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/") + "/", "", "", ""))

    if platform == "tiktok":
        # 视频URL: tiktok.com/@user/video/123 → tiktok.com/@user/
        path = parsed.path
        if "/video/" in path:
            user_part = path.split("/video/")[0]
            clean = urlunparse((parsed.scheme, parsed.netloc, user_part + "/", "", "", ""))
        # 确认是 profile URL（包含 @username）
        is_profile = "/@" in clean
        return clean, is_profile

    if platform == "twitter":
        # x.com/username → profile URL
        # x.com/username/status/123 → post URL
        is_profile = "/status/" not in parsed.path and "/statuses/" not in parsed.path
        return clean, is_profile

    if platform == "reddit":
        # 确保是 subreddit URL（/r/xxx/）
        is_profile = "/r/" in parsed.path or "/user/" in parsed.path
        return clean, is_profile

    if platform == "youtube":
        # youtube.com/@channel 或 youtube.com/channel/xxx → profile
        is_profile = "/@" in parsed.path or "/channel/" in parsed.path or "/c/" in parsed.path
        return clean, is_profile

    # instagram, facebook: 默认就是 profile URL
    return clean, True


class SocialMediaCollector(BaseCollector):
    """社交媒体数据收集器

    工作流程:
    1. 通过 Serper 搜索企业在各平台的账号 URL
    2. 调用 BrightData 获取各平台 Profile 数据
    3. 获取最近 Posts（每平台 top N 条）
    4. 汇总为 SocialMediaRaw
    """

    name = "SocialMediaCollector"
    cache_category = "social_media"

    def __init__(self, config=None, use_cache: bool = True):
        super().__init__(use_cache=use_cache)
        self.config = config or get_config()
        self.brightdata_client = BrightDataClient(self.config)
        self.max_posts = self.config.brightdata.max_posts_per_platform
        self.enabled_platforms = self.config.brightdata.social_platforms

    async def collect(self, seed: SeedData) -> SocialMediaRaw:
        """执行社交媒体数据采集"""
        result = SocialMediaRaw()

        if not self.config.has_social_media_config():
            logger.info("Social media collection skipped: not configured")
            return result

        # 并行搜索各平台的企业账号 URL
        platform_urls = await self._find_social_urls(seed)

        if not platform_urls:
            logger.warning(f"No social media accounts found for {seed.company_name}")
            result.errors.append("No social media accounts found")
            return result

        # 并行采集各平台数据
        tasks = {}
        for platform, url in platform_urls.items():
            if platform in self.enabled_platforms:
                tasks[platform] = asyncio.create_task(
                    self._collect_platform(platform, url)
                )

        if tasks:
            await asyncio.gather(*tasks.values(), return_exceptions=True)

        for platform, task in tasks.items():
            try:
                platform_data = task.result()
                if isinstance(platform_data, Exception):
                    result.errors.append(f"{platform}: {platform_data}")
                    continue
                # 将平台数据写入对应字段
                setattr(result, platform, platform_data)
            except Exception as e:
                result.errors.append(f"{platform}: {e}")

        return result

    async def _find_social_urls(self, seed: SeedData) -> dict[str, str]:
        """通过 Serper 搜索企业在各平台的账号 URL

        Returns:
            {platform: url} 映射
        """
        from ..utils.serper_client import SerperClient

        platform_urls = {}

        async with SerperClient(self.config.serper) as serper:
            # 并行搜索各平台
            search_tasks = {}
            for platform in self.enabled_platforms:
                if platform not in PLATFORM_DOMAINS:
                    continue
                domain = PLATFORM_DOMAINS[platform]
                query = f'"{seed.company_name}" site:{domain}'
                search_tasks[platform] = asyncio.create_task(
                    serper.search(query, num_results=3)
                )

            if search_tasks:
                await asyncio.gather(*search_tasks.values(), return_exceptions=True)

            for platform, task in search_tasks.items():
                try:
                    results = task.result()
                    if isinstance(results, Exception):
                        logger.warning(f"Search failed for {platform}: {results}")
                        continue
                    if results and results.results:
                        domain = PLATFORM_DOMAINS[platform]
                        for item in results.results:
                            if domain in item.link.lower():
                                platform_urls[platform] = item.link
                                logger.info(f"Found {platform} URL: {item.link}")
                                break
                except Exception as e:
                    logger.warning(f"Search error for {platform}: {e}")

        return platform_urls

    # 这些平台的 Posts "Discover" 端点支持从 profile URL 获取帖子列表
    # Twitter posts 端点只接受单条推文 URL，不支持从 profile 发现
    # Reddit posts 端点只接受单条帖子 URL 或 subreddit URL
    POSTS_DISCOVER_FROM_PROFILE = {"instagram", "tiktok", "youtube"}

    async def _collect_platform(self, platform: str, url: str) -> Optional[dict]:
        """采集单个平台的数据

        Returns:
            {"profile": {...}, "posts": [...]} 或 None
        """
        data = {}

        # URL 清洗：去查询参数、修正格式
        cleaned_url, is_profile = _clean_url(platform, url)
        logger.info(f"[{platform}] cleaned URL: {cleaned_url} (is_profile={is_profile})")

        # 获取 Profile（不是所有平台都支持 profile 采集）
        has_profile_dataset = platform in BrightDataClient.PLATFORM_PROFILE_DATASETS
        if has_profile_dataset and is_profile:
            try:
                profile = await self.brightdata_client.get_social_profile(platform, cleaned_url)
                if profile:
                    data["profile"] = {
                        "url": profile.url,
                        "name": profile.name,
                        "username": profile.username,
                        "description": profile.description,
                        "followers": profile.followers,
                        "following": profile.following,
                        "posts_count": profile.posts_count,
                        "verified": profile.verified,
                        "external_url": profile.external_url,
                    }
            except Exception as e:
                logger.warning(f"Failed to get {platform} profile: {e}")

        # 获取 Posts — 只在该平台支持从 profile URL 发现帖子时才尝试
        has_posts_dataset = platform in BrightDataClient.PLATFORM_POSTS_DATASETS
        can_discover_posts = platform in self.POSTS_DISCOVER_FROM_PROFILE and is_profile
        if has_posts_dataset and can_discover_posts:
            try:
                posts = await self.brightdata_client.get_social_posts(
                    platform, cleaned_url, limit=self.max_posts
                )
                if posts:
                    data["posts"] = [
                        {
                            "url": p.url,
                            "title": p.title,
                            "content": p.content[:500] if p.content else None,
                            "date": p.date,
                            "likes": p.likes,
                            "comments": p.comments,
                            "shares": p.shares,
                            "views": p.views,
                            "media_type": p.media_type,
                        }
                        for p in posts
                    ]
            except Exception as e:
                logger.warning(f"Failed to get {platform} posts: {e}")
        elif has_posts_dataset and not can_discover_posts:
            logger.info(f"[{platform}] Skipping posts: profile URL discover not supported or URL is not a profile")

        return data if data else None

    def _get_empty_result(self) -> SocialMediaRaw:
        """返回空结果"""
        return SocialMediaRaw(errors=["Collection failed"])


# 便捷函数
async def collect_social_media(seed: SeedData, config=None) -> SocialMediaRaw:
    """收集社交媒体数据的便捷函数"""
    collector = SocialMediaCollector(config)
    return await collector.collect(seed)
