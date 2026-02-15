"""
Bright Data API 客户端 (LinkedIn + 社交媒体数据采集)

支持的数据类型:
- LinkedIn: 公司资料 + 员工概览 / 个人详细资料 / 人员搜索
- Instagram: Profiles / Posts / Reels / Comments
- Facebook: Posts (Profile/Group/URL) / Comments / Reels
- TikTok: Profiles / Posts / Comments
- X/Twitter: Profiles / Posts
- YouTube: Profiles / Videos / Comments
- Reddit: Posts / Comments
"""
import httpx
import logging
from typing import Optional, Any
from dataclasses import dataclass, field

from ..config import get_config

logger = logging.getLogger(__name__)


@dataclass
class LinkedInEmployee:
    """LinkedIn 员工概览数据"""
    name: str
    title: str
    linkedin_url: Optional[str] = None
    profile_image: Optional[str] = None


@dataclass
class LinkedInCompanyProfile:
    """LinkedIn 公司资料"""
    name: str
    linkedin_url: str
    description: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    headquarters: Optional[str] = None
    founded: Optional[str] = None
    website: Optional[str] = None
    employees: list[LinkedInEmployee] = None

    def __post_init__(self):
        if self.employees is None:
            self.employees = []


@dataclass
class LinkedInPersonProfile:
    """LinkedIn 个人详细资料"""
    name: str
    linkedin_url: str
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    experience: list[dict] = None
    education: list[dict] = None
    skills: list[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    def __post_init__(self):
        if self.experience is None:
            self.experience = []
        if self.education is None:
            self.education = []
        if self.skills is None:
            self.skills = []


@dataclass
class SocialProfile:
    """社交媒体账号资料"""
    platform: str  # instagram, facebook, tiktok, twitter, youtube, reddit
    url: str
    name: Optional[str] = None
    username: Optional[str] = None
    description: Optional[str] = None
    followers: Optional[int] = None
    following: Optional[int] = None
    posts_count: Optional[int] = None
    verified: Optional[bool] = None
    profile_image: Optional[str] = None
    external_url: Optional[str] = None
    raw_data: Optional[dict] = None


@dataclass
class SocialPost:
    """社交媒体帖子/视频"""
    platform: str
    url: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    date: Optional[str] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    views: Optional[int] = None
    media_type: Optional[str] = None  # image, video, text, reel
    raw_data: Optional[dict] = None


class BrightDataClient:
    """Bright Data API 客户端

    通过 Bright Data 的 Web Scraper API 获取 LinkedIn 数据。
    """

    # Bright Data Web Scraper API 端点
    BASE_URL = "https://api.brightdata.com/datasets/v3/trigger"

    # === LinkedIn 数据集 ID ===
    DATASET_COMPANY_PROFILE = "gd_l1vikfnt1wgvvqz95w"  # LinkedIn Company Profile
    DATASET_PERSON_PROFILE = "gd_l1viktl72bvl7bjuj0"   # LinkedIn Person Profile
    DATASET_PEOPLE_SEARCH = "gd_l1viktl72bvl7bjv1u"    # LinkedIn People Search

    # === 社交媒体数据集 ID ===
    # Instagram
    DATASET_INSTAGRAM_PROFILES = "gd_l1vikfch901nx3by4"
    DATASET_INSTAGRAM_POSTS = "gd_lk5ns7kz21pck8jpis"
    DATASET_INSTAGRAM_REELS = "gd_lyclm20il4r5helnj"
    DATASET_INSTAGRAM_COMMENTS = "gd_ltppn085pokosxh13"
    # Facebook
    DATASET_FACEBOOK_POSTS_PROFILE = "gd_lkaxegm826bjpoo9m5"
    DATASET_FACEBOOK_POSTS_GROUP = "gd_lz11l67o2cb3r0lkj3"
    DATASET_FACEBOOK_POSTS_URL = "gd_lyclm1571iy3mv57zw"
    DATASET_FACEBOOK_COMMENTS = "gd_lkay758p1eanlolqw8"
    DATASET_FACEBOOK_REELS = "gd_lyclm3ey2q6rww027t"
    # TikTok
    DATASET_TIKTOK_PROFILES = "gd_l1villgoiiidt09ci"
    DATASET_TIKTOK_POSTS = "gd_lu702nij2f790tmv9h"
    DATASET_TIKTOK_COMMENTS = "gd_lkf2st302ap89utw5k"
    # X/Twitter
    DATASET_TWITTER_PROFILES = "gd_lwxmeb2u1cniijd7t4"
    DATASET_TWITTER_POSTS = "gd_lwxkxvnf1cynvib9co"
    # YouTube
    DATASET_YOUTUBE_PROFILES = "gd_lk538t2k2p1k3oos71"
    DATASET_YOUTUBE_VIDEOS = "gd_lk56epmy2i5g7lzu0k"
    DATASET_YOUTUBE_COMMENTS = "gd_lk9q0ew71spt1mxywf"
    # Reddit
    DATASET_REDDIT_POSTS = "gd_lvz8ah06191smkebj4"
    DATASET_REDDIT_COMMENTS = "gd_lvzdpsdlw09j6t702"

    # 平台 → Profile Dataset ID 映射
    PLATFORM_PROFILE_DATASETS = {
        "instagram": DATASET_INSTAGRAM_PROFILES,
        "tiktok": DATASET_TIKTOK_PROFILES,
        "twitter": DATASET_TWITTER_PROFILES,
        "youtube": DATASET_YOUTUBE_PROFILES,
    }

    # 平台 → Posts Dataset ID 映射
    PLATFORM_POSTS_DATASETS = {
        "instagram": DATASET_INSTAGRAM_POSTS,
        "facebook": DATASET_FACEBOOK_POSTS_URL,
        "tiktok": DATASET_TIKTOK_POSTS,
        "twitter": DATASET_TWITTER_POSTS,
        "youtube": DATASET_YOUTUBE_VIDEOS,
        "reddit": DATASET_REDDIT_POSTS,
    }

    def __init__(self, config=None):
        self.config = config or get_config()
        self.api_key = self.config.brightdata.api_key
        self.user_id = self.config.brightdata.user_id
        self.timeout = self.config.brightdata.timeout
        self.max_retries = self.config.brightdata.max_retries

    def _get_headers(self) -> dict:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _make_request(
        self,
        dataset_id: str,
        inputs: list[dict],
        format: str = "json",
        max_wait_seconds: int = 120
    ) -> Optional[dict]:
        """发送数据采集请求 (异步模式)

        Bright Data API 工作流程:
        1. 触发采集 → 获得 snapshot_id
        2. 轮询状态直到 ready
        3. 下载结果

        Args:
            dataset_id: 数据集 ID
            inputs: 输入参数列表
            format: 输出格式
            max_wait_seconds: 最大等待时间

        Returns:
            API 响应数据
        """
        import asyncio

        if not self.api_key:
            logger.error("Bright Data API key not configured")
            return None

        # Step 1: 触发采集
        trigger_url = f"{self.BASE_URL}?dataset_id={dataset_id}&format={format}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    trigger_url,
                    headers=self._get_headers(),
                    json=inputs
                )

                if response.status_code == 401:
                    logger.error("Bright Data authentication failed")
                    return None
                elif response.status_code != 200:
                    logger.error(f"Bright Data trigger error: {response.status_code} - {response.text}")
                    return None

                trigger_result = response.json()
                snapshot_id = trigger_result.get("snapshot_id")

                if not snapshot_id:
                    logger.error(f"No snapshot_id in response: {trigger_result}")
                    return None

                logger.info(f"Triggered collection, snapshot_id: {snapshot_id}")

                # Step 2: 轮询状态
                progress_url = f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}"
                poll_interval = 3  # 秒
                waited = 0

                while waited < max_wait_seconds:
                    await asyncio.sleep(poll_interval)
                    waited += poll_interval

                    status_response = await client.get(
                        progress_url,
                        headers=self._get_headers()
                    )

                    if status_response.status_code != 200:
                        logger.warning(f"Progress check failed: {status_response.status_code}")
                        continue

                    status_data = status_response.json()
                    status = status_data.get("status")
                    logger.debug(f"Snapshot {snapshot_id} status: {status}")

                    if status == "ready":
                        # Step 3: 下载结果
                        download_url = f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}?format={format}"
                        download_response = await client.get(
                            download_url,
                            headers=self._get_headers()
                        )

                        if download_response.status_code == 200:
                            return download_response.json()
                        else:
                            logger.error(f"Download failed: {download_response.status_code} - {download_response.text}")
                            return None

                    elif status == "failed":
                        logger.error(f"Snapshot collection failed: {status_data}")
                        return None

                logger.error(f"Timeout waiting for snapshot {snapshot_id} (waited {waited}s)")
                return None

        except httpx.TimeoutException:
            logger.error("Request timeout")
            return None
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None

    async def get_company_profile(self, linkedin_url: str) -> Optional[LinkedInCompanyProfile]:
        """获取公司资料及员工概览

        Args:
            linkedin_url: 公司 LinkedIn URL

        Returns:
            LinkedInCompanyProfile 或 None
        """
        logger.info(f"Fetching LinkedIn company profile: {linkedin_url}")

        inputs = [{"url": linkedin_url}]
        result = await self._make_request(self.DATASET_COMPANY_PROFILE, inputs)

        if not result or not isinstance(result, list) or len(result) == 0:
            return None

        data = result[0] if isinstance(result, list) else result

        # 解析员工列表
        # Bright Data 返回字段: title=名字, subtitle=职位, link=URL, img=头像
        employees = []
        raw_employees = data.get("employees", []) or []
        for emp in raw_employees[:self.config.brightdata.max_employees_per_request]:
            employees.append(LinkedInEmployee(
                name=emp.get("title", ""),  # Bright Data 用 title 字段存储名字
                title=emp.get("subtitle", ""),  # subtitle 才是职位
                linkedin_url=emp.get("link"),  # link 字段是 LinkedIn URL
                profile_image=emp.get("img")  # img 字段是头像
            ))

        return LinkedInCompanyProfile(
            name=data.get("name", ""),
            linkedin_url=linkedin_url,
            description=data.get("description"),
            industry=data.get("industry"),
            company_size=data.get("company_size") or data.get("size"),
            headquarters=data.get("headquarters"),
            founded=data.get("founded"),
            website=data.get("website"),
            employees=employees
        )

    async def get_person_profile(self, linkedin_url: str) -> Optional[LinkedInPersonProfile]:
        """获取个人详细资料

        Args:
            linkedin_url: 个人 LinkedIn URL

        Returns:
            LinkedInPersonProfile 或 None
        """
        logger.info(f"Fetching LinkedIn person profile: {linkedin_url}")

        inputs = [{"url": linkedin_url}]
        result = await self._make_request(self.DATASET_PERSON_PROFILE, inputs)

        if not result or not isinstance(result, list) or len(result) == 0:
            return None

        data = result[0] if isinstance(result, list) else result

        return LinkedInPersonProfile(
            name=data.get("name", ""),
            linkedin_url=linkedin_url,
            title=data.get("title") or data.get("headline"),
            company=data.get("company") or data.get("current_company"),
            location=data.get("location"),
            summary=data.get("summary") or data.get("about"),
            experience=data.get("experience", []),
            education=data.get("education", []),
            skills=data.get("skills", []),
            email=data.get("email"),
            phone=data.get("phone")
        )

    # ================================================================
    # 社交媒体采集方法
    # ================================================================

    async def get_social_profile(
        self,
        platform: str,
        url: str,
    ) -> Optional[SocialProfile]:
        """获取社交媒体主页资料

        Args:
            platform: 平台名称 (instagram, tiktok, twitter, youtube)
            url: 社交主页 URL

        Returns:
            SocialProfile 或 None
        """
        dataset_id = self.PLATFORM_PROFILE_DATASETS.get(platform)
        if not dataset_id:
            logger.warning(f"No profile dataset for platform: {platform}")
            return None

        logger.info(f"Fetching {platform} profile: {url}")
        inputs = [{"url": url}]
        result = await self._make_request(dataset_id, inputs)

        if not result or not isinstance(result, list) or len(result) == 0:
            return None

        data = result[0] if isinstance(result, list) else result
        return self._parse_social_profile(platform, url, data)

    async def get_social_posts(
        self,
        platform: str,
        url: str,
        limit: int = 5,
    ) -> list[SocialPost]:
        """获取社交媒体帖子/视频列表

        Args:
            platform: 平台名称 (instagram, facebook, tiktok, twitter, youtube, reddit)
            url: 主页 URL 或搜索关键词
            limit: 返回数量限制

        Returns:
            SocialPost 列表
        """
        dataset_id = self.PLATFORM_POSTS_DATASETS.get(platform)
        if not dataset_id:
            logger.warning(f"No posts dataset for platform: {platform}")
            return []

        logger.info(f"Fetching {platform} posts: {url} (limit={limit})")
        # 只发送 URL，不发送 num_of_posts（部分平台不支持该参数会返回400）
        inputs = [{"url": url}]
        result = await self._make_request(dataset_id, inputs)

        if not result:
            return []

        results = result if isinstance(result, list) else [result]
        posts = []
        for item in results[:limit]:
            if isinstance(item, dict):
                post = self._parse_social_post(platform, item)
                if post:
                    posts.append(post)

        return posts

    def _parse_social_profile(
        self, platform: str, url: str, data: dict
    ) -> SocialProfile:
        """解析社交媒体主页数据为统一格式"""
        # 各平台字段映射（BrightData 返回字段不同）
        followers_keys = ["followers", "follower_count", "subscribers", "subscriber_count"]
        following_keys = ["following", "following_count", "friends_count"]
        posts_keys = ["posts_count", "media_count", "video_count", "statuses_count"]
        name_keys = ["name", "full_name", "display_name", "title"]
        username_keys = ["username", "screen_name", "handle", "custom_url"]
        desc_keys = ["description", "biography", "bio", "about"]

        def _first_val(keys):
            for k in keys:
                v = data.get(k)
                if v is not None:
                    return v
            return None

        return SocialProfile(
            platform=platform,
            url=url,
            name=_first_val(name_keys),
            username=_first_val(username_keys),
            description=_first_val(desc_keys),
            followers=_first_val(followers_keys),
            following=_first_val(following_keys),
            posts_count=_first_val(posts_keys),
            verified=data.get("verified") or data.get("is_verified"),
            profile_image=data.get("profile_image") or data.get("profile_pic_url") or data.get("avatar"),
            external_url=data.get("external_url") or data.get("website"),
            raw_data=data,
        )

    def _parse_social_post(self, platform: str, data: dict) -> Optional[SocialPost]:
        """解析社交媒体帖子为统一格式"""
        likes_keys = ["likes", "like_count", "digg_count", "favorite_count"]
        comments_keys = ["comments", "comment_count", "comments_count", "reply_count"]
        shares_keys = ["shares", "share_count", "retweet_count", "reposts"]
        views_keys = ["views", "view_count", "play_count", "video_view_count"]
        content_keys = ["text", "content", "caption", "description", "body"]
        title_keys = ["title", "heading"]
        date_keys = ["date", "created_at", "timestamp", "published_at", "upload_date"]

        def _first_val(keys):
            for k in keys:
                v = data.get(k)
                if v is not None:
                    return v
            return None

        return SocialPost(
            platform=platform,
            url=data.get("url") or data.get("post_url") or data.get("link"),
            title=_first_val(title_keys),
            content=_first_val(content_keys),
            date=str(_first_val(date_keys)) if _first_val(date_keys) else None,
            likes=_first_val(likes_keys),
            comments=_first_val(comments_keys),
            shares=_first_val(shares_keys),
            views=_first_val(views_keys),
            media_type=data.get("media_type") or data.get("type"),
            raw_data=data,
        )

    # ================================================================
    # LinkedIn 采集方法
    # ================================================================

    async def search_people(
        self,
        company_name: str,
        keywords: Optional[str] = None,
        title_filter: Optional[str] = None,
        limit: int = 20
    ) -> list[LinkedInEmployee]:
        """搜索公司员工

        Args:
            company_name: 公司名称
            keywords: 搜索关键词
            title_filter: 职位过滤
            limit: 返回数量限制

        Returns:
            员工列表
        """
        logger.info(f"Searching LinkedIn people at {company_name}")

        # 构建搜索查询
        query_parts = [company_name]
        if keywords:
            query_parts.append(keywords)
        if title_filter:
            query_parts.append(f"title:{title_filter}")

        inputs = [{
            "keyword": " ".join(query_parts),
            "limit": limit
        }]

        result = await self._make_request(self.DATASET_PEOPLE_SEARCH, inputs)

        if not result:
            return []

        employees = []
        results = result if isinstance(result, list) else [result]

        for data in results[:limit]:
            if isinstance(data, dict):
                employees.append(LinkedInEmployee(
                    name=data.get("name", ""),
                    title=data.get("title", ""),
                    linkedin_url=data.get("linkedin_url") or data.get("profile_url"),
                    profile_image=data.get("profile_image")
                ))

        return employees


# 便捷函数
async def get_company_linkedin_data(linkedin_url: str) -> Optional[LinkedInCompanyProfile]:
    """获取公司 LinkedIn 数据的便捷函数"""
    client = BrightDataClient()
    return await client.get_company_profile(linkedin_url)


async def get_person_linkedin_data(linkedin_url: str) -> Optional[LinkedInPersonProfile]:
    """获取个人 LinkedIn 数据的便捷函数"""
    client = BrightDataClient()
    return await client.get_person_profile(linkedin_url)


async def get_social_profile_data(platform: str, url: str) -> Optional[SocialProfile]:
    """获取社交媒体主页数据的便捷函数"""
    client = BrightDataClient()
    return await client.get_social_profile(platform, url)


async def get_social_posts_data(platform: str, url: str, limit: int = 5) -> list[SocialPost]:
    """获取社交媒体帖子的便捷函数"""
    client = BrightDataClient()
    return await client.get_social_posts(platform, url, limit)
