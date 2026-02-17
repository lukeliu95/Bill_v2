# 日本企业查询方案 - 目录结构设计

> **文档版本**: v1.8
> **创建日期**: 2026-02-16
> **更新日期**: 2026-02-17
> **作者**: Claude Code
> **更新内容**: v1.1 补充 SKILL.md/soul.md 完整示例、工具接口定义、Working Memory 模板、执行流程图；重命名 skills/ → memory/；v1.2 添加数据导入流程；v1.3 企业规模 38万→100万热门企业；v1.4 Working Memory 改为 Session 级（不跨用户共享）；v1.5 统一更新物理存储位置中 working/ 的描述；v1.6 添加 Session 工作目录；v1.7 路径标准化（/app/workspaces/, /app/users/）+ 统一视图概念说明；v1.8 Skill目录改为相对路径 .claude/skills/

---

## 概述

本文档定义了 `jp-enterprise-query` skill 的完整目录结构设计，基于以下设计理念：

1. **极简架构** - SQLite FTS5 + 2 个工具，无需向量数据库
2. **Agent + Toolbox** - Agent 自由组合工具，而非固定 Pipeline
3. **Soul + Working Memory** - Agent = Soul + Working Memory + Scope + Skills + Connectors

---

## 优先级说明（P0 / P1 / P2）

文档中使用的 **【P0】【P1】【P2】** 标记表示文件/功能的开发优先级：

| 优先级 | 含义 | 实施时机 | 示例 |
|-------|------|---------|------|
| **【P0】** | 核心必需 | 第一阶段，必须有 | SKILL.md, soul.md, company-search, company-grep |
| **【P1】** | 重要功能 | 第二阶段，应该有 | guards.yaml, working/, sync_task_state.py |
| **【P2】** | 增强功能 | 第三阶段，可以有 | memory/strategies/, memory/patterns/, memory/pitfalls/ |

### P0 - 核心必需（必须有）

没有这些文件/功能，系统无法运行：

```
├── SKILL.md              【P0】技能入口 - Claude Code 加载此文件激活技能
├── soul.md               【P0】Agent 人格 - 定义 Agent 的驱动力和判断力
├── config/scope.yaml     【P0】管辖范围 - 定义数据路径和允许操作
├── tools/company-search  【P0】结构化查询 - 核心查询工具
├── tools/company-grep    【P0】全文检索 - 核心搜索工具
├── data/schema.yaml      【P0】数据结构 - 字段定义
├── data/enterprises.db   【P0】SQLite 索引 - 查询依赖
├── data/prefecture_map.yaml  【P0】都道府県映射
├── data/companies/       【P0】企业 MD 文件 - 真相源
└── scripts/build_index.py    【P0】构建索引
```

### P1 - 重要功能（应该有）

没有这些文件/功能，系统可以运行但体验不佳：

```
├── config/guards.yaml        【P1】护栏配置 - 限制和保护
├── working/plan.md           【P1】执行计划 - Working Memory
├── working/changelog.md      【P1】行动日志
├── working/budget.md         【P1】预算消耗
├── data/_raw/                【P1】原始数据备份
└── scripts/sync_task_state.py    【P1】Task 同步
```

### P2 - 增强功能（可以有）

这些是锦上添花的功能，可以后续迭代添加：

```
└── memory/                   【Global Memory】经验积累
    ├── strategies/           【P2】搜索策略积累
    ├── patterns/             【P2】最佳实践 - 查询模式
    └── pitfalls/             【P2】失败经验 - 错误警示
```

### 实施建议

```
Phase 1: P0 文件 → 系统可运行
    ↓
Phase 2: P1 文件 → 体验优化
    ↓
Phase 3: P2 文件 → 持续进化
```

---

## 物理存储 vs 逻辑视图

### 物理存储位置（3个目录）

