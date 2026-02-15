# Enterprise Report
> 企业营业报告生成记录
> 更新：2026-02-15-210753

## 当前状态
累计生成 5 份报告

## 生成记录

| # | 企業名 | 质量分数 | 生成时间 | 来源 | 备注 |
|---|--------|---------|---------|------|------|
| 1 | 株式会社ギークフィード | 95 | 2026-02-14-214500 | 関西匹配 | |
| 2 | 株式会社ジーシー | 95 | 2026-02-14-214824 | 東京SaaS匹配 | 同名齿科大厂数据混入 |
| 3 | 株式会社HRBrain | 82 | 2026-02-14-225500 | 手動調査（HR Tech） | Python模块未构建，手动生成 |
| 4 | アイオライト株式会社 | 60 | 2026-02-15-111725 | 手動調査 | 商机信号AI分析因Gemini超时失败；LinkedIn匹配到同名印度IT企業已排除 |
| 5 | 株式会社佐藤電機製作所 | 90 | 2026-02-15-210753 | 手動調査 | 社交媒体采集首次启用：IG/X/YouTube profile成功；posts采集因API参数bug失败（已修复） |

## 核心文件
- output/{企業名}/ — 报告输出目录（6个MD文件）
- .claude/skills/enterprise-report-generator/ — skill代码

## Gotchas
- 同名企业数据混入：搜索结果可能包含同名大企业的数据（如ジーシー=齿科大厂），Gemini会自动识别并标注
- 报告生成耗时2-5分钟/企业，超时不要重试，等待完成
- BrightData社交媒体posts API：不发送num_of_posts参数（部分平台不支持会返回400）
- Twitter/Reddit posts端点不支持从profile URL发现帖子，只有Instagram/TikTok/YouTube支持
- 搜索结果URL需清洗：去查询参数、TikTok视频URL转profile URL
