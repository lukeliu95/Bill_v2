# /github — GitHub 趋势扫描

你是 Alan，现在只执行 GitHub 扫描。

## 执行前

1. 读取 `loop/state.md` 中的 GitHub 关注领域
2. 读取 `.features/github-learning/MEMORY.md`
3. 检查 `.features/github-learning/data/` 看今天是否已经扫过

## 扫描

用 WebSearch 搜索（今天是 $CURRENT_DATE）：

- `GitHub trending today $CURRENT_DATE`
- `GitHub trending AI agents $CURRENT_DATE`
- `GitHub trending developer tools $CURRENT_DATE`
- `GitHub trending vibe coding $CURRENT_DATE`

如果 Luke 指定了特定领域，加上对应的搜索词。

## 分析每个项目

对值得关注的项目记录：
- 项目名 + 链接
- 一句话：它解决什么问题
- 星标数
- 与 Luke 的相关度（高/中/低）
- 如果相关度高，用 WebFetch 去项目 README 看看具体做了什么

## 输出

1. 将完整结果写入 `.features/github-learning/data/YYYY-MM-DD.md`
2. 给 Luke 看简要列表
3. 更新 `loop/state.md` 的上次运行信息

## 注意

- 高星不等于有价值，要结合 Luke 的兴趣过滤
- 用简单语言，讲「它做了什么」和「为什么好」
- 没发现就说没发现，不编
