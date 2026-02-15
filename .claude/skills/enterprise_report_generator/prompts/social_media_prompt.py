"""
社交媒体分析 Prompt

用于将社交媒体原始数据纳入 AI 分析，评估企业的数字化成熟度和社交活跃度。
"""
import json


SOCIAL_MEDIA_SYSTEM = """あなたは企業のソーシャルメディアプレゼンスを分析する専門家です。
収集されたソーシャルメディアデータから、企業のデジタル成熟度と活動状況を評価してください。"""


def build_social_media_section(social_media_data: dict) -> str:
    """将社交媒体数据构建为 AI prompt 的一个章节

    用于嵌入到 signals_prompt 中，作为商机信号分析的补充数据。

    Args:
        social_media_data: SocialMediaRaw.model_dump() 的结果

    Returns:
        prompt 文本
    """
    if not social_media_data:
        return ""

    sections = []
    sections.append("## ソーシャルメディアデータ")
    sections.append("")

    platform_names = {
        "instagram": "Instagram",
        "facebook": "Facebook",
        "tiktok": "TikTok",
        "twitter": "X/Twitter",
        "youtube": "YouTube",
        "reddit": "Reddit",
    }

    for platform_key, platform_label in platform_names.items():
        platform_data = social_media_data.get(platform_key)
        if not platform_data:
            continue

        sections.append(f"### {platform_label}")
        sections.append("")

        # Profile 信息
        profile = platform_data.get("profile")
        if profile:
            if profile.get("name"):
                sections.append(f"- アカウント名: {profile['name']}")
            if profile.get("followers") is not None:
                sections.append(f"- フォロワー数: {profile['followers']}")
            if profile.get("posts_count") is not None:
                sections.append(f"- 投稿数: {profile['posts_count']}")
            if profile.get("description"):
                desc = profile['description'][:200]
                sections.append(f"- プロフィール: {desc}")
            sections.append("")

        # Posts 信息
        posts = platform_data.get("posts", [])
        if posts:
            sections.append(f"最近の投稿 ({len(posts)}件):")
            for i, post in enumerate(posts[:5], 1):
                title = post.get("title") or post.get("content", "")[:100] or "(内容なし)"
                date = post.get("date", "日付不明")
                likes = post.get("likes", 0) or 0
                comments = post.get("comments", 0) or 0
                sections.append(f"  {i}. [{date}] {title}")
                sections.append(f"     いいね: {likes} / コメント: {comments}")
            sections.append("")

    sections.append("""
上記のソーシャルメディアデータを踏まえて、以下を評価に含めてください:
- 企業のデジタル成熟度（ソーシャルメディアの活用度合い）
- 投稿頻度と直近の活動状況（活発か休止中か）
- フォロワー数やエンゲージメントから見る影響力
- 営業アプローチに活用できるシグナル
""")

    return "\n".join(sections)