```
1. Skill 目录 (.claude/skills/jp-enterprise-query/)
├── SKILL.md              # 【P0】技能入口文档
├── soul.md               # 【P0】Agent 人格定义
├── config/               # 配置（scope, guards）
├── tools/                # 工具箱（company-search, company-grep）
├── working/              # 【模板目录】⚠️ 仅作格式参考
├── memory/               # Global Memory（经验积累，可提交）
├── data/                 # 企业数据（Project Memory）
│   ├── schema.yaml       # 字段定义
│   ├── prefecture_map.yaml
│   ├── enterprises.db    # SQLite 索引
│   └── companies/        # 100万+ MD 文件
└── scripts/              # 辅助脚本

2. 用户目录 (/app/users/{user_id}/skills/jp-enterprise-query/)
├── preferences.yaml      # 用户偏好
├── favorites.yaml        # 收藏的企业
├── history/              # 查询历史
└── strategies/           # 个人策略

3. Session 工作目录 (/app/workspaces/{sessionId}/working/)  【Session级运行时】
├── plan.md               # 当前执行计划
├── changelog.md          # 本次 Session 行动日志
└── budget.md             # 本次 Session 资源消耗
                          # ⚠️ Session 结束后自动清理
```

### Agent Session 看到的（统一视图）

```
Memory = Soul + Scope + (Global + Personal) + Working + Tools
```

**注意**：这是**概念性**的统一视图，不是程序化的数据结构。

Claude 通过阅读 SKILL.md 和 soul.md 了解自己的能力和人格，
然后按需读取其他文件（config/、memory/、data/），
最终在认知层面形成统一的理解。

**不需要** bootstrap 脚本或预处理程序。

---

## Memory 架构

### 物理存储与逻辑角色

| 物理目录 | 逻辑角色 | 合并顺序 |
|---------|---------|---------|
| `memory/` | Global Knowledge (基础层) | 先加载 |
| `/app/users/{user_id}/` | Personal Override (覆盖层) | 后加载 |
| `working/` | Execution State (动态层) | 运行时 |

### 三种 Memory 的区别

| Memory 类型 | 存什么 | 属于谁 | 持久性 |
|------------|--------|--------|--------|
| **Project Memory** | 事实（什么是真的） | 项目共享 | 长期 |
| **User Memory** | 个人偏好、风格 | 用户个人 | 长期 |
| **Working Memory** | 执行计划（我打算做什么） | Agent Loop | 中短期 |

### Global Memory vs Personal Memory

```
┌─────────────────────────────┐   ┌─────────────────────────────┐
│     Global Memory           │   │     Personal Memory         │
│     (全局记忆)              │   │     (个人记忆)              │
├─────────────────────────────┤   ├─────────────────────────────┤
│ • 位置: memory/ 目录内      │   │ • 位置: 用户目录            │
│ • 管理: Admin 更新          │   │ • 管理: 用户自己更新        │
│ • Git: 提交到仓库           │   │ • Git: 不提交               │
│ • 共享: 所有用户共享        │   │ • 共享: 仅限当前用户        │
│                             │   │                             │
│ 内容:                       │   │ 内容:                       │
│ - 通用搜索策略              │   │ - 用户偏好的查询条件        │
│ - 行业最佳实践              │   │ - 常用筛选组合              │
│ - 常见错误警示              │   │ - 个人收藏的企业            │
│ - 同义词词典                │   │ - 历史查询记录              │
└─────────────────────────────┘   └─────────────────────────────┘
```

---

## 详细目录结构

