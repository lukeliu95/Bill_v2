---
name: customer-match
description: |
  基于 ICP 画像（.features/find-customer/data/ 下的 MD 文件），在企业数据库中匹配潜在客户。
  使用 Python 执行三层漏斗查询（硬性条件 → 正向/负向关键词 → 评分排序），输出分层匹配企业列表。

  触发场景：find-customer 输出 ICP 画像后手动触发，
  或用户说"帮我匹配客户"、"跑一下筛选"时手动触发。
---

# Customer Match

读取 ICP 筛选条件，在企业数据库中匹配潜在客户。

## 核心原则

1. **三层漏斗**：硬性条件 → 关键词正向/负向 → 多信号评分
2. **Python 优先**：不用 bash grep+awk 管道（字段解析容易出错），统一用 Python 解析
3. **分层输出**：结果按评分分为高/中/低匹配，不混在一起
4. **实时写入**：匹配结果立刻写入 `.features/customer-match/data/`

## 数据格式

企业数据在 `data/enterprises.db`（SQLite 数据库），由 `data/Kihonjoho_UTF-8.csv`（579万行）导入。

**数据库结构**：
- 主表 `enterprises`：houjin_bangou(PK), company_name, address, prefecture, prefecture_code, employee_count, capital, business_summary, business_type, website, established_date 等
- FTS5 全文索引 `enterprises_fts`：company_name, business_summary, business_type
- 结构化索引：prefecture_code, employee_count, capital, established_date, (prefecture_code + employee_count) 复合索引

**如果数据库不存在**，先运行 `python3 scripts/import_csv_to_sqlite.py` 导入。

**旧数据源**：`data/enterprises_10000.md`（10000 条）已不再使用，仍保留作为备份。

## 流程

### Step 1: 读取 ICP 画像

读取 `.features/find-customer/data/` 目录下**最新的 MD 文件**（按文件名时间戳排序）。

**读取方式**：
1. 用 Glob 找到 `.features/find-customer/data/*.md` 下所有文件
2. 取文件名时间戳最新的一个
3. 读取文件，提取 `## 筛选条件（JSON）` 下的 JSON code block
4. 解析 JSON 中的筛选条件

**解析字段**：
- `prefectureIds` → 地域过滤
- `minEmployeeNumber` / `maxEmployeeNumber` → 员工数范围
- `minEstablishmentAt` / `maxEstablishmentAt` → 成立日范围
- `minCapitalStock` / `maxCapitalStock` → 资本金范围
- `categoryCodes` → 行业关键词映射（不能直接匹配カテゴリID）
- `enhancedConditions` → 评分信号

**异常处理**：如果 `.features/find-customer/data/` 下没有文件，提示用户先运行 `/find-customer` 生成 ICP 画像。

### Step 2: 执行三层漏斗检索

**使用 `scripts/enterprise_search.py`**，它内置了完整的三层漏斗逻辑。

#### 执行方式

```bash
# 方式 A：从 ICP 文件读取条件
python3 scripts/enterprise_search.py --icp .features/find-customer/data/xxx.md

# 方式 B：直接传 JSON 条件
python3 scripts/enterprise_search.py --query '{"prefectureIds":[13],"minEmployeeNumber":10,"maxEmployeeNumber":500,"categoryCodes":["G"]}'

# 方式 C：自定义关键词
python3 scripts/enterprise_search.py --query '...' --keywords "AI,SaaS,クラウド"

# 方式 D：FTS5 全文搜索（自由文本）
python3 scripts/enterprise_search.py --fts "AI SaaS クラウド"
```

#### Layer 1: 硬性条件（SQL 索引查询，毫秒级）

直接用 `prefecture_code` 索引过滤都道府県，用 `employee_count` 索引过滤员工数。
不再需要字符串匹配住所，不再需要 regex 清洗数字字段。

#### Layer 2: 行业关键词（正向 + 负向排除）

**重要**：数据中的 `カテゴリID` 是平台内部编号，不能用 `categoryCodes` 直接匹配。
行业过滤改用事業内容关键词。

##### 行业关键词映射表

根据 `categoryCodes` 和 `enhancedConditions` 构建两组关键词：

**正向关键词（IT/SaaS 类，必须命中 ≥1 才进入候选池）**：

| categoryCodes | 宽匹配关键词（Tier 1 — IT识别） |
|--------------|-------------------------------|
| G（情報通信業） | IT, ソフトウェア, システム, クラウド, Web, デジタル, AI, テクノロジー, DX, エンジニアリング, アプリ, データ, SaaS, プラットフォーム, プロダクト, ソリューション, IoT, セキュリティ, ネットワーク, インターネット, テック |

其他行业的宽匹配关键词：

| categoryCodes | 宽匹配关键词 |
|--------------|-------------|
| E（製造業） | 製造, メーカー, 工場, 生産 |
| I（卸売業、小売業） | 卸売, 小売, 商社, 販売, 流通 |
| D（建設業） | 建設, 工事, 建築, 土木 |
| J（金融業、保険業） | 銀行, 証券, 保険, 金融, ファイナンス |
| K（不動産業） | 不動産, 賃貸, 物件 |
| L（専門・技術サービス業） | コンサル, 法律, 会計, 広告, デザイン, 調査 |
| H（運輸業） | 運輸, 物流, 配送, 倉庫 |
| P（医療、福祉） | 医療, 病院, 介護, 福祉 |

**负向关键词（硬排除 — 命中即排除）**：

```python
hard_exclude = ["受託", "派遣", "SES", "人材紹介", "請負", "常駐", "人材派遣"]
```

これらは SI/SES/外包の典型的キーワード。事業内容に含まれていれば候補から除外する。

