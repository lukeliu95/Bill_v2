# 产品信息

产品名称：Bill_v2
一句话描述：AI 驱动的 B2B 企业搜索与营业情报系统 — 从 579 万法人中精准定位目标客户

目标用户：需要找客户的销售人员与市场人员

## 核心功能

### `/find-customer` — 客户画像构建
- 输入层：理解产品 → 竞品分析 → 输出客户画像（ICP）
- 输出层：生成日本市场筛选条件（JSON 格式）
- 最终产出：告诉用户「你的理想客户长什么样」和筛选条件

### `/customer-match` — 客户匹配（SQLite + FTS5）
- 数据源：`data/enterprises.db`（579万法人，gBizINFO 全量导入）
- 三层漏斗查询：
  - Layer 1: SQL 索引查询（都道府県 + 従業員数 + 資本金 + 設立日）→ 毫秒级
  - Layer 2: 关键词过滤（正向行业词 + 负向硬排除词）→ Python 内存处理
  - Layer 3: 多信号评分排序 → 高/中/低分层输出
- 检索脚本：`python3 scripts/enterprise_search.py --icp <ICP文件>`
- FTS5 全文搜索：`python3 scripts/enterprise_search.py --fts "关键词"`
- 输出：`.features/customer-match/data/YYYY-MM-DD-HHmmss.md`

### 直接企业搜索（不需要 ICP）
- 用户直接描述目标（如"做SaaS給与的企业"）→ SQL/FTS5 直查 + Web 搜索补充
- 适用于：已知目标类型、不需要完整画像分析的场景

### `/enterprise-report-generator` — 企业深度报告
- 4个采集器并行：基本信息 / 销售情报 / 商机信号 / 社交媒体
- AI 分析（Gemini）生成营业策略
- 输出：报告 + 人物档案 + 官网内容 + 社交媒体 + 商机信号

### 联系方式深挖（手动触发）
- BrightData API：LinkedIn 个人资料（email/phone）、Instagram/X/YouTube profile
- 多源搜索：採用サイト、商务平台、采访文章、業界団体
- 交叉验证后输出推奨コンタクトルート

## 企业数据库

### 主数据库：`data/enterprises.db`（SQLite）

由 `data/Kihonjoho_UTF-8.csv`（gBizINFO 全量数据）导入，约 1.55GB。

**数据规模**：5,748,365 法人

**核心字段**：

| 字段 | DB列名 | 用途 |
|------|--------|------|
| 法人番号 | houjin_bangou (PK) | 唯一标识 |
| 商号 | company_name | 企业名匹配 |
| 都道府県 | prefecture / prefecture_code | 地域过滤（索引） |
| 従業員数 | employee_count | 规模过滤（索引） |
| 資本金 | capital | 规模过滤（索引） |
| 設立年月日 | established_date | 成立日过滤（索引） |
| 事業概要 | business_summary | 关键词匹配（FTS5） |
| 事業種目 | business_type | 行业分类（FTS5） |
| 代表者 | representative | 人物信息 |
| 官网 | website | 联系渠道 |

**索引**：
- 结构化：prefecture_code, employee_count, capital, established_date, (prefecture_code + employee_count)
- 全文：FTS5 on company_name + business_summary + business_type

**数据质量**（重要）：
- 事業概要填写率：1.5%（86,341 / 574万）
- 従業員数填写率：2.4%（140,739 / 574万）
- 大部分记录只有法人番号、商号、住所等基本信息
- 新兴 SaaS/IT 企业覆盖不足，需 Web 搜索补充

**重建数据库**：`python3 scripts/import_csv_to_sqlite.py`（约 40 秒）

### 旧数据源（已废弃）
- `data/enterprises_10000.md` — 10,000 条预筛选记录，不再使用

## 外部数据源

| 数据源 | 用途 | API |
|--------|------|-----|
| gBizINFO | 企业基本信息（→ 已导入 SQLite） | REST API / 本地DB |
| Serper | Google 搜索（竞品、人物、商机信号、社交账号发现） | REST API |
| BrightData | LinkedIn（公司+个人）、Instagram/X/TikTok/YouTube/Reddit | Web Scraper API |
| Gemini | AI 分析（报告生成、信号解读） | Generative AI API |

## 输出物

```
output/{企業名}/
├── report_{timestamp}.md                      — 汇总营业报告（含 AI 分析）
├── company/{timestamp}_公司信息.md             — 企业基本信息（gBizINFO + 官网）
├── people/{timestamp}_人物档案.md              — 关键人物 + 联系方式 + コンタクトルート
├── contacts/{timestamp}_連絡先情報.md          — 自动采集的联系方式 + 推奨コンタクトルート
├── website/{timestamp}_官网内容.md             — 官网爬取内容
├── social_media/{timestamp}_ソーシャルメディア.md — SNS 账号 + 最新动态
├── signals/{timestamp}_商机信号.md             — 商机评分 + 采用/融资信号
└── news/{timestamp}_新闻动态.md               — 新闻 + PR TIMES 动态
```
