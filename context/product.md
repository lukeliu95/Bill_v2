# 产品信息

产品名称：Bill_v2
一句话描述：AI 驱动的客户发现与营业情报系统 — 分析产品，找到客户，深度调研

目标用户：需要找客户的销售人员与市场人员

## 核心功能

### `/find-customer` — 客户画像构建
- 输入层：理解产品 → 竞品分析 → 输出客户画像（ICP）
- 输出层：生成日本市场筛选条件（JSON 格式）
- 最终产出：告诉用户「你的理想客户长什么样」和筛选条件

### `/customer-match` — 客户匹配
- 基于 ICP 画像，在企业数据库中匹配潜在客户
- 三层漏斗查询：硬性条件 → 关键词 → 评分排序
- 输出分层匹配列表（高/中/低）

### `/enterprise-report-generator` — 企业深度报告
- 4个采集器并行：基本信息 / 销售情报 / 商机信号 / 社交媒体
- AI 分析（Gemini）生成营业策略
- 输出：报告 + 人物档案 + 官网内容 + 社交媒体 + 商机信号

### 联系方式深挖（手动触发）
- BrightData API：LinkedIn 个人资料（email/phone）、Instagram/X/YouTube profile
- 多源搜索：採用サイト、商务平台、采访文章、業界団体
- 交叉验证后输出推奨コンタクトルート

## 数据源

| 数据源 | 用途 | API |
|--------|------|-----|
| gBizINFO | 企业基本信息（法人番号、代表者、従業員数） | REST API |
| Serper | Google 搜索（竞品、人物、商机信号、社交账号发现） | REST API |
| BrightData | LinkedIn（公司+个人）、Instagram/X/TikTok/YouTube/Reddit | Web Scraper API |
| Gemini | AI 分析（报告生成、信号解读） | Generative AI API |
| 企业数据库 | 日本企业CSV（法人番号、事業内容、カテゴリ） | 本地CSV |

## 输出物

```
output/{企業名}/
├── report_{timestamp}.md          — 汇总营业报告（含 AI 分析）
├── people/{timestamp}_人物档案.md  — 关键人物 + 联系方式 + コンタクトルート
├── website/{timestamp}_官网内容.md — 官网爬取内容
├── social_media/{timestamp}_ソーシャルメディア.md — SNS 账号 + 动态
├── signals/{timestamp}_商机信号.md — 商机评分 + 采用/融资信号
└── basic_info/                    — 基本企业信息
```