#### Layer 3: 多信号评分排序

通过 Layer 2 的企业，按事業内容中的信号打分。

##### 评分信号表

**正向信号（SaaS/产品公司特征）**：

| 信号关键词 | 分数 | 含义 |
|-----------|------|------|
| SaaS | +5 | SaaS 明示 |
| プロダクト | +4 | 有自己产品 |
| 自社サービス, 自社開発 | +4 | 自社开发/服务 |
| プラットフォーム | +3 | 平台型 |
| アプリ | +3 | 应用开发 |
| クラウド | +2 | 云服务 |
| AI, 人工知能, 機械学習 | +2 | AI 相关 |
| DX, デジタルトランスフォーメーション | +2 | DX 推进 |
| データ分析, データ活用, ビッグデータ | +2 | 数据分析 |
| 開発（无受託時） | +1 | 可能是自社開発 |

**负向信号（IT服务/外包特征 — 减分但不排除）**：

| 信号关键词 | 分数 | 含义 |
|-----------|------|------|
| コンサルティング, コンサル | -2 | 咨询为主 |
| マーケティング支援, 広告運用, 広告代理 | -2 | 广告/营销代理 |
| 制作, Web制作 | -1 | 制作公司 |
| 人材, 採用支援, HR | -1 | 人材系 |
| 運用・保守, 運用保守 | -1 | 运维为主 |

**评分规则**：
- 每组信号只计一次（同组内多个关键词命中不重复加分）
- 最终按总分降序排列
- 分数相同时按员工数降序

##### 根据 enhancedConditions 调整评分

ICP 画像的 `enhancedConditions` 中的 weight 用于调整评分：
- weight ≥ 4 的条件对应的关键词，评分 ×1.5
- weight ≤ 2 的条件对应的关键词，评分 ×0.8

示例：ICP 中 `DX推進中` weight=5 → DX 关键词从 +2 变为 +3。

### Step 3: 执行与输出

**执行方式**：`python3 scripts/enterprise_search.py --icp <ICP文件路径>`，结果自动保存到 `.features/customer-match/data/`。

**分层展示**：

| 层级 | 条件 | 含义 |
|------|------|------|
| ★ 高匹配 | 评分 ≥ 4 | SaaS产品公司特征明显 |
| ◆ 中匹配 | 评分 1-3 | IT企业，可能有产品 |
| ○ 低匹配 | 评分 ≤ 0 | IT服务/コンサル为主 |

**件数控制**：
- 高+中匹配 0 件 → 条件缓和（见下方策略）
- 高+中匹配 1-50 件 → 正常输出
- 高+中匹配 50+ 件 → 收紧正向关键词或加强负向排除

**结果文件输出**：`.features/customer-match/data/YYYY-MM-DD-HHmmss.md`

出力フォーマット：
```markdown
# 客户匹配结果
> 匹配时间：YYYY-MM-DD-HHmmss
> 筛选条件：ICP の parseExplanation を引用
> 匹配数：N 件（高匹配 X 件 + 中匹配 Y 件 + 低匹配 Z 件）

## 筛选条件摘要
- 地域：XX
- 员工数：XX ~ XX
- 正向关键词：XX
- 负向排除词：XX

## ★ 高匹配（≥4分）

| # | 企業名 | 従業員数 | 評分 | 信号 | 事業内容 | ウェブサイト | 法人番号 |
|---|--------|----------|------|------|----------|-------------|----------|
| 1 | XX | XX | XX | XX | XX | XX | XX |

## ◆ 中匹配（1-3分）

| # | 企業名 | 従業員数 | 評分 | 信号 | 事業内容 | ウェブサイト | 法人番号 |
|---|--------|----------|------|------|----------|-------------|----------|
| 1 | XX | XX | XX | XX | XX | XX | XX |

## ○ 低匹配（≤0分）

| # | 企業名 | 従業員数 | 評分 | 事業内容 | ウェブサイト | 法人番号 |
|---|--------|----------|------|----------|-------------|----------|
| 1 | XX | XX | XX | XX | XX | XX |
```

**MEMORY.md 更新**：`.features/customer-match/MEMORY.md` の快速索引に追記。
**用户展示**：高匹配全件 + 中匹配全件を対話で表示。低匹配は件数のみ。

## 条件缓和策略

高+中匹配が 0 件の場合、以下の順序で条件を緩和：

1. 正向関键词を広げる（Tier 1 のみ → enhancedConditions 由来のキーワードも正向に追加）
2. 従業員数範囲を ±50% に拡大
3. 地域を隣接エリアに拡大（例：関西 → 関西+中部）
4. 成立日・資本金条件を削除

緩和した場合は必ずユーザーに報告する。

## 注意事項

- **数据库优先**：使用 `data/enterprises.db` (SQLite + FTS5)，579万行企业数据，查询毫秒级
- **如果 DB 不存在**：运行 `python3 scripts/import_csv_to_sqlite.py` 重建（约 40 秒）
- カテゴリID は平台内部编号 → categoryCodes で直接マッチ不可
- 事業概要（business_summary）が短い・汎用的な企業が多い → 正向キーワード「必須命中≥1」でフィルタし、評分で優先度をつける
- 設立日が空の企業がある → 設立日フィルタ時は空値を除外しない
- 結果は必ず `.features/customer-match/data/` に保存する（実時写入原則）
- 高匹配でも事業概要の記載だけでは精度に限界がある → ユーザーに「官网验证推奨」を提案する
- **検索脚本路径**：`scripts/enterprise_search.py`（三層漏斗）、`scripts/import_csv_to_sqlite.py`（导入）
