# Customer Match
> 基于 ICP 在企业数据库中查找匹配客户
> 更新：2026-02-14-180000

## 当前状态
v3 最终版。两类客户共 62 家：制造业 30 家 + 東京SaaS 32 家。ICP 分析已迁移至 /find-customer skill 内置完成。

## 快速索引
- 2026-02-14-150000: v1 错误版（找成IT同行）→ v2 修正（制造业30家）→ v3 最终版（+東京SaaS 32家）
- 2026-02-14-170000: ICP 功能迁移至 /find-customer skill，删除 .features/icp-analysis/

## 核心文件
- .features/customer-match/data/2026-02-14.md — 匹配结果（62 家）
- data/enterprises_10000.md — 企业数据库
- .claude/skills/find-customer/SKILL.md — ICP + 客户画像 skill

## Gotchas
- 企业数据格式：パイプ区切り（法人番号|企業名|住所|設立日|資本金|従業員数|代表者|事業内容|ウェブサイト|アクティビティ数|カテゴリID）
- 关键词匹配对制造业够用，对SaaS企业不够 — 需要语义判断 + 网站验证
- 超早期SaaS（≤5人）极度缺工程师但可能没预算，优先级放后

## 索引
- decisions/ — 设计决策
