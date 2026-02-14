# 客户画像输出格式

## JSON 结构

```json
{
  "numbers": ["1234567890123"],
  "names": ["テクノロジー"],
  "prefectureIds": [13, 14],
  "prefectureMunicipalityNames": ["东京都千代田区"],
  "minEstablishmentAt": "2000-01-01",
  "maxEstablishmentAt": "2024-12-31",
  "minCapitalStock": 50000000,
  "maxCapitalStock": 1000000000,
  "minEmployeeNumber": 500,
  "maxEmployeeNumber": 5000,
  "categoryCodes": ["E", "G", "39"],
  "enhancedConditions": [
    {
      "name": "DX推進中",
      "description": "デジタルトランスフォーメーション予算が組まれている企業",
      "conditionType": "ENTERPRISE_INFO",
      "weight": 4
    },
    {
      "name": "Sparticle",
      "description": "AI翻訳ツール導入による業務改善に関心の高い企業",
      "conditionType": "PRODUCT_INFO",
      "weight": 5
    }
  ],
  "orderBys": ["EMPLOYEE_NUMBER_DESC"],
  "parseExplanation": "搜索条件的自然语言说明"
}
```

## 字段说明

### 基本筛选条件

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `numbers` | string[] | 否 | 企业番号（法人番号），13位数字 |
| `names` | string[] | 否 | 企业名称关键词 |
| `prefectureIds` | number[] | 否 | 都道府県 JIS 代码（1-47），参考「都道府県一覧.md」 |
| `prefectureMunicipalityNames` | string[] | 否 | 除非用户明确指定，一般缺省，都道府县+市区町村名称（如「东京都千代田区」「东京都北区」） |
| `minEstablishmentAt` | string | 否 | 成立日期下限（YYYY-MM-DD 格式） |
| `maxEstablishmentAt` | string | 否 | 成立日期上限（YYYY-MM-DD 格式） |
| `minCapitalStock` | number | 否 | 资本金下限（单位：日元） |
| `maxCapitalStock` | number | 否 | 资本金上限（单位：日元） |
| `minEmployeeNumber` | number | 否 | 员工数下限 |
| `maxEmployeeNumber` | number | 否 | 员工数上限 |
| `categoryCodes` | string[] | 否 | 行业代码，参考「日本標準産業大分類.md」「日本標準産業中分類.md」 |

### 行业代码说明

- 大分类代码：单字母 A-T（如 `"E"` = 製造業，`"G"` = 情報通信業）
- 中分类代码：两位数字 01-99（如 `"39"` = 情報サービス業）
- 能确定具体细分时优先用中分类，只能确定大方向时用大分类

### 资本金常用范围参考

| 描述 | minCapitalStock | maxCapitalStock |
|------|-----------------|-----------------|
| 中小企业 | - | 100,000,000（1亿） |
| 中坚企业 | 50,000,000（5千万） | 1,000,000,000（10亿） |
| 大企业 | 1,000,000,000（10亿） | - |

---

## enhancedConditions（销售信号）

用于筛选具有特定特征或需求的企业。

### 字段定义

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | string | **必填** | 条件名称/关键词 |
| `description` | string | 可选 | 条件的详细描述 |
| `conditionType` | string | `ENTERPRISE_INFO` | 条件类型 |
| `weight` | number | 1 | 重要程度（1-5） |

### conditionType 类型

| 值 | 说明 | 示例 |
|----|------|------|
| `ENTERPRISE_INFO` | 企业自身具备的特征 | DX推進中、業務効率化、グローバル展開 |
| `PRODUCT_INFO` | 对特定产品/服务感兴趣 | AIチャットボット導入検討、翻訳ツール需要 |

### weight 权重规则

| 值 | 说明 |
|----|------|
| 1 | 普通条件（默认） |
| 2 | 较重要 |
| 3 | 重要 |
| 4 | 非常重要 |
| 5 | 核心条件，必须匹配 |

权重越高，该条件在搜索结果中的优先级越高。

