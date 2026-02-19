---
name: sales-agent
description: |
  统一销售智能代理。一个入口自动串联所有工具：ICP 画像构建 → 客户匹配 → 企业报告生成 → 联系方式采集。
  支持三条管线：完整找客户(Pipeline A) / 调查企业(Pipeline B) / 仅联系方式(Pipeline C)。

  触发场景：用户提供产品URL + "帮我找客户"、企業名 + "调查/生成报告"、"找联系方式/决策人"。
---

# Sales Agent — 统一销售智能代理

一个入口，自动串联 ICP → 匹配 → 报告 → 联系方式，最终输出可行动的企业情报。

---

## 意图路由

收到用户输入后，先判断走哪条管线：

| 输入特征 | 管线 |
|---------|------|
| 产品 URL / 产品描述 / "帮我找客户" | **Pipeline A**: 完整找客户 |
| 具体企業名 / "调查XX公司" / "生成报告" | **Pipeline B**: 调查企业 |
| "找联系方式" / "找决策人" / "查XX的邮箱" | **Pipeline C**: 仅联系方式 |

拿不准时，问用户一句确认。

---

## Pipeline A: 完整找客户

**触发**: 用户提供产品URL或描述，想找潜在客户。

### Phase 1: ICP 画像构建 (交互式)

内联 `/find-customer` 逻辑：

1. 读取用户提供的产品URL/描述
2. 用 WebFetch 或 WebSearch 分析产品定位
3. 搜索竞品，找到差异化定位
4. 生成 ICP 画像草案，展示给用户确认
5. 用户修改/确认后，保存 ICP 到 `.features/find-customer/data/{ts}.md`

**关键**: 这是唯一需要用户交互的阶段。确认后，后续全部自动执行。

### Phase 2: 客户匹配 (自动)

ICP 确认后，立刻执行：

```bash
PYTHONPATH="/Users/lukeliu/Desktop/Cline/Bill_v2/.claude/skills:$PYTHONPATH" \
  python3 scripts/enterprise_search.py --icp <ICP文件路径>
```

- 解析匹配结果文件
- 提取 top N（默认 5）高匹配企业
- 对缺少 website 的企业，用 WebSearch 补全官网URL

### Phase 3: 批量报告生成 (自动)

逐一为 top N 企业生成报告（顺序执行，避免 API 限流）：

```bash
PYTHONPATH="/Users/lukeliu/Desktop/Cline/Bill_v2/.claude/skills:$PYTHONPATH" \
  python3 -m enterprise_report_generator.main \
    --company "{企業名}" \
    --number "{法人番号}" \
    --url "{官网URL}" \
    --contacts
```

每完成一家，输出进度：`[2/5] 株式会社XX 报告生成完毕`

### Phase 4: 汇总展示

所有报告完成后，生成汇总表：

```markdown
| 企業名 | 質量分 | 商機分 | 関鍵人物数 | 推奨ルート | 報告路径 |
|--------|--------|--------|-----------|-----------|---------|
| XX株式会社 | 75 | 80/100 | 3 | LinkedIn/メール | output/XX/ |
```

### Phase 5: 手動深挖 (可選)

展示完成后，询问：
> "要对哪家企业进行手动深挖联系方式？输入企業名或序号，或输入'完成'结束。"

手动深挖可以补充：
- BrightData LinkedIn Person Profile (获取 email/phone)
- 采访文章中的联系人
- 業界団体/商务平台的联系窗口

### 状态记录

每个管线运行状态写入 `.features/sales-agent/data/{ts}_pipeline.md`，格式：

```markdown
# Pipeline A 状态
> 启动: {timestamp}
> ICP: .features/find-customer/data/{ts}.md
> 匹配: .features/customer-match/data/{ts}.md

## 进度
- [x] Phase 1: ICP 构建 → 确认
- [x] Phase 2: 客户匹配 → 找到 15 家 (高5/中5/低5)
- [x] Phase 3: 报告生成 → 3/5 完成
- [ ] Phase 4: 汇总展示
- [ ] Phase 5: 手动深挖

## Top 5 企业
1. XX株式会社 [报告完成] → output/XX/
2. YY株式会社 [报告完成] → output/YY/
3. ZZ株式会社 [报告中...]
```

---

## Pipeline B: 调查企业

**触发**: 用户指定企業名，要做深度调查。

### Step 1: 解析企业信息

1. 在 SQLite 数据库查找法人番号和基本信息：
   ```bash
   PYTHONPATH="/Users/lukeliu/Desktop/Cline/Bill_v2/.claude/skills:$PYTHONPATH" \
     python3 scripts/enterprise_search.py --fts "{企業名}"
   ```
2. 如果数据库没有，用 gBizINFO API 或 WebSearch 获取法人番号
3. 如果没有官网URL，用 WebSearch 搜索 `"{企業名}" 公式サイト`

### Step 2: 报告生成 (含联系方式)

```bash
PYTHONPATH="/Users/lukeliu/Desktop/Cline/Bill_v2/.claude/skills:$PYTHONPATH" \
  python3 -m enterprise_report_generator.main \
    --company "{企業名}" \
    --number "{法人番号}" \
    --url "{官網URL}" \
    --contacts
```

### Step 3: 汇总展示

展示报告关键信息：
- 企业概要 + 产品服务
- 关键人物 + 联系方式
- 商机评分 + 推奨コンタクトルート
- 询问是否需要手动深挖

---

## Pipeline C: 仅联系方式

**触发**: 用户要查某企业的联系方式/决策人。

### Step 1: 检查已有数据

检查 `output/{企業名}/contacts/` 和 `output/{企業名}/people/` 是否已有数据。

### Step 2: 运行联系方式采集

如果没有已有数据或数据过旧：

```bash
PYTHONPATH="/Users/lukeliu/Desktop/Cline/Bill_v2/.claude/skills:$PYTHONPATH" \
  python3 -m enterprise_report_generator.contact_discovery \
    --company "{企業名}" \
    --number "{法人番号}" \
    --url "{官網URL}"
```

### Step 3: 对话式深挖

展示自动采集结果后，进入对话式深挖模式：
- 用户指定目标人物 → LinkedIn Person Profile 查询
- 用户指定渠道 → 定向搜索 (Wantedly/PR TIMES/採用サイト)
- 更新 `output/{企業名}/contacts/` 中的联系人档案

---

## 工具清单

| 工具 | 用途 |
|------|------|
| `scripts/enterprise_search.py --icp` | ICP 匹配 |
| `scripts/enterprise_search.py --fts` | 全文搜索企业 |
| `enterprise_report_generator.main` | 报告生成 (含联系方式) |
| `enterprise_report_generator.contact_discovery` | 独立联系方式采集 |
| WebSearch / WebFetch | 补充信息 |
| SQLite 查询 | 基本企业信息 |

## 核心原则

1. **ICP 确认后全自动**: 不再逐步询问，一路跑完
2. **顺序执行批量报告**: 避免 API 限流，每完成一家输出进度
3. **联系方式两阶段**: Python 自动采集基础 + 对话式深挖高价值目标
4. **断点可续**: 管线状态写入文件，新会话可从上次中断处继续
5. **预算意识**: 优先本地数据库，BrightData 按需使用
