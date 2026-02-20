# Bill_v2 - B2B Sales Intelligence System

Bill_v2 是一个智能化的 B2B 销售情报系统，旨在通过 AI 代理自动化客户发现、匹配和深度调研流程。系统核心包含三个主要 Agent，分别负责 ICP 画像构建、企业数据库匹配和深度营业报告生成。

## 核心功能 (Core Features)

系统通过自然语言交互，基于意图路由到以下三个核心 Skill：

### 1. Find Customer (`/find-customer`)
- **功能**: 分析产品定位，构建理想客户画像 (ICP)。
- **输入**: 官网 URL、产品资料或简单的产品描述。
- **输出**: 结构化的 ICP 画像 (Markdown + JSON)，存储于 `.features/find-customer/data/`。

### 2. Customer Match (`/customer-match`)
- **功能**: 基于 ICP 画像，在企业数据库中筛选和匹配潜在客户。
- **输入**: ICP 画像或筛选指令。
- **输出**: 匹配的企业列表，存储于 `.features/customer-match/data/`。
- **技术**: 使用 SQLite + FTS5 进行千万级企业数据的高效检索。

### 3. Enterprise Report Generator (`/enterprise-report-generator`)
- **功能**: 对目标企业生成深度营业报告 (3层结构)。
- **输入**: 企业名称、法人番号、官网 URL。
- **输出**: 包含基本信息、销售指南、商机信号的深度报告，以及关键联系人挖掘。
- **数据源**: gBizINFO, Serper (Google), LinkedIn (Bright Data), 企业官网。

## 快速开始 (Quick Start)

### 环境要求
- Python 3.11+
- Crawl4AI 浏览器环境

### 1. 安装依赖

```bash
# 安装企业报告生成器的依赖
pip install -r .claude/skills/enterprise_report_generator/requirements.txt

# 安装 Crawl4AI 浏览器 (首次使用)
crawl4ai-setup
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入必要的 API Key：

```bash
cp .env.example .env
```

`.env` 文件中必须配置：
- `SERPER_API_KEY`: 用于 Google 搜索 (https://serper.dev)
- `GEMINI_API_KEY`: 用于 AI 分析 (https://aistudio.google.com/apikey)

可选配置：
- `GBIZINFO_API_TOKEN`: 日本政府企业数据库
- `BRIGHT_DATA_API_KEY`: LinkedIn 深度采集

### 3. 数据准备

确保 `data/` 目录下有企业数据库文件 `enterprises.db`。如果只有 CSV 文件，可以使用脚本导入：

```bash
python scripts/import_csv_to_sqlite.py
```

## 使用指南 (Usage)

### 方式一：自然语言交互 (推荐)

在 IDE 中直接与 AI 助手对话，系统会根据意图自动路由：

- **找客户**: "帮我找做 SaaS 的企业"、"分析这个产品：https://example.com"
- **匹配客户**: "根据刚才的 ICP 匹配一下客户"、"筛选东京都在 50 人以上的 AI 公司"
- **生成报告**: "帮我生成 Sparticle株式会社 的营业报告"、"调查一下这个公司"

### 方式二：命令行工具

#### 1. 企业搜索脚本 (`enterprise_search.py`)

用于快速检索企业数据库：

```bash
# 基于 ICP 文件搜索
python scripts/enterprise_search.py --icp .features/find-customer/data/xxx.md

# 直接指定查询条件
python scripts/enterprise_search.py --query '{"prefectureIds":[13],"minEmployeeNumber":10}' --keywords "AI,SaaS"
```

#### 2. 企业报告生成器

直接运行报告生成模块：

```bash
python -m .claude.skills.enterprise_report_generator.main \
  --company "Sparticle株式会社" \
  --number "4120001222866" \
  --url "https://www.sparticle.com/ja"
