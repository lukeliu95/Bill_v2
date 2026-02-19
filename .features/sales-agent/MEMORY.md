# Sales Agent
> 统一销售智能代理：ICP → 匹配 → 报告 → 联系方式
> 更新：2026-02-17-120000

## 当前状态

初始版本。三条管线（Pipeline A/B/C）已定义，ContactDiscoveryCollector 已集成到报告生成器。

## 快速索引

- 2026-02-17: 初始创建。ContactDiscoveryCollector + sales-agent SKILL.md + CLAUDE.md 路由更新

## 核心文件

- `.claude/skills/sales-agent/SKILL.md` — 管线定义
- `.claude/skills/enterprise_report_generator/collectors/contact_discovery_collector.py` — 联系方式收集器
- `.claude/skills/enterprise_report_generator/collectors/contact_models.py` — 数据模型
- `.claude/skills/enterprise_report_generator/contact_discovery.py` — CLI 入口
- `.features/sales-agent/data/` — 管线运行状态

## Gotchas

- ContactDiscovery 依赖 SalesIntel 的 LinkedIn 数据，所以在报告生成器中是第二阶段执行
- BrightData LinkedIn Person Profile 获取 email/phone 成功率低（日本企业多数不公开）
- 批量报告生成需顺序执行，避免 API 限流
