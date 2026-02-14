---
name: enterprise-report-generator
description: |
  对目标企业生成深度营业报告。输入企业名、法人番号、官网URL，
  自动采集基本信息、销售情报、商机信号，经 AI 分析后输出 JSON + Markdown 报告。
  报告保存至 output/{企業名}/ 目录。

  触发场景：用户说"帮我生成报告"、"调查一下XX公司"、"出一份营业报告"时使用此技能。
---

# Enterprise Report Generator

对目标企业生成深度营业报告（基本信息 + 销售情报 + 商机信号 + AI 分析）。

## 运行方式

通过 Bash 工具执行 Python 模块：

```bash
PYTHONPATH="/Users/lukeliu/Desktop/Cline/Bill_v2/.claude/skills:$PYTHONPATH" \
  python3 -m enterprise_report_generator.main \
    --company "企业名称" \
    --number "法人番号" \
    --url "官网URL"
```

### 参数说明

| 参数 | 必须 | 说明 |
|------|------|------|
| `--company` / `-c` | 是 | 企业名称 |
| `--number` / `-n` | 是 | 法人番号（13位） |
| `--url` / `-u` | 是 | 官网 URL |
| `--address` / `-a` | 否 | 地址 |
| `--no-cache` | 否 | 不使用缓存 |
| `--no-save` | 否 | 不保存到文件 |
| `--output` / `-o` | 否 | 指定输出文件路径 |

### 可选参数示例

```bash
# 指定地址 + 不使用缓存
PYTHONPATH="/Users/lukeliu/Desktop/Cline/Bill_v2/.claude/skills:$PYTHONPATH" \
  python3 -m enterprise_report_generator.main \
    --company "株式会社HRBrain" \
    --number "3010401123536" \
    --url "https://www.hrbrain.co.jp/" \
    --address "東京都品川区" \
    --no-cache
```

## 输出

报告保存在项目根目录 `output/` 下：
- `{企業名}_{法人番号}_{timestamp}.json` — 结构化数据
- `{企業名}_{法人番号}_{timestamp}.md` — Markdown 可读报告

## 依赖

需要以下环境变量（配置在项目根目录 `.env` 中）：
- `SERPER_API_KEY` — Serper 搜索 API
- `GBIZINFO_API_TOKEN` — gBizINFO 企业数据 API
- `GEMINI_API_KEY` — Gemini AI 分析
- `BRIGHT_DATA_API_KEY`（可选）— LinkedIn 数据采集
- `BRIGHT_DATA_USER_ID`（可选）— LinkedIn 数据采集

## 数据流

```
输入（企业名 + 法人番号 + URL）
  ↓
并行采集：基本信息 / 销售情报 / 商机信号
  ↓
AI 分析 → 生成报告
  ↓
质量检查 → 输出文件
  ↓
更新 .features/enterprise-report/MEMORY.md
```
