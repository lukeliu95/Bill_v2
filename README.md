# Bill_v2

AI 驱动的信息雷达 + 机会发现系统。

由 Alan（Claude Code Agent）自主运行，每天扫描 GitHub 和 Twitter，从噪音中提炼信号，告诉你什么值得关注、什么可能机会。

## 三个模块

| 模块 | 做什么 |
|------|--------|
| **GitHub Learning** | 扫描 GitHub Trending，发现高价值开源项目 |
| **Twitter AI Radar** | 追踪美中日三国 AI 领域关键人物动态 |
| **Money Signal** | 从上述信息中提炼商业机会 |

GitHub + Twitter 是信息输入层，Money Signal 是处理层。

## 项目结构

```
CLAUDE.md            # Alan 的灵魂（人格 + 工作协议）
context/             # 产品和用户上下文
.features/           # 三个功能模块的记忆和数据
  github-learning/
  twitter-ai-radar/
  money-signal/
loop/                # 循环运行状态
scheduler/           # 定时任务编排
  run-task.sh        # 多 Agent 编排器
  agents/            # 4 个 Agent prompt
  send-email.sh      # 邮件通知
```

## 使用方式

手动触发（在 Claude Code 中）：

```
/radar    — 完整循环：GitHub → Twitter → 信号分析
/github   — 只扫 GitHub
/twitter  — 只看 Twitter
/signal   — 只分析赚钱信号
```

自动触发：通过 macOS launchd 定时执行多 Agent 并行编排。

## 设计哲学

- **递弱代偿** — 人的注意力有限，用 AI 的计算能力补偿
- **信号优先于噪音** — 不堆信息量，只说值得说的
- **文件即记忆** — Agent 没有连续记忆，用文件系统代偿

## 作者

- **[@luke](https://x.com/lukeliu95)**