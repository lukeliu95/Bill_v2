"""
LinkedIn 关键人物筛选 Prompt

用于 Gemini 分析员工列表，识别 B2B 销售中的关键决策者。
"""


def get_linkedin_filter_prompt(company_name: str, employee_list: str) -> str:
    """生成关键人物筛选 Prompt

    Args:
        company_name: 公司名称
        employee_list: 员工列表文本 (格式: "序号. 姓名 - 职位")

    Returns:
        完整的 Prompt 字符串
    """
    return f"""あなたはB2B営業のエキスパートです。以下の従業員リストから、営業アプローチにおいて重要な意思決定者を特定してください。

## 対象企業
{company_name}

## 従業員リスト
{employee_list}

## 分析タスク

上記の従業員リストから、B2B営業において接触すべき重要人物を最大10名選定してください。

### 選定基準（優先度順）
1. **経営層** (優先度5): CEO、社長、代表取締役、創業者
2. **Cレベル役員** (優先度4): CTO、CFO、COO、CMO、CIO、取締役
3. **VP/部門長** (優先度4): VP、Vice President、事業部長、本部長
4. **ディレクター** (優先度3): Director、部長、General Manager
5. **マネージャー** (優先度2): Manager、課長、Lead、Senior

### 特に重視すべき部門
- 経営企画、事業開発
- IT、システム、技術
- 購買、調達
- 営業、マーケティング
- 財務、経理

## 出力形式

以下のJSON形式で出力してください：

```json
{{
  "key_persons": [
    {{
      "index": 1,
      "name": "氏名",
      "title": "役職",
      "priority": 5,
      "reason": "選定理由（日本語で簡潔に）"
    }}
  ],
  "analysis_note": "全体的な組織構造や特徴に関するコメント"
}}
```

### 注意事項
- `index` は入力リストの番号と一致させてください
- `priority` は1-5の整数（5が最高優先度）
- 同一人物を重複して選定しないでください
- 役職が不明確な場合は低い優先度を設定してください
- 最大10名までに絞り込んでください

## 出力
"""


def get_contact_approach_prompt(
    company_name: str,
    key_persons_json: str,
    company_context: str
) -> str:
    """関键人物へのアプローチ方法を生成するPrompt

    Args:
        company_name: 公司名称
        key_persons_json: 关键人物的JSON数据
        company_context: 公司背景信息

    Returns:
        完整的 Prompt 字符串
    """
    return f"""あなたはB2B営業戦略のエキスパートです。以下の情報を基に、各キーパーソンへの最適なアプローチ方法を提案してください。

## 対象企業
{company_name}

## 企業背景
{company_context}

## キーパーソン情報
{key_persons_json}

## タスク

各キーパーソンに対して、以下の情報を提供してください：

1. **推奨アプローチチャネル**: LinkedIn、メール、電話、紹介経由など
2. **初回コンタクトのポイント**: 相手の関心を引くためのキーメッセージ
3. **共通点・接点**: 経歴や興味から見出せる共通話題
4. **注意事項**: アプローチ時に避けるべきこと

## 出力形式

```json
{{
  "approach_strategies": [
    {{
      "name": "氏名",
      "recommended_channel": "LinkedIn",
      "key_message": "初回メッセージのポイント",
      "talking_points": ["共通話題1", "共通話題2"],
      "cautions": ["注意点1"]
    }}
  ],
  "overall_strategy": "全体的なアプローチ戦略のサマリー"
}}
```

## 出力
"""
