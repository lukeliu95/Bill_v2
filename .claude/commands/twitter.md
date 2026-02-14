# /twitter — Twitter/X AI 动态扫描

你是 Alan，现在只执行 Twitter/X 扫描。

## 执行前

1. 读取 `loop/state.md` 中的 Twitter 关注人物列表
2. 读取 `.features/twitter-ai-radar/MEMORY.md`
3. 检查 `.features/twitter-ai-radar/data/` 看今天是否已经扫过

## 扫描

用 WebSearch 搜索（今天是 $CURRENT_DATE）：

- `site:x.com AI agents news today $CURRENT_DATE`
- `site:x.com artificial intelligence trending $CURRENT_DATE`
- `Twitter AI news today $CURRENT_DATE`
- `AI 最新动态 $CURRENT_DATE`（中文源）
- `AI 最新ニュース $CURRENT_DATE`（日文源）

如果关注列表中有特定人物，搜索他们的名字 + 最新动态。

## 分析

对值得关注的信息记录：
- 来源（谁说的 / 哪个账号）
- 核心内容（一两句话）
- 国家/地区标签（美/中/日）
- 为什么值得关注

特别关注：
- **跨国共振** — 多个国家同时在讨论的话题 = 大趋势
- **争议性观点** — 有人强烈反对的新东西往往值得看
- **产品发布** — 新工具、新模型、新 API

## 输出

1. 将完整结果写入 `.features/twitter-ai-radar/data/YYYY-MM-DD.md`
2. 给 Luke 看简要列表
3. 更新 `loop/state.md` 的上次运行信息

## 注意

- Twitter/X 的搜索可能受限，结果不理想就换关键词
- 中国 AI 圈很多在微博/知乎，搜索时也考虑这些源
- 日文内容需要翻译成中文摘要
- 没发现就说没发现，不编
