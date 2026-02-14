# 企业营业报告自动生成系统

Enterprise Report Generator v0.2 - 面向 B2B 销售团队的企业情报报告自动生成系统。

输入企业种子数据（名称、法人番号、官网 URL），系统自动从多个数据源采集信息，通过 AI 分析生成三层结构化 JSON 报告，供销售人员快速了解目标企业。

## 功能特点

- **多源并行采集**: 并行采集来自 gBizINFO、Serper (Google Search)、LinkedIn (Bright Data)、企业官网等多个数据源
- **AI 智能分析**: 使用 Gemini AI (`gemini-3-pro-preview`) 生成结构化的三层报告
- **LinkedIn 深度采集**: 通过 Bright Data MCP Server 获取公司员工列表，AI 筛选关键决策人，采集深度个人资料（简介、技能、LinkedIn URL）
- **质量检查**: 自动化质量评分和数据验证（满分 100 分）
- **智能缓存**: 分级 TTL 缓存策略，减少重复 API 调用
- **优雅降级**: 单个数据源失败不影响整体流程，系统持续运行

## 报告结构

生成的报告包含三层结构:

| 层级 | 内容 | 描述 |
|------|------|------|
| **Layer 1** | 基本信息 | 企业名称、法人番号、代表人、员工数、业务概要、主要产品、行业标签 |
| **Layer 2** | 销售指南 | 销售难度评估、组织结构、关键人物、接触策略、最佳时机 |
| **Layer 3** | 商机信号 | 商机分数、近期新闻、融资记录、招聘信号、投资意向 |

## 系统架构

```
种子数据 (公司名/法人番号/URL)
        │
        ▼
  ┌─────────────────────────────────────┐
  │         并行数据采集 (asyncio)        │
  │                                     │
  │  BasicInfoCollector   ──→ gBizINFO + 官网爬取
  │  SalesIntelCollector  ──→ Serper搜索 + LinkedIn
  │  SignalCollector      ──→ 新闻/融资/招聘搜索
  └─────────────────────────────────────┘
        │
        ▼
  ┌─────────────────────────────────────┐
  │         AI 分析 (Gemini API)         │
  │                                     │
  │  Layer 1: 基本信息结构化              │
  │  Layer 2: 销售策略 + 关键人物分析      │
  │  Layer 3: 商机信号评估               │
  └─────────────────────────────────────┘
        │
        ▼
  ┌─────────────────────────────────────┐
  │         质量检查 & 输出               │
  │  QualityChecker → JSON Report       │
  └─────────────────────────────────────┘
```

## 快速开始

### 环境要求

- Python 3.11+
- Crawl4AI 浏览器（首次使用需安装）

### 1. 安装依赖

```bash
cd enterprise_report_generator
pip install -r requirements.txt

# 安装 Crawl4AI 浏览器 (首次使用)
crawl4ai-setup
```

### 2. 配置环境变量

创建 `.env` 文件:

```bash
# 必需
SERPER_API_KEY=your_serper_api_key
GEMINI_API_KEY=your_gemini_api_key

# 可选 (政府数据 API)
GBIZINFO_API_TOKEN=your_gbizinfo_token

# 可选 (LinkedIn 深度采集)
BRIGHT_DATA_API_KEY=your_brightdata_api_key
BRIGHT_DATA_USER_ID=your_brightdata_user_id
```

### 3. 运行

**命令行方式:**

```bash
python -m enterprise_report_generator.main \
  --company "Sparticle株式会社" \
  --number "4120001222866" \
  --url "https://www.sparticle.com/ja"
```

**Python 代码方式:**

```python
import asyncio
from enterprise_report_generator import generate_report

async def main():
    report, quality = await generate_report(
        company_name="Sparticle株式会社",
        corporate_number="4120001222866",
        website_url="https://www.sparticle.com/ja"
    )

    print(f"质量分数: {quality.score}")
    print(report.to_json(indent=2))

asyncio.run(main())
```