```

## 项目结构 (Project Structure)

```
Bill_v2/
├── CLAUDE.md                        # 项目开发指南与意图路由规则
├── .env                             # 环境变量配置（API Key）
│
├── context/                         # 项目上下文文档
│   ├── soul.md                      # Alan 的身份与世界观
│   ├── user.md                      # Luke 的偏好与预算约束
│   └── product.md                   # 产品功能与数据库规格
│
├── .claude/skills/                  # 核心 Skill 实现
│   ├── find-customer/               # ICP 画像构建 Skill
│   │   ├── SKILL.md                 # Skill 说明与执行流程
│   │   └── references/              # 参考数据（産業分類、都道府県等）
│   ├── customer-match/              # 客户匹配 Skill
│   │   └── SKILL.md
│   ├── sales-agent/                 # 统一销售代理 Skill（推荐入口）
│   │   └── SKILL.md
│   └── enterprise_report_generator/ # 企业报告生成 Skill（Python 实现）
│       ├── SKILL.md / README.md
│       ├── main.py                  # 入口：并行调度各采集器
│       ├── config.py                # 全局配置（API Key、超时等）
│       ├── collectors/              # 数据采集层
│       │   ├── basic_info_collector.py      # gBizINFO + 官网基本信息
│       │   ├── sales_intel_collector.py     # LinkedIn + 人物情报
│       │   ├── signal_collector.py          # 商机信号（招聘/投资）
│       │   ├── social_media_collector.py    # SNS 账号 + 动态
│       │   └── contact_discovery_collector.py # 联系方式深挖
│       ├── analyzers/               # AI 分析层（Gemini）
│       ├── renderers/               # Markdown 渲染层
│       ├── exporters/               # 文件导出层
│       ├── models/                  # 数据模型（Schema + Tag词汇表）
│       ├── prompts/                 # Gemini Prompt 模板
│       ├── utils/                   # 工具层（API 客户端）
│       │   ├── brightdata_client.py
│       │   ├── gbizinfo_client.py
│       │   ├── gemini_client.py
│       │   ├── serper_client.py
│       │   └── cache.py             # API 响应本地缓存
│       ├── validators/              # 报告质量检查
│       └── tests/                   # E2E + 单元测试
│
├── .features/                       # 业务数据与模块记忆
│   ├── find-customer/
│   │   ├── MEMORY.md                # 模块运行记忆
│   │   └── data/{timestamp}.md      # ICP 画像（MD + 嵌入 JSON）
│   ├── customer-match/
│   │   ├── MEMORY.md
│   │   └── data/{timestamp}.md      # 匹配企业列表（分层评分）
│   ├── enterprise-report/
│   │   └── MEMORY.md                # 报告生成历史索引
│   └── sales-agent/
│       ├── MEMORY.md
│       └── data/{timestamp}_pipeline.md  # 管线运行状态（支持断点续跑）
│
├── output/                          # 企业报告输出（每家企业独立目录）
│   └── {企業名}/
│       ├── report_{timestamp}.md                       # 汇总营业报告（含 AI 分析）
│       ├── company/{timestamp}_公司信息.md              # 企业基本信息
│       ├── people/{timestamp}_人物档案.md               # 关键人物 + コンタクトルート
│       ├── contacts/{timestamp}_連絡先情報.md           # 联系方式 + 推奨アプローチ
│       ├── website/{timestamp}_官网内容.md              # 官网爬取内容
│       ├── social_media/{timestamp}_ソーシャルメディア.md  # SNS 账号 + 最新动态
│       ├── signals/{timestamp}_商机信号.md              # 商机评分 + 采用/融资信号
│       └── news/{timestamp}_新闻动态.md                # 新闻 + PR TIMES 动态
│
├── scripts/                         # 命令行工具
│   ├── enterprise_search.py         # 企业数据库检索（三层漏斗）
│   └── import_csv_to_sqlite.py      # CSV → SQLite 导入工具
│
├── data/                            # 基础数据（已 .gitignore）
│   ├── enterprises.db               # SQLite 主数据库（579万法人）
│   └── Kihonjoho_UTF-8.csv          # gBizINFO 原始数据
│
├── cache/                           # API 响应缓存（JSON，本地复用）
├── loop/
│   └── state.md                     # 会话运行状态（上次做了什么/待处理）
└── Docs/                            # 设计文档
    ├── enterprise-search-design.md
    └── jp-enterprise-query-directory-design.md
```

## 开发指南

- 详细开发规范请参考 [CLAUDE.md](CLAUDE.md)。
- 报告生成器的详细文档请参考 [.claude/skills/enterprise_report_generator/README.md](.claude/skills/enterprise_report_generator/README.md)。