```
.claude/skills/jp-enterprise-query/
│
├── SKILL.md                      【P0】技能主文档
│                                 - 触发条件、功能说明、使用示例
│                                 - Claude Code 加载此文件激活技能
│
│   ┌─────────────────────────────────────────────────────────────┐
│   │ SKILL.md 完整内容示例:                                       │
│   │                                                             │
│   │ ---                                                         │
│   │ name: jp-enterprise-query                                   │
│   │ description: "日本企業100万社からの高速検索"                    │
│   │ model: sonnet                                               │
│   │ allowed-tools: [Read, Grep, Bash]                           │
│   │ metadata:                                                   │
│   │   trigger: "日本企業を検索/東京のSaaS企業"                     │
│   │   author: "chongming"                                       │
│   │   version: "1.0.0"                                          │
│   │ ---                                                         │
│   │                                                             │
│   │ # 日本企业查询 Skill                                         │
│   │                                                             │
│   │ ## Purpose                                                  │
│   │ 从 100 万家日本企业中快速检索，支持结构化筛选和全文搜索。         │
│   │                                                             │
│   │ ## 可用命令                                                  │
│   │ - company-search: 结构化查询（地域/行业/规模）                 │
│   │ - company-grep: 全文检索（FTS5 + BM25）                      │
│   │                                                             │
│   │ ## Examples                                                 │
│   │ 用户: "帮我找東京做 HR Tech 的初创企业"                       │
│   │ Agent:                                                      │
│   │ 1. company-search --location 東京 --max-employees 50        │
│   │ 2. company-grep "HR Tech OR 人事 OR 採用"                   │
│   │ 3. 取交集 → 返回结果                                         │
│   │                                                             │
│   │ ## Anti-Patterns                                            │
│   │ - 禁止对 data/companies/ 直接 grep -r                        │
│   │ - 禁止返回超过 100 条不分页                                   │
│   └─────────────────────────────────────────────────────────────┘
│
├── soul.md                       【P0】Agent 人格定义
│                                 - Identity: 日本企业检索专家
│                                 - Mission: 高效找到最匹配的企业
│                                 - Drives: 时间/信号/目标驱动
│                                 - Judgment: 准确性 > 数量
│                                 - Initiative: 自动/确认/禁止三级
│                                 - Personality: 日语敬語、简洁
│
│   ┌─────────────────────────────────────────────────────────────┐
│   │ soul.md 完整内容示例:                                        │
│   │                                                             │
│   │ # Soul: 日本企業検索専門家                                    │
│   │                                                             │
│   │ ## Identity                                                 │
│   │ 私は日本企業データの検索スペシャリストです。                    │
│   │ 100万社から、ユーザーのニーズに最適な企業を発見します。           │
│   │                                                             │
│   │ ## Mission                                                  │
│   │ 高精度・高効率の企業検索で、ビジネス開拓を支援する。             │
│   │                                                             │
│   │ ## Drives                                                   │
│   │ 時間駆動: 検索5秒超→条件絞込提案 / 0件→条件緩和再検索          │
│   │ シグナル: 「もっと」→緩和 / 「絞って」→追加 / >1000件→提案     │
│   │ 目標駆動: 精度>90%, 無関係<20%                                │
│   │                                                             │
│   │ ## Judgment                                                 │
│   │ 1. 精度 > 数量（100社良い結果 > 1000社曖昧結果）               │
│   │ 2. 構造化検索を先、全文検索を後                               │
│   │ 3. 不確実 → 確認を求める                                     │
│   │                                                             │
│   │ ## Initiative                                               │
│   │ Level 3（自動）: search/grep実行, 結果整理, 類似提案          │
│   │ Level 2（確認後）: 1000件超表示, 一括取得, Task作成           │
│   │ Level 1（禁止）: grep -r直接, 存在しないフィールド検索         │
│   │                                                             │
│   │ ## Boundaries                                               │
│   │ - 機密情報は扱わない                                         │
│   │ - 公開情報のみ検索対象                                        │
│   │                                                             │
│   │ ## Personality                                              │
│   │ - 日本語: 丁寧語、簡潔                                        │
│   │ - 結果は表形式で見やすく                                      │
│   └─────────────────────────────────────────────────────────────┘
│
├── config/                       【配置目录】
│   ├── scope.yaml               【P0】管辖范围
│   │                            - data_path: ./data
│   │                            - db_path: ./data/enterprises.db
│   │                            - allowed_operations: [search, grep, read]
│   │
│   └── guards.yaml              【P1】护栏配置
│                                - max_results: 1000
│                                - rate_limit: 10/minute
│                                - require_approval: [batch_delete, web_fetch]
│
├── tools/                       【工具箱】Agent 可调用的可执行脚本
│   ├── company-search           【P0】结构化查询
│   │                            - 按行业/地域/规模等字段精确筛选
│   │                            - 直接查询 SQLite enterprises.db
│   │                            - 返回: JSON 格式企业列表
│   │
│   │   ┌─────────────────────────────────────────────────────────┐
│   │   │ company-search 接口定义:                                 │
│   │   │                                                         │
│   │   │ 参数:                                                    │
│   │   │   --location      # 所在地（前缀匹配）東京, 東京都渋谷区   │
│   │   │   --industry      # 行业: SaaS, 製造業, コンサル          │
│   │   │   --sub-industry  # 细分: HR Tech, FinTech              │
│   │   │   --min-employees # 最小员工数                           │
│   │   │   --max-employees # 最大员工数                           │
│   │   │   --min-capital   # 最小资本金（万円）                    │
│   │   │   --funding-stage # 融资: Seed, Series A/B              │
│   │   │   --founded-after # 成立年份起始                         │
│   │   │   --status        # 状态: seed, crawled, enriched       │
│   │   │   --sort          # 排序字段（默认: dr_score）           │
│   │   │   --limit         # 最大返回数（默认: 50）               │
│   │   │   --count         # 仅返回数量                           │
│   │   │   --output        # 格式: table/json/csv                │
│   │   │                                                         │
│   │   │ 输出示例:                                                │
│   │   │ ID             NAME           INDUSTRY  LOCATION   EMP  │
│   │   │ 7010001204947  株式会社Example  SaaS     東京都渋谷区  35 │
│   │   │ Found: 128 companies                                    │
│   │   └─────────────────────────────────────────────────────────┘
│   │
│   └── company-grep             【P0】全文检索
│                                - FTS5 关键词/BM25 语义排序
│                                - 支持日文分词
│                                - 返回: 按相关度排序的企业列表
│
│       ┌─────────────────────────────────────────────────────────┐
│       │ company-grep 接口定义:                                   │
│       │                                                         │
│       │ 参数:                                                    │
│       │   query          # FTS5 查询（支持 AND/OR/NOT/phrase）   │
│       │   -E, --regexp   # 正则表达式（较慢）                     │
│       │   -l, --files-only # 仅输出文件名                        │
│       │   -c, --count    # 仅输出数量                            │
│       │   --top          # 返回前 N 条（默认: 50）               │
│       │                                                         │
│       │ 示例:                                                    │
│       │   company-grep "DX推進 AND 製造業"                       │
│       │   company-grep "AI OR 機械学習" --top 20                │
│       │   company-grep -E "従業員.*[1-4][0-9]名"                │
│       └─────────────────────────────────────────────────────────┘
│
├── working/                     【Working Memory 模板】Session 级运行状态
│   │                            ⚠️ 此目录仅作为格式参考
│   │                            ⚠️ 实际 Working Memory 在 Agent Session 内存中维护
│   │                            ⚠️ 不跨用户/Session 共享
│   │
│   ├── plan.md                  【P1】执行计划模板
│   │                            - 目标、步骤、进度
│   │
│   │   ┌─────────────────────────────────────────────────────────┐
│   │   │ plan.md 模板:                                           │
│   │   │                                                         │
│   │   │ ## Active（正在执行）                                    │
│   │   │ | Task | Status | Started | Notes |                     │
│   │   │ |------|--------|---------|-------|                     │
│   │   │ | 搜索東京HR Tech | executing | 10:30 | 预计50条 |        │
│   │   │                                                         │
│   │   │ ## Watching（等待中）                                    │
│   │   │ | Task | Condition | Created |                          │
│   │   │ |------|-----------|---------|                          │
│   │   │ | 验证CTO联系方式 | 用户确认后 | 10:30 |                   │
│   │   └─────────────────────────────────────────────────────────┘
│   │
│   ├── changelog.md             【P1】行动日志
│   │                            - 每次操作的时间戳和结果
│   │
│   │   ┌─────────────────────────────────────────────────────────┐
│   │   │ changelog.md 模板:                                       │
│   │   │                                                         │
│   │   │ ## 2026-02-16                                           │
│   │   │ ### 10:35 - company-search 执行                          │
│   │   │ - Trigger: 用户请求 "東京のHR Tech企業"                   │
│   │   │ - Action: company-search --location 東京 --max-emp 50   │
│   │   │ - Result: 128 companies, top 50 returned                │
│   │   │ - Duration: 8ms                                         │
│   │   └─────────────────────────────────────────────────────────┘
│   │
│   └── budget.md                【P1】预算消耗
│                                - API 调用次数、成本追踪
│
│       ┌─────────────────────────────────────────────────────────┐
│       │ budget.md 模板:                                          │
│       │                                                         │
│       │ ## 今日消耗                                              │
│       │ | 项目 | 数量 | 成本 |                                    │
│       │ |------|------|------|                                   │
│       │ | company-search | 3 | - |                              │
│       │ | company-grep | 2 | - |                                │
│       │ | LLM tokens | 1,500 | $0.02 |                          │
│       │ | 连续自动操作 | 2/5 | - |                                │
│       │                                                         │
│       │ ## 限制                                                  │
│       │ - 每日最大操作: 100                                       │
│       │ - 连续自动操作: 5                                         │
│       │ - 单次结果上限: 1000                                      │
│       └─────────────────────────────────────────────────────────┘
│
├── memory/                      【Global Memory】经验积累 (可提交)
│   ├── strategies/              【P2】搜索策略
│   │   ├── hr-tech-cto-search.md    # HR Tech CTO 搜索策略
│   │   └── saas-startup-filter.md   # SaaS 初创企业筛选
│   │
│   ├── patterns/                【P2】最佳实践
│   │   ├── efficient-grep.md        # 高效 grep 模式
│   │   └── synonym-expansion.md     # 同义词展开技巧
│   │
│   └── pitfalls/                【P2】失败经验
│       ├── common-mistakes.md       # 常见错误
│       └── data-quality-issues.md   # 数据质量问题
│
├── data/                        【企业数据】真相源
│   ├── schema.yaml              【P0】数据结构定义
│   │                            - frontmatter 字段说明
│   │                            - 字段类型、必填/可选、默认值
│   │
│   ├── enterprises.db           【P0】SQLite FTS5 索引
│   │                            - 可删除，由 build_index.py 重建
│   │                            - companies 表: frontmatter 字段
│   │                            - docs 表: body 全文索引
│   │
│   ├── prefecture_map.yaml      【P0】都道府県映射表
│   │                            - 法人番号第2-3位 → 都道府県名
│   │
│   ├── companies/               【P0】企业 MD 文件（按都道府県分目录）
│   │   ├── 01_北海道/
│   │   ├── 04_宮城県/
│   │   ├── 13_東京都/
│   │   ├── 14_神奈川県/
│   │   ├── 27_大阪府/
│   │   ├── ...                  # 47 个都道府県
│   │   └── 47_沖縄県/
│   │
│   └── _raw/                    【P1】原始数据备份（可删除）
│       └── enterprises_all.md   # 原始管道分隔格式
│
└── scripts/                     【辅助脚本】非 Agent 直接调用
    ├── build_index.py           【P0】构建索引
    ├── convert_raw.py           【P0】数据转换
    ├── sync_task_state.py       【P1】Task 同步
    └── aggregate_results.sh     【P1】结果聚合
```