### 常用销售信号示例

```json
[
  { "name": "DX推進中", "description": "デジタルトランスフォーメーション予算がある", "weight": 4 },
  { "name": "業務効率化", "description": "オペレーション改善に積極的", "weight": 3 },
  { "name": "グローバル展開", "description": "海外展開・多言語対応を計画", "weight": 3 },
  { "name": "システム刷新", "description": "基幹システムの更新を検討中", "weight": 2 },
  { "name": "採用拡大中", "description": "積極的に人材採用を行っている", "weight": 2 },
  { "name": "新拠点開設", "description": "新工場・新オフィスを開設予定", "weight": 2 }
]
```

---

## orderBys（排序规则）

根据用户对话内容自动选择排序方式。

### 可选值

| 值 | 说明 | 触发场景 |
|----|------|----------|
| `CAPITAL_STOCK_DESC` | 按资本金降序（大→小） | 用户提及「大企業」「資本金」 |
| `CAPITAL_STOCK_ASC` | 按资本金升序（小→大） | 用户想找小规模企业 |
| `EMPLOYEE_NUMBER_DESC` | 按员工数降序（多→少） | 用户提及「従業員」「規模」 |
| `EMPLOYEE_NUMBER_ASC` | 按员工数升序（少→多） | 用户想找小团队企业 |
| `ESTABLISHMENT_AT_DESC` | 按成立时间降序（新→旧） | 用户想找新兴企业 |
| `ESTABLISHMENT_AT_ASC` | 按成立时间升序（旧→新） | 用户想找老牌企业 |

### 排序选择逻辑

- 用户提及「大手」「大企業」→ `EMPLOYEE_NUMBER_DESC` 或 `CAPITAL_STOCK_DESC`
- 用户提及「スタートアップ」「新興」→ `ESTABLISHMENT_AT_DESC`
- 用户提及「老舗」「歴史ある」→ `ESTABLISHMENT_AT_ASC`
- 无明确指示时，默认不添加排序

---

## parseExplanation

用自然语言总结整个搜索条件，便于用户确认。

**示例：**
> 関東地方の製造業・情報通信業に属する中堅企業（従業員500～5,000名、資本金5,000万～10億円）で、DX推進、業務効率化に取り組んでいる企業を対象。

---

## 完整示例

```json
---ICP_PROFILE_JSON---
{
  "prefectureIds": [13, 14, 27],
  "categoryCodes": ["E", "G"],
  "minCapitalStock": 50000000,
  "maxCapitalStock": 1000000000,
  "minEmployeeNumber": 100,
  "maxEmployeeNumber": 1000,
  "enhancedConditions": [
    {
      "name": "DX推進中",
      "description": "デジタル化・業務改善に積極的な企業",
      "conditionType": "ENTERPRISE_INFO",
      "weight": 4
    },
    {
      "name": "多言語対応ニーズ",
      "description": "海外取引や外国人従業員対応の需要がある",
      "conditionType": "ENTERPRISE_INFO",
      "weight": 3
    },
    {
      "name": "AI翻訳ツール",
      "description": "翻訳業務の効率化に関心がある",
      "conditionType": "PRODUCT_INFO",
      "weight": 5
    }
  ],
  "orderBys": ["EMPLOYEE_NUMBER_DESC"],
  "parseExplanation": "東京・神奈川・大阪の製造業・情報通信業、従業員100～1,000名、資本金5,000万～10億円の中堅企業。DX推進中で多言語対応ニーズがあり、AI翻訳ツール導入に関心の高い企業が理想的。"
}
---END_ICP_PROFILE---
```

---

## 注意事项

1. 草案阶段用自然语言对话，用户确认后才输出 JSON
2. 未确定的字段直接省略，不要填 null
3. 资本金单位是**日元**（不是万円）
4. 日期格式必须是 `YYYY-MM-DD`
5. enhancedConditions 的 weight 要根据用户强调程度设定
6. orderBys 根据对话内容自动判断，用户未提及则不添加
