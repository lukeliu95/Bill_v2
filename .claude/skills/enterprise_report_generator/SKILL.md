---
name: enterprise-report-generator
description: |
  对目标企业生成深度营业报告。输入企业名、法人番号、官网URL，
  自动采集基本信息、销售情报、商机信号、社交媒体数据，经 AI 分析后输出 Markdown 报告。
  报告保存至 output/{企業名}/ 目录。

  触发场景：用户说"帮我生成报告"、"调查一下XX公司"、"出一份营业报告"时使用此技能。
---

# Enterprise Report Generator

对目标企业生成深度营业报告（基本信息 + 销售情报 + 商机信号 + 社交媒体 + AI 分析）。

## 运行方式

通过 Bash 工具执行 Python 模块：

```bash
PYTHONPATH="/Users/lukeliu/Desktop/Cline/Bill_v2/.claude/skills:$PYTHONPATH" \
  python3 -m enterprise_report_generator.main \
    --company "企业名称" \
    --number "法人番号" \
    --url "官网URL"
```

### 参数说明

| 参数 | 必须 | 说明 |
|------|------|------|
| `--company` / `-c` | 是 | 企业名称 |
| `--number` / `-n` | 是 | 法人番号（13位） |
| `--url` / `-u` | 是 | 官网 URL |
| `--address` / `-a` | 否 | 地址 |
| `--no-cache` | 否 | 不使用缓存 |
| `--no-save` | 否 | 不保存到文件 |
| `--output` / `-o` | 否 | 指定输出文件路径 |

### 可选参数示例

```bash
# 指定地址 + 不使用缓存
PYTHONPATH="/Users/lukeliu/Desktop/Cline/Bill_v2/.claude/skills:$PYTHONPATH" \
  python3 -m enterprise_report_generator.main \
    --company "株式会社HRBrain" \
    --number "3010401123536" \
    --url "https://www.hrbrain.co.jp/" \
    --address "東京都品川区" \
    --no-cache
```

## 采集能力

| 采集器 | 数据源 | 采集内容 |
|--------|--------|----------|
| BasicInfoCollector | gBizINFO + Serper + 官网 | 企业基本信息、事业概要、认证 |
| SalesIntelCollector | Serper + BrightData LinkedIn | 关键人物、组织结构、LinkedIn 员工列表 |
| SignalCollector | Serper + 招聘网站 | 商机评分、采用动向、融资信号、投资意向 |
| SocialMediaCollector | Serper + BrightData | Instagram/X/TikTok/YouTube/Facebook/Reddit 账号+动态 |

### 社交媒体采集详情

通过 Serper 搜索 `"企業名" site:{platform}` 发现各平台账号 URL，再调用 BrightData Web Scraper API 获取 profile 数据。

| 平台 | Profile 采集 | Posts 发现 |
|------|------------|-----------|
| Instagram | 支持 | 支持（从 profile URL 发现） |
| TikTok | 支持 | 支持（从 profile URL 发现） |
| YouTube | 支持 | 支持（从 channel URL 发现） |
| X/Twitter | 支持 | 仅单条推文 URL |
| Facebook | — | 仅单条帖子 URL |
| Reddit | — | 仅单条/subreddit URL |

## 输出

报告保存在项目根目录 `output/{企業名}/` 下：

```
output/{企業名}/
├── report_{timestamp}.md                    — 汇总营业报告
├── people/{timestamp}_人物档案.md            — 关键人物 + 联系方式
├── website/{timestamp}_官网内容.md           — 官网爬取内容
├── social_media/{timestamp}_ソーシャルメディア.md — SNS 账号 + 最近动态
├── signals/{timestamp}_商机信号.md            — 商机评分 + 信号详情
└── basic_info/                               — 基本企业信息
```

## 依赖

需要以下环境变量（配置在项目根目录 `.env` 中）：
- `SERPER_API_KEY` — Serper 搜索 API（必须）
- `GBIZINFO_API_TOKEN` — gBizINFO 企业数据 API（必须）
- `GEMINI_API_KEY` — Gemini AI 分析（必须）
- `BRIGHT_DATA_API_KEY`（可选）— LinkedIn + 社交媒体数据采集
- `BRIGHT_DATA_USER_ID`（可选）— LinkedIn + 社交媒体数据采集

## 数据流

```
输入（企业名 + 法人番号 + URL）
  ↓
并行采集：基本信息 / 销售情报 / 商机信号 / 社交媒体
  ↓
AI 分析（Gemini）→ 生成营业报告
  ↓
质量检查 → 输出文件
  ↓
更新 .features/enterprise-report/MEMORY.md
```

## 报告生成后的手动深挖

报告生成后，用户可要求进一步深挖联系方式：
1. BrightData LinkedIn Person Profile API → 个人 email/phone
2. BrightData Instagram/X/YouTube Profile → 企业社交详情
3. Google 搜索 → 採用サイト、商务平台、采访文章中的联系人
4. 交叉验证 → 构建推奨コンタクトルート（经营层/现场/采购/HR/SNS）
5. 结果更新到 `output/{企業名}/people/` 人物档案