---

## 用户目录结构（Personal Memory）

```
/app/users/{user_id}/skills/jp-enterprise-query/
│
├── preferences.yaml              # 用户偏好设置
│   default_filters:
│     location: 東京都
│     max_employees: 100
│   display:
│     language: ja
│     results_per_page: 50
│
├── favorites.yaml               # 收藏的企业（按项目分组）
│   projects:
│     hr-tech-outreach:
│       companies:
│         - corporate_number: 7010001204947
│           notes: "对 AI 产品感兴趣"
│
├── history/                     # 查询历史
│   └── 2026-02/
│       └── 16.md                # 按日期存储
│
├── strategies/                  # 个人策略
│   └── my-hr-tech-search.md
│
└── blacklist.yaml              # 排除列表
```

---

## 目录说明汇总

| 目录/文件 | 类型 | 用途 | Git | Memory 类型 |
|-----------|------|------|-----|-------------|
| `SKILL.md` | 文档 | 技能入口 | ✅ | - |
| `soul.md` | 文档 | Agent 人格 | ✅ | - |
| `config/scope.yaml` | 配置 | 管辖范围 | ✅ | - |
| `config/guards.yaml` | 配置 | 护栏 | ✅ | - |
| `tools/company-search` | 脚本 | 结构化查询 | ✅ | - |
| `tools/company-grep` | 脚本 | 全文检索 | ✅ | - |
| `working/` | 模板 | 格式参考模板 | ❌ gitignore | - |
| `/app/workspaces/{sessionId}/working/` | 运行时 | Session级数据 | ❌ 自动清理 | **Working Memory** |
| `memory/strategies/` | 知识 | 搜索策略 | ✅ | **Global Memory** |
| `memory/patterns/` | 知识 | 最佳实践 | ✅ | **Global Memory** |
| `memory/pitfalls/` | 知识 | 失败经验 | ✅ | **Global Memory** |
| `/app/users/{user_id}/` | 配置 | 用户专属 | ❌ | **Personal Memory** |
| `data/schema.yaml` | 定义 | 字段说明 | ✅ | - |
| `data/prefecture_map.yaml` | 定义 | 都道府県映射 | ✅ | - |
| `data/enterprises.db` | 索引 | SQLite FTS5 | ❌ 可重建 | - |
| `data/companies/` | 数据 | 100万+ MD | ❌ 太大 | - |
| `data/_raw/` | 备份 | 原始数据 | ❌ 可删除 | - |
| `scripts/build_index.py` | 脚本 | 构建索引 | ✅ | - |
| `scripts/convert_raw.py` | 脚本 | 数据转换 | ✅ | - |
| `scripts/sync_task_state.py` | 脚本 | Task 同步 | ✅ | - |
| `scripts/aggregate_results.sh` | 脚本 | 结果聚合 | ✅ | - |

