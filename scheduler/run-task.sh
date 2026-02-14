#!/bin/bash
# Bill_v2 多 Agent 编排器
# 由 launchd 每小时整点触发，执行多阶段 radar 循环
# Phase 1（并行）: GitHub Scout + Twitter Radar
# Phase 2（串行）: Signal Analyzer
# Phase 3（串行）: Briefing Generator
# 如果电脑休眠错过了，醒来后会自动补跑

PROJECT_DIR="/Users/lukeliu/Desktop/Cline/Bill_v2"
LOG_FILE="$PROJECT_DIR/logs/task-history.log"
LAST_RUN_LOG="$PROJECT_DIR/loop/last-run.log"
AGENTS_DIR="$PROJECT_DIR/scheduler/agents"
STATUS_DIR="$PROJECT_DIR/loop/agents"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
CURRENT_DATE=$(date '+%Y-%m-%d')
CURRENT_HOUR=$(date '+%H')
RUN_ID="${CURRENT_DATE}-${CURRENT_HOUR}00"
TASK_NAME="${1:-radar}"

# 关键：清除 CLAUDECODE 变量，避免嵌套会话检测
unset CLAUDECODE

# 确保 PATH 包含 claude 命令
export PATH="/Users/lukeliu/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# macOS 通知函数
notify() {
  local title="$1"
  local message="$2"
  osascript -e "display notification \"$message\" with title \"$title\" sound name \"Glass\""
}

