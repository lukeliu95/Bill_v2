#!/bin/bash
# Bill_v2 邮件发送工具
# 通过 AppleScript 调用 Mail.app 发送纯文本格式雷达简报
# 用法: bash scheduler/send-email.sh [摘要文件路径]

PROJECT_DIR="/Users/lukeliu/Desktop/Cline/Bill_v2"
TO_EMAIL="liu.conjure.cn@gmail.com"

# 读取摘要内容
SUMMARY_FILE="${1:-$PROJECT_DIR/loop/last-run-summary.md}"

if [ ! -f "$SUMMARY_FILE" ]; then
    echo "摘要文件不存在: $SUMMARY_FILE"
    exit 1
fi

TODAY=$(date '+%Y-%m-%d')
SUBJECT="Alan 雷达简报 | $TODAY"

# Markdown → 可读纯文本转换（去掉 #、**、| 等格式符号）
CONTENT=$(python3 "$PROJECT_DIR/scheduler/md2plain.py" < "$SUMMARY_FILE" 2>/dev/null)

# 如果转换失败，回退为原始内容
if [ $? -ne 0 ] || [ -z "$CONTENT" ]; then
    CONTENT=$(cat "$SUMMARY_FILE")
fi

# 转义 AppleScript 中的特殊字符（反斜杠和引号）
CONTENT=$(echo "$CONTENT" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g')

# 通过 AppleScript 用 Mail.app 发送
osascript -e "
tell application \"Mail\"
    set msgContent to \"$CONTENT\"
    set newMessage to make new outgoing message with properties {subject:\"$SUBJECT\", content:msgContent, visible:false}
    tell newMessage
        make new to recipient at end of to recipients with properties {address:\"$TO_EMAIL\"}
    end tell
    send newMessage
end tell
"

EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "邮件已发送: $SUBJECT -> $TO_EMAIL"
else
    echo "邮件发送失败 (exit code: $EXIT_CODE)"
fi
exit $EXIT_CODE