## 命令行参数

| 参数 | 缩写 | 必需 | 描述 |
|------|------|------|------|
| `--company` | `-c` | 是 | 企业名称 |
| `--number` | `-n` | 是 | 法人番号 (13位) |
| `--url` | `-u` | 是 | 官网 URL |
| `--address` | `-a` | 否 | 地址 |
| `--no-cache` | - | 否 | 不使用缓存 |
| `--no-save` | - | 否 | 不保存到文件 |
| `--output` | `-o` | 否 | 指定输出文件路径 |

## 项目结构

```
enterprise_report_generator/
├── __init__.py               # 包入口 (v0.2)
├── main.py                   # 主入口 & CLI
├── config.py                 # 配置管理 (dataclass)
├── requirements.txt          # 依赖
│
├── collectors/               # 数据收集器 (并行执行)
│   ├── base_collector.py     # 收集器基类
│   ├── basic_info_collector.py    # 基本信息 (gBizINFO + 官网爬取)
│   ├── sales_intel_collector.py   # 销售情报 (搜索 + 团队页面)
│   ├── signal_collector.py        # 商机信号 (新闻/融资/招聘)
│   └── linkedin_collector.py      # LinkedIn 深度采集 (Bright Data)
│
├── analyzers/                # AI 分析器
│   └── ai_analyzer.py        # Gemini AI 分析引擎 (三层报告生成)
│
├── validators/               # 验证器
│   └── quality_checker.py    # 质量检查 & 评分
│
├── models/                   # 数据模型
│   ├── report_schema.py      # Pydantic v2 模型 (SeedData, EnterpriseReport 等)
│   └── tag_vocabulary.py     # 行业/企业标签词库
│
├── prompts/                  # AI Prompts
│   ├── basic_info_prompt.py       # 基本信息提取
│   ├── sales_approach_prompt.py   # 销售策略分析 (含 LinkedIn 数据)
│   ├── signals_prompt.py          # 商机信号识别
│   └── linkedin_filter_prompt.py  # 关键人物筛选
│
├── utils/                    # 工具类
│   ├── serper_client.py      # Serper 搜索 API
│   ├── gbizinfo_client.py    # gBizINFO 政府 API
│   ├── gemini_client.py      # Gemini AI API
│   ├── brightdata_client.py  # Bright Data MCP Server (LinkedIn)
│   └── cache.py              # 文件缓存 (分级 TTL)
│
└── tests/                    # 测试
    ├── test_e2e.py           # 端到端集成测试
    └── test_linkedin.py      # LinkedIn 模块测试
```

## API Keys 获取

### Serper API (必需)
- 注册: https://serper.dev
- 免费额度: 2500 次/月

### Gemini API (必需)
- 注册: https://aistudio.google.com/apikey
- 免费额度: 充足

### gBizINFO API (可选)
- 注册: https://info.gbiz.go.jp/api/
- 日本政府企业数据库，免费

### Bright Data API (可选，用于 LinkedIn)
- 注册: https://brightdata.com
- 付费服务，按请求计费

## 测试

```bash
# 运行 LinkedIn 模块测试
python -m enterprise_report_generator.tests.test_linkedin

# 运行端到端测试
python -m enterprise_report_generator.tests.test_e2e
```

## 输出示例

报告输出为 JSON 格式，保存在 `output/` 目录:

```json
{
  "meta": {
    "report_id": "uuid",
    "generated_at": "2026-02-05T00:53:21",
    "quality_score": 100
  },
  "layer1_basic_info": {
    "company_name": "Sparticle株式会社",
    "corporate_number": "4120001222866",
    "employee_count": {"value": 10, "source": "gBizINFO"},
    "capital": {"value": 100000000, "currency": "JPY"},
    "business_overview": "...",
    "main_products": [...],
    "tags": {"industry": [...], "company_type": [...]}
  },
  "layer2_sales_approach": {
    "summary": {
      "difficulty": 2,
      "recommended_channel": "LinkedIn DM"
    },
    "key_persons": [
      {
        "name": "Jeffery Jin (金田 達也)",
        "title": "CEO/Founder",
        "confidence": "high",
        "source": "linkedin",
        "linkedin_url": "https://jp.linkedin.com/in/jeffery-fj/en",
        "linkedin_summary": "Veteran in Software industry...",
        "skills": ["SaaS", "Android OS", "Startups", "Generative AI"]
      }
    ]
  },
  "layer3_signals": {
    "opportunity_score": {"score": 88},
    "recent_news": [...],
    "hiring_signals": [...]
  }
}
```

## 配置选项

在 `config.py` 中可以调整:

| 配置项 | 默认值 | 描述 |
|--------|--------|------|
| `cache.enabled` | `True` | 是否启用缓存 |
| `cache.basic_info_ttl` | 30天 | 基本信息缓存时间 |
| `cache.search_results_ttl` | 24小时 | 搜索结果缓存时间 |
| `cache.linkedin_ttl` | 7天 | LinkedIn 数据缓存时间 |
| `crawler.delay_between_requests` | 2.0秒 | 爬虫请求间隔 |
| `brightdata.max_employees_per_request` | 50 | 单次获取最大员工数 |
| `brightdata.max_key_persons` | 10 | LinkedIn 关键人物最大数量 |
| `gemini.model_name` | `gemini-3-pro-preview` | Gemini 模型名称 |
| `gemini.temperature` | 0.3 | AI 输出稳定性 (越低越稳定) |

## 技术栈

| 组件 | 技术 | 用途 |
|------|------|------|
| 语言 | Python 3.11+ | 主开发语言 |
| 数据验证 | Pydantic v2 | 类型安全 & JSON Schema |
| 官网爬取 | Crawl4AI | 企业官网内容提取 |
| 搜索引擎 | Serper API | Google 搜索结果 |
| AI 分析 | Gemini API | 报告生成 & 数据分析 |
| 政府数据 | gBizINFO API | 日本法人登记数据 |
| LinkedIn | Bright Data MCP Server | 员工 & 联系人信息 |
| HTTP 客户端 | httpx | 异步 HTTP 请求 |

## 注意事项

1. **API 限制**: 注意各 API 的调用频率限制
2. **LinkedIn 采集**: 需要 Bright Data 付费账户，按请求计费
3. **缓存清理**: 缓存文件在 `cache/` 目录
4. **日语优化**: 系统针对日本企业优化，搜索关键词和 Prompt 均支持日语
5. **数据溯源**: 所有数据点均包含来源 URL 和采集时间戳

## 故障排除

### Crawl4AI 浏览器错误
```bash
# 重新安装浏览器
crawl4ai-setup
```

### API 超时
- 检查网络连接
- 增加 `config.py` 中的 `timeout` 值

### LinkedIn 采集失败
- 确认 `BRIGHT_DATA_API_KEY` 和 `BRIGHT_DATA_USER_ID` 配置正确
- 检查 Bright Data 账户余额
- 注意 Bright Data API 返回的字段映射: `title` 是员工名字，`subtitle` 才是职位

### 质量分数低
- 检查各数据源是否正常返回
- 确认 Gemini API key 有效
- 查看日志中的 WARNING 信息定位问题

## 开发路线

- [x] 基本信息采集 (gBizINFO + 官网)
- [x] 销售情报采集 (搜索 + 团队页面)
- [x] 商机信号采集 (新闻/融资/招聘)
- [x] LinkedIn 深度采集 & 关键人物筛选
- [x] 三层 AI 分析报告生成
- [ ] 新闻全文深度采集 (设计完成，待实现)
- [ ] FastAPI 服务封装
- [ ] Gemini 筛选 Prompt 优化

## 许可证

MIT License