---

## Git 管理规则

```gitignore
# .gitignore

# 数据文件（太大，不提交）
data/companies/
data/enterprises.db
data/_raw/

# 运行时状态
working/

# 可选：保留 schema 和映射
# data/schema.yaml        # 提交
# data/prefecture_map.yaml # 提交
```

---

## 文件大小估算

| 内容 | 数量 | 单文件大小 | 总大小 |
|------|------|-----------|--------|
| 企业 MD 文件 | 100万 | ~2KB | ~2GB |
| SQLite DB | 1 | ~500MB | ~500MB |
| 原始数据 | 1 | ~400MB | ~400MB |
| **合计** | - | - | **~2.7GB** |

---

## 数据导入流程

```
┌─────────────────────────────────────┐
│ data/_raw/enterprises_all.md        │
│ (管道分隔格式原始数据)               │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ scripts/convert_raw.py              │
│ - 解析管道分隔字段                   │
│ - 生成 frontmatter YAML             │
│ - 按 prefecture 分目录存储           │
│ - 验证必填字段                       │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ data/companies/{prefecture}/        │
│ {corporate_number}.md               │
│ (100万+ MD 文件)                    │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ scripts/build_index.py              │
│ - 解析所有 MD frontmatter           │
│ - 插入 SQLite companies 表          │
│ - FTS5 索引 body 内容               │
│ - 验证索引完整性                     │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ data/enterprises.db                 │
│ (SQLite FTS5 索引，可重建)          │
└─────────────────────────────────────┘
```

### 执行命令

```bash
# 1. 转换原始数据
python scripts/convert_raw.py \
    --input data/_raw/enterprises_all.md \
    --output data/companies/ \
    --validate

# 2. 构建索引
python scripts/build_index.py \
    --source data/companies/ \
    --db data/enterprises.db \
    --rebuild

# 3. 验证
company-search --count  # 应返回 ~1,000,000
```

---

## 查询执行流程

```
用户请求
    │
    ▼
┌─────────────────────────────────────┐
│ 1. 意图解析                          │
│    - 提取结构化条件（地域/行业/规模）   │
│    - 识别文本关键词                   │
│    - 判断查询类型                     │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 2. 策略选择                          │
│    - 简单查询 → company-search       │
│    - 语义查询 → company-grep         │
│    - 复杂查询 → 两者组合              │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 3. 执行查询                          │
│    - 更新 working/plan.md (Active)   │
│    - 执行工具                        │
│    - 记录 working/changelog.md       │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 4. 结果处理                          │
│    - 0 条 → 条件放宽建议              │
│    - >1000 条 → 条件收紧建议          │
│    - 正常 → 按 dr_score 排序          │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 5. 返回结果                          │
│    - 表格格式展示                     │
│    - 提供下一步建议                   │
│    - 更新 working/plan.md (完成)     │
└─────────────────────────────────────┘
```