# 自动压缩 data/ 目录
# 当某个 feature 的 data/ 超过 20 个文件时，将旧文件合并为周摘要
compress_data() {
  local FEATURE_DIR="$1"
  local DATA_DIR="$FEATURE_DIR/data"
  local FILE_COUNT=$(ls "$DATA_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ')

  if [ "$FILE_COUNT" -gt 20 ]; then
    echo "[$(date '+%H:%M:%S')] 压缩 $DATA_DIR ($FILE_COUNT 个文件)" >> "$LOG_FILE"
    # 保留最近 10 个文件，旧的移入 archive/
    mkdir -p "$DATA_DIR/archive"
    ls -t "$DATA_DIR"/*.md | tail -n +11 | while read f; do
      mv "$f" "$DATA_DIR/archive/"
    done
    local ARCHIVED=$(ls "$DATA_DIR/archive/"*.md 2>/dev/null | wc -l | tr -d ' ')
    echo "  已归档 $ARCHIVED 个旧文件到 archive/" >> "$LOG_FILE"
  fi
}

# 运行单个 agent
# 用法: run_agent <agent-name>
# 读取 scheduler/agents/<name>.md 作为 prompt，替换变量
# 输出写入 logs/agent-<name>.log
run_agent() {
  local NAME="$1"
  local PROMPT_FILE="$AGENTS_DIR/${NAME}.md"
  local AGENT_LOG="$PROJECT_DIR/logs/agent-${NAME}.log"
  local START_TIME=$(date '+%Y-%m-%d %H:%M:%S')

  echo "[$START_TIME] Agent 开始: $NAME" >> "$LOG_FILE"

  if [ ! -f "$PROMPT_FILE" ]; then
    echo "[$START_TIME] Agent 失败: $NAME — prompt 文件不存在: $PROMPT_FILE" >> "$LOG_FILE"
    echo "timestamp: $START_TIME" > "$STATUS_DIR/${NAME}.status"
    echo "status: failed" >> "$STATUS_DIR/${NAME}.status"
    echo "reason: prompt file not found" >> "$STATUS_DIR/${NAME}.status"
    return 1
  fi

  # 读取 prompt 并替换变量
  local PROMPT
  PROMPT=$(sed -e "s/\$CURRENT_DATE/$CURRENT_DATE/g" -e "s/\$RUN_ID/$RUN_ID/g" "$PROMPT_FILE")

  # 根据 agent 类型设置 allowedTools
  local ALLOWED_TOOLS
  case "$NAME" in
    github-scout|twitter-radar)
      ALLOWED_TOOLS='WebSearch,WebFetch,Read,Write,Edit,Glob,Grep'
      ;;
    signal-analyzer|briefing-generator)
      ALLOWED_TOOLS='Read,Write,Edit,Glob,Grep'
      ;;
    *)
      ALLOWED_TOOLS='Read,Write,Edit,Glob,Grep'
      ;;
  esac

  # 执行 agent（10 分钟超时，macOS 无 timeout 命令，用后台进程 + wait 实现）
  > "$AGENT_LOG"
  claude -p "$PROMPT" \
    --allowedTools "$ALLOWED_TOOLS" \
    >> "$AGENT_LOG" 2>&1 &
  local AGENT_PID=$!

  # 超时守护：10 分钟后杀掉 agent 进程
  (
    sleep 600
    if kill -0 "$AGENT_PID" 2>/dev/null; then
      kill "$AGENT_PID" 2>/dev/null
      echo "[$NAME] 超时 (600s)，已终止" >> "$LOG_FILE"
    fi
  ) &
  local WATCHDOG_PID=$!

  wait "$AGENT_PID"
  local EXIT_CODE=$?

  # 清理超时守护进程
  kill "$WATCHDOG_PID" 2>/dev/null
  wait "$WATCHDOG_PID" 2>/dev/null

  local END_TIME=$(date '+%Y-%m-%d %H:%M:%S')
  echo "[$END_TIME] Agent 完成: $NAME (exit: $EXIT_CODE)" >> "$LOG_FILE"
  echo "  开始: $START_TIME | 结束: $END_TIME" >> "$LOG_FILE"

  return $EXIT_CODE
}

# 检查 agent status 文件是否标记成功
check_agent_success() {
  local NAME="$1"
  local STATUS_FILE="$STATUS_DIR/${NAME}.status"
  if [ -f "$STATUS_FILE" ] && grep -q "status: success" "$STATUS_FILE"; then
    return 0
  fi
  return 1
}

# 为崩溃的 agent 补写 status
write_crashed_status() {
  local NAME="$1"
  local STATUS_FILE="$STATUS_DIR/${NAME}.status"
  if [ ! -f "$STATUS_FILE" ]; then
    echo "timestamp: $(date '+%Y-%m-%d %H:%M:%S')" > "$STATUS_FILE"
    echo "status: crashed" >> "$STATUS_FILE"
    echo "reason: agent process exited without writing status file" >> "$STATUS_FILE"
  fi
}

# ============================================================
# 主流程
# ============================================================

echo "========================================" >> "$LOG_FILE"
echo "[$TIMESTAMP] 多 Agent 编排开始: $TASK_NAME (run: $RUN_ID)" >> "$LOG_FILE"
echo "触发方式: $([ -t 0 ] && echo '手动' || echo 'launchd')" >> "$LOG_FILE"

cd "$PROJECT_DIR"

# 清空上次运行日志
> "$LAST_RUN_LOG"

# 清理旧 status 文件
rm -f "$STATUS_DIR"/*.status

# ============================================================
# 预处理：自动压缩过大的 data/ 目录
# ============================================================

compress_data "$PROJECT_DIR/.features/github-learning"
compress_data "$PROJECT_DIR/.features/twitter-ai-radar"
compress_data "$PROJECT_DIR/.features/money-signal"

# ============================================================
# Phase 1: 并行 — GitHub Scout + Twitter Radar
# ============================================================

echo "" >> "$LOG_FILE"
echo "--- Phase 1: 并行扫描 ---" >> "$LOG_FILE"

run_agent "github-scout" &
PID_GH=$!

run_agent "twitter-radar" &
PID_TW=$!

# 等待两个 agent 完成
wait $PID_GH
EXIT_GH=$?
wait $PID_TW
EXIT_TW=$?

# 补写崩溃 agent 的 status
write_crashed_status "github-scout"
write_crashed_status "twitter-radar"

# Phase 1 门控：至少一个成功才继续
GH_OK=false
TW_OK=false
check_agent_success "github-scout" && GH_OK=true
check_agent_success "twitter-radar" && TW_OK=true

echo "Phase 1 结果: github-scout=$GH_OK, twitter-radar=$TW_OK" >> "$LOG_FILE"

if [ "$GH_OK" = false ] && [ "$TW_OK" = false ]; then
  echo "Phase 1 全部失败，跳过 Phase 2，直接进入 Phase 3 报告状态" >> "$LOG_FILE"
else
  # ============================================================
  # Phase 2: 串行 — Signal Analyzer
  # ============================================================

  echo "" >> "$LOG_FILE"
  echo "--- Phase 2: 信号分析 ---" >> "$LOG_FILE"

  run_agent "signal-analyzer"
  EXIT_SA=$?
  write_crashed_status "signal-analyzer"
fi

# ============================================================
# Phase 3: 串行 — Briefing Generator（始终运行）
# ============================================================

echo "" >> "$LOG_FILE"
echo "--- Phase 3: 简报生成 ---" >> "$LOG_FILE"

run_agent "briefing-generator"
EXIT_BG=$?
write_crashed_status "briefing-generator"

# ============================================================
# 通知 + 邮件
# ============================================================

END_TIME=$(date '+%Y-%m-%d %H:%M:%S')
SUMMARY_FILE="$PROJECT_DIR/loop/last-run-summary.md"

if [ -f "$SUMMARY_FILE" ]; then
  SUMMARY=$(head -c 200 "$SUMMARY_FILE")
  notify "Alan 雷达扫描完成" "$SUMMARY"
  # 发送邮件简报
  bash "$PROJECT_DIR/scheduler/send-email.sh" "$SUMMARY_FILE" >> "$LOG_FILE" 2>&1
else
  notify "Alan 雷达扫描完成" "简报文件未生成，查看 logs/ 了解详情"
fi

# 汇总各 agent 日志到 last-run.log
echo "=== 多 Agent 运行汇总 ($RUN_ID) ===" >> "$LAST_RUN_LOG"
echo "运行时间: $TIMESTAMP → $END_TIME" >> "$LAST_RUN_LOG"
echo "" >> "$LAST_RUN_LOG"
for AGENT_NAME in github-scout twitter-radar signal-analyzer briefing-generator; do
  AGENT_LOG="$PROJECT_DIR/logs/agent-${AGENT_NAME}.log"
  if [ -f "$AGENT_LOG" ]; then
    echo "--- $AGENT_NAME ---" >> "$LAST_RUN_LOG"
    cat "$AGENT_LOG" >> "$LAST_RUN_LOG"
    echo "" >> "$LAST_RUN_LOG"
  fi
done

echo "[$END_TIME] 多 Agent 编排完成 ($RUN_ID)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
