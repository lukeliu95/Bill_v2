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
├── .claude/skills/              # 核心技能实现
│   ├── customer-match/          # 客户匹配 Skill
│   ├── enterprise_report_generator/ # 报告生成 Skill (含 Python 源码)
│   └── find-customer/           # ICP 分析 Skill
├── .features/                   # 业务数据与记忆
│   ├── customer-match/data/     # 匹配结果
│   ├── find-customer/data/      # ICP 画像
│   └── enterprise-report/       # 生成的报告记录
├── output/                      # 企业报告输出目录
│   └── {企業名}/                 # 每家企业独立目录
│       ├── report_{timestamp}.md                      # 汇总营业报告（含 AI 分析）
│       ├── company/{timestamp}_公司信息.md             # 企业基本信息
│       ├── people/{timestamp}_人物档案.md              # 关键人物 + 联系方式
│       ├── contacts/{timestamp}_連絡先情報.md          # 联系方式 + 推奨コンタクトルート
│       ├── website/{timestamp}_官网内容.md             # 官网爬取内容
│       ├── social_media/{timestamp}_ソーシャルメディア.md # SNS 账号 + 最新动态
│       ├── signals/{timestamp}_商机信号.md             # 商机评分 + 采用/融资信号
│       └── news/{timestamp}_新闻动态.md               # 新闻 + PR TIMES 动态
├── scripts/                     # 实用脚本
│   ├── enterprise_search.py     # 搜索逻辑实现
│   └── import_csv_to_sqlite.py  # 数据导入工具
├── data/                        # 基础数据 (SQLite DB, CSV)
├── CLAUDE.md                    # 项目开发指南与 Prompt
└── .env                         # 环境变量配置
```

## 开发指南

- 详细开发规范请参考 [CLAUDE.md](CLAUDE.md)。
- 报告生成器的详细文档请参考 [.claude/skills/enterprise_report_generator/README.md](.claude/skills/enterprise_report_generator/README.md)。
