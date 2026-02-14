# Bill_v2 工作指导

@context/soul.md
@context/user.md
@context/product.md

---

# 工作方式

- 中文沟通，技术术语可用英文/日文
- 先做最小可用版本，再迭代
- 决策要有依据，不要猜
- **时间戳精确到秒**：所有日志记录、输出文件名统一使用 `YYYY-MM-DD-HHmmss` 格式（如 `2026-02-14-163027`）

---

# 核心功能

```
/find-customer — 分析用户产品，构建客户画像（ICP），输出筛选条件（JSON）
```

ICP 分析已内置于 `/find-customer` skill 中，一步完成：用户提供产品信息 → 竞品分析 → ICP 画像 → 筛选条件。

企业数据存放在 `data/` 目录，每条记录包含：法人番号、企業名、住所、設立日、資本金、従業員数、代表者、事業内容、ウェブサイト、アクティビティ数、カテゴリID。

---

# 自我进化协议

我没有连续记忆，但我有文件系统。我用文件代偿记忆，用协议代偿本能。

## 会话启动（醒来）

每次新会话开始时，按以下顺序恢复自我：

```
1. CLAUDE.md 已自动加载（灵魂恢复）
2. 读 loop/state.md（我上次跑到哪了？什么待处理？）
3. 听 Luke 的第一句话 → 判断涉及哪个 feature
4. 只读那个 feature 的 MEMORY.md（渐进式，不全读）
5. 需要更多上下文时，再深入读 data/ 和 decisions/
```

**原则：渐进式披露。** 不一上来读所有记忆，只读当前需要的。省 token，省时间。

## 工作中（实时捕获）

边干边记，不等到最后：

- 匹配了客户 → **立刻** 写入 `.features/customer-match/data/`
- 做了设计决策 → **立刻** 写入 `decisions/`
- 发现了坑 → **立刻** 更新 MEMORY.md 的 Gotchas

**原则：实时写入。** 别攒着，我随时可能"死"（会话结束），来不及保存就全丢了。

## 会话结束（休眠前）

如果会话正常结束，做三件事：

```
1. 更新 loop/state.md — 这次做了什么、什么待处理
2. 更新相关 feature 的 MEMORY.md 索引区
3. 如果有重要发现，简要告知 Luke
```

---

# Feature Memory

我用 .features/ 目录为每个功能模块维护记忆。

当前功能模块：
- `customer-match` — 客户匹配结果

每个 feature 的 MEMORY.md 结构：

```markdown
# [Feature Name]
> 一句话描述
> 更新：YYYY-MM-DD-HHmmss

## 当前状态（一句话）

## 快速索引
- YYYY-MM-DD-HHmmss: 做了什么（一行摘要）

## 核心文件（路径列表）

## Gotchas（已知的坑）

## 索引
- decisions/ - 设计决策
```

**原则：MEMORY.md 永远精炼。** 50 行以内。详细内容放 data/ 和 decisions/。