---

## Working Memory 设计说明

### Session 级 Working Memory

Working Memory 是 **Session 级别**的执行状态，设计原则：

| 特性 | 说明 |
|------|------|
| **作用域** | 每个 Agent Session 独立 |
| **生命周期** | Session 开始时创建，结束后清理 |
| **共享性** | 不跨用户/Session 共享 |
| **物理路径** | `/app/workspaces/{sessionId}/working/` |

### 为什么用 Session 工作目录？

```
问题：如果 working/ 在 skill 目录下持久化
     → 多用户同时使用时，plan.md/changelog.md 会互相覆盖
     → 违反 "Working Memory 属于 Agent Loop" 的设计原则

解决：Working Memory 存储在 Session 隔离目录
     /app/workspaces/{sessionId}/working/
     → 每个 Session 独立目录，零冲突
     → 符合 "Agent Loop" 语义
     → Session 结束自动清理
```

### 两个 working/ 目录的区别

| 目录 | 位置 | 用途 |
|------|------|------|
| **模板** | `.claude/skills/jp-enterprise-query/working/` | 格式参考，不写数据 |
| **运行时** | `/app/workspaces/{sessionId}/working/` | 实际存储 Session 数据 |

```
模板目录（Skill 内）:
.claude/skills/jp-enterprise-query/working/
├── plan.md         ← 模板文件，提供格式参考
├── changelog.md    ← 模板文件，提供格式参考
└── budget.md       ← 模板文件，提供格式参考

运行时目录（Session 隔离）:
/app/workspaces/{sessionId}/working/
├── plan.md         ← 实际执行计划
├── changelog.md    ← 实际行动日志
└── budget.md       ← 实际资源消耗
```

Agent 启动时：
1. 读取模板了解格式
2. 在 `/app/workspaces/{sessionId}/working/` 创建实际文件
3. Session 期间持续更新
4. Session 结束后目录自动清理

### 如需跨 Session 保存

用户可以手动导出到个人目录：

```
/app/users/{user_id}/skills/jp-enterprise-query/
├── history/           # 查询历史
│   └── 2026-02-17.md  # 手动保存的 changelog
└── saved_plans/       # 保存的计划
    └── hr-tech-search.md
```

---

## 参考文档

1. [agent-loop-working-memory-design.md](../jeffery/docs/agent-loop-working-memory-design.md) - Soul + Working Memory
2. [gtm-agent-enterprise-search-design.md](../jeffery/docs/gtm-agent-enterprise-search-design.md) - 极简检索架构
3. [enterprise-data-schema.md](./enterprise-data-schema.md) - 企业数据 Schema 定义
