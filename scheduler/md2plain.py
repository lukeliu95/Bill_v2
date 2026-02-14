#!/usr/bin/env python3
"""
Markdown → 纯文本邮件转换器
去掉 Markdown 格式符号，保留可读结构。
用法: python3 md2plain.py < input.md
"""

import sys
import re


def convert(md_text):
    lines = md_text.split('\n')
    out = []

    for line in lines:
        stripped = line.strip()

        # 表格分隔行 |---|---| → 跳过
        if re.match(r'^\|[-\s|:]+\|$', stripped):
            continue

        # 表格行 | a | b | → 对齐输出
        if stripped.startswith('|') and stripped.endswith('|'):
            cells = [c.strip() for c in stripped.strip('|').split('|')]
            out.append('  '.join(f'{c:<20}' for c in cells))
            continue

        # # 标题 → 大写风格 + 下划线
        m = re.match(r'^(#{1,3})\s+(.+)', stripped)
        if m:
            level = len(m.group(1))
            title = re.sub(r'\*\*(.+?)\*\*', r'\1', m.group(2))
            if level == 1:
                out.append('')
                out.append(f'{"=" * 50}')
                out.append(f'  {title}')
                out.append(f'{"=" * 50}')
            elif level == 2:
                out.append('')
                out.append(f'▸ {title}')
                out.append(f'  {"-" * (len(title) + 4)}')
            else:
                out.append('')
                out.append(f'  【{title}】')
            continue

        # > 引用 → 缩进
        if stripped.startswith('>'):
            text = stripped[1:].strip()
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
            out.append(f'  | {text}')
            continue

        # 有序列表
        m = re.match(r'^(\d+)\.\s+(.+)', stripped)
        if m:
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', m.group(2))
            out.append(f'  {m.group(1)}. {text}')
            continue

        # 无序列表 - → •
        if stripped.startswith('- '):
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', stripped[2:])
            out.append(f'  • {text}')
            continue

        # 普通行：去掉 **bold** 标记
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', stripped)
        # 去掉 `code` 标记
        text = re.sub(r'`([^`]+)`', r'\1', text)
        out.append(text)

    return '\n'.join(out)


if __name__ == '__main__':
    print(convert(sys.stdin.read()))
