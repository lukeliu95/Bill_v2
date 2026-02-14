# launchd 定时任务配置记录

> 操作时间：2026-02-13 20:47（初始），22:05（目录重构），2026-02-14（多 Agent 架构）
> 操作人：Alan

## 背景

之前用 cron 配置定时任务，但执行失败。原因有两个：
1. cron 环境带 `CLAUDECODE` 变量，claude 误判为嵌套会话拒绝启动
2. macOS 上 cron 不够可靠（休眠不补跑、权限限制等）

## 方案：改用 launchd

macOS 原生任务调度器，优势：
- 电脑休眠醒来后自动补跑错过的任务
- 更好的环境变量控制
- 更好的日志管理

## 架构：多 Agent 编排（2026-02-14 升级）

从单 agent 串行升级为多 agent 并行架构：

```
Phase 1（并行）: GitHub Scout + Twitter Radar
          ↓ 门控：至少一个成功
Phase 2（串行）: Signal Analyzer（读 Phase 1 输出）
          ↓
Phase 3（串行）: Briefing Generator（汇总 → 简报 → 更新状态）
          ↓
      run-task.sh 发通知 + 发邮件（bash 层）
```

### Agent 文件

| 文件 | 职责 | 工具权限 |
|------|------|----------|
| `scheduler/agents/github-scout.md` | GitHub 趋势扫描 | WebSearch, WebFetch, Read, Write, Edit, Glob, Grep |
| `scheduler/agents/twitter-radar.md` | Twitter/X AI 动态 | WebSearch, WebFetch, Read, Write, Edit, Glob, Grep |
| `scheduler/agents/signal-analyzer.md` | 赚钱信号分析 | Read, Write, Edit, Glob, Grep |
| `scheduler/agents/briefing-generator.md` | 简报生成 + 状态更新 | Read, Write, Edit, Glob, Grep |

### Agent 间通信

- 通过文件系统通信，不通过内存
- 每个 agent 完成后写 `loop/agents/{name}.status`
- Signal Analyzer 读 status 文件发现 Phase 1 输出路径
- Briefing Generator 读所有 status + data，汇总写入 state.md
- 写冲突避免：每个 agent 只写自己 feature 的文件

### 错误处理

- Phase 1 两个 scout 独立运行，一个失败不影响另一个
- Phase 1 → Phase 2 门控：至少一个 scout 成功才跑 Signal Analyzer
- 每个 agent 10 分钟超时（`timeout 600`）
- 崩溃检测：orchestrator 检查 status 文件，缺失则写 crashed
- Briefing Generator 始终运行（即使信号分析失败也报告状态）

## 目录结构

```
scheduler/                  ← 定时任务系统（脚本 + 配置）
  run-task.sh              ← 多 Agent 编排器
  send-email.sh            ← 邮件发送
  setup-launchd.md         ← 本文件，配置记录
  com.bill-v2.radar.plist  ← plist 备份
  agents/                  ← Agent prompt 文件
    github-scout.md
    twitter-radar.md
    signal-analyzer.md
    briefing-generator.md

logs/                       ← 纯日志
  task-history.log         ← 执行历史
  agent-github-scout.log   ← GitHub Scout 输出
  agent-twitter-radar.log  ← Twitter Radar 输出
  agent-signal-analyzer.log ← Signal Analyzer 输出
  agent-briefing-generator.log ← Briefing Generator 输出
  launchd-stdout.log       ← launchd stdout
  launchd-stderr.log       ← launchd stderr

loop/
  state.md                 ← 全局状态（只有 Briefing Generator 写）
  last-run.log             ← 所有 agent 合并输出
  last-run-summary.md      ← 一句话摘要（用于通知 + 邮件）
  agents/                  ← Agent 状态文件（每次运行刷新）
    github-scout.status
    twitter-radar.status
    signal-analyzer.status
    briefing-generator.status
```

## 管理命令

```bash
# 查看服务状态
launchctl list | grep bill

# 停止服务
launchctl unload ~/Library/LaunchAgents/com.bill-v2.radar.plist

# 重新加载（修改 plist 后）
launchctl unload ~/Library/LaunchAgents/com.bill-v2.radar.plist
launchctl load ~/Library/LaunchAgents/com.bill-v2.radar.plist

# 手动触发完整测试
bash scheduler/run-task.sh radar

# 单独测试某个 agent（手动调用）
cd /Users/lukeliu/Desktop/Cline/Bill_v2
CURRENT_DATE=$(date '+%Y-%m-%d')
PROMPT=$(sed "s/\$CURRENT_DATE/$CURRENT_DATE/g" scheduler/agents/github-scout.md)
claude -p "$PROMPT" --allowedTools 'WebSearch,WebFetch,Read,Write,Edit,Glob,Grep'

# 查看各 agent 运行状态
cat loop/agents/*.status

# 查看某个 agent 的详细日志
cat logs/agent-github-scout.log
```

## 测试结果
