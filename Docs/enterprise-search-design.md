# GTM Agent 企業検索システム — 実装設計書

> 本文档面向 Claude Code。请按照本文档完成编码实现。

---

## 目标

为 AI Agent 提供两个 CLI 命令，在百万级日本企业 MD 文件中实现毫秒级检索。

- `company-search` — 结构化字段查询（地域、行业、规模等）
- `company-grep` — 全文检索（关键词、布尔逻辑、正则、BM25 排序）

底层统一使用 **一个 SQLite 数据库文件**（含 FTS5 全文索引）。

---

## 系统总览

```
数据流：

  MD 文件（真相源）
       │
       ▼
  sync 脚本（解析 MD → 写入 SQLite）
       │
       ▼
  SQLite（companies.db）
    ├── companies 表 — frontmatter 结构化字段
    └── docs 表（FTS5）— 全文内容，倒排索引
       │
       ▼
  CLI 命令（Agent 调用）
    ├── company-search — 查 companies 表
    └── company-grep   — 查 docs 表
```

Agent 还可以用原生 `cat /companies/JP-XXXXX.md` 读取单个企业详情。

---

## 1. 数据源：MD 文件格式

每个企业一个 MD 文件，路径为 `/companies/{company_id}.md`。

文件结构：

```markdown
---
company_id: JP-00123
name_ja: 株式会社Example
name_en: Example Inc.
industry: SaaS
location: 東京都渋谷区
employees: 35
revenue: 500000000
founded: 2018
funding_stage: Series A
tech_stack: Python, AWS, React
tags: AI, DX推進, スタートアップ
dr_score: 78
---

## 企業概要

株式会社Example は東京都渋谷区に本社を置く SaaS 企業で...

## 事業内容

主に中小企業向けの DX 推進ソリューションを提供...

## 最新ニュース

2024年3月、シリーズA で5億円の資金調達を完了...

## 採用情報

現在エンジニアを積極採用中...
```

---

## 2. SQLite スキーマ

数据库文件：`companies.db`

### 2.1 companies 表（结构化查询用）

```sql
CREATE TABLE companies (
    company_id   TEXT PRIMARY KEY,
    name_ja      TEXT NOT NULL,
    name_en      TEXT,
    industry     TEXT,
    location     TEXT,
    employees    INTEGER,
    revenue      INTEGER,          -- 日元，整数
    founded      INTEGER,          -- 年份
    funding_stage TEXT,
    tech_stack   TEXT,             -- 逗号分隔
    tags         TEXT,             -- 逗号分隔
    dr_score     REAL DEFAULT 0,
    file_path    TEXT NOT NULL     -- MD 文件路径
);

-- 索引（按查询频率建）
CREATE INDEX idx_location   ON companies(location);
CREATE INDEX idx_industry   ON companies(industry);
CREATE INDEX idx_employees  ON companies(employees);
CREATE INDEX idx_revenue    ON companies(revenue);
CREATE INDEX idx_founded    ON companies(founded);
CREATE INDEX idx_dr_score   ON companies(dr_score);
CREATE INDEX idx_funding    ON companies(funding_stage);
```

### 2.2 docs 表（FTS5 全文检索用）

```sql
CREATE VIRTUAL TABLE docs USING fts5(
    company_id,
    name_ja,
    body,                          -- MD 文件 body 全文（去掉 frontmatter）
    tokenize='icu ja'              -- ICU 日文分词器
);
```

> **注意**：ICU tokenizer 需要 SQLite 编译时启用 `SQLITE_ENABLE_ICU`。如果环境不支持，退回到 `tokenize='unicode61'`，对日文分词效果会差一些但可用。

### 2.3 验证环境是否支持

实现前先跑以下检查：

```python
import sqlite3

db = sqlite3.connect(":memory:")

# 检查 FTS5
try:
    db.execute("CREATE VIRTUAL TABLE _test USING fts5(content)")
    db.execute("DROP TABLE _test")
    print("FTS5: OK")
except:
    print("FTS5: NOT AVAILABLE — 需要安装支持 FTS5 的 SQLite")

# 检查 ICU tokenizer
try:
    db.execute("CREATE VIRTUAL TABLE _test USING fts5(content, tokenize='icu ja')")
    db.execute("DROP TABLE _test")
    print("ICU tokenizer: OK")
except:
    print("ICU tokenizer: NOT AVAILABLE — 退回到 unicode61")
```

---

## 3. Sync 脚本：MD → SQLite

文件：`sync_db.py`

### 职责

1. 扫描 `/companies/` 目录下所有 `.md` 文件
2. 解析每个文件的 YAML frontmatter → `companies` 表
3. 提取 body 文本（frontmatter 之后的内容）→ `docs` 表
4. 支持全量重建和增量更新

### 实现要点

```python
#!/usr/bin/env python3
"""sync_db.py — 将 MD 文件同步到 SQLite"""

import os
import sys
import yaml
import sqlite3
import hashlib
from pathlib import Path

COMPANIES_DIR = "/companies"
DB_PATH = "companies.db"

def parse_md(filepath: str) -> tuple[dict, str]:
    """
    解析 MD 文件，返回 (frontmatter_dict, body_text)。
    
    frontmatter 是 --- 和 --- 之间的 YAML。
    body 是第二个 --- 之后的所有内容。
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 分割 frontmatter 和 body
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm = yaml.safe_load(parts[1])
            body = parts[2].strip()
            return fm or {}, body
    
    return {}, content.strip()


def init_db(db: sqlite3.Connection):
    """建表。如果表已存在则跳过。"""
    db.executescript("""
        CREATE TABLE IF NOT EXISTS companies (
            company_id    TEXT PRIMARY KEY,
            name_ja       TEXT NOT NULL,
            name_en       TEXT,
            industry      TEXT,
            location      TEXT,
            employees     INTEGER,
            revenue       INTEGER,
            founded       INTEGER,
            funding_stage TEXT,
            tech_stack    TEXT,
            tags          TEXT,
            dr_score      REAL DEFAULT 0,
            file_path     TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_location   ON companies(location);
        CREATE INDEX IF NOT EXISTS idx_industry   ON companies(industry);
        CREATE INDEX IF NOT EXISTS idx_employees  ON companies(employees);
        CREATE INDEX IF NOT EXISTS idx_revenue    ON companies(revenue);
        CREATE INDEX IF NOT EXISTS idx_founded    ON companies(founded);
        CREATE INDEX IF NOT EXISTS idx_dr_score   ON companies(dr_score);
        CREATE INDEX IF NOT EXISTS idx_funding    ON companies(funding_stage);
    """)
    
    # FTS5 表 — 先尝试 ICU，失败则用 unicode61
    try:
        db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS docs 
            USING fts5(company_id, name_ja, body, tokenize='icu ja')
        """)
    except sqlite3.OperationalError:
        db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS docs 
            USING fts5(company_id, name_ja, body, tokenize='unicode61')
        """)


def sync_file(db: sqlite3.Connection, filepath: str):
    """同步单个 MD 文件到数据库。"""
    fm, body = parse_md(filepath)
    
    cid = fm.get("company_id")
    if not cid:
        print(f"SKIP (no company_id): {filepath}", file=sys.stderr)
        return
    
    # UPSERT companies 表
    db.execute("""
        INSERT INTO companies 
            (company_id, name_ja, name_en, industry, location, employees,
             revenue, founded, funding_stage, tech_stack, tags, dr_score, file_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(company_id) DO UPDATE SET
            name_ja=excluded.name_ja, name_en=excluded.name_en,
            industry=excluded.industry, location=excluded.location,
            employees=excluded.employees, revenue=excluded.revenue,
            founded=excluded.founded, funding_stage=excluded.funding_stage,
            tech_stack=excluded.tech_stack, tags=excluded.tags,
            dr_score=excluded.dr_score, file_path=excluded.file_path
    """, (
        cid,
        fm.get("name_ja", ""),
        fm.get("name_en"),
        fm.get("industry"),
        fm.get("location"),
        fm.get("employees"),
        fm.get("revenue"),
        fm.get("founded"),
        fm.get("funding_stage"),
        fm.get("tech_stack"),
        fm.get("tags"),
        fm.get("dr_score", 0),
        filepath,
    ))
    
    # UPSERT docs 表（FTS5 不支持 ON CONFLICT，先删后插）
    db.execute("DELETE FROM docs WHERE company_id = ?", (cid,))
    db.execute(
        "INSERT INTO docs (company_id, name_ja, body) VALUES (?, ?, ?)",
        (cid, fm.get("name_ja", ""), body),
    )


def sync_all(full_rebuild: bool = False):
    """同步全部 MD 文件。"""
    db = sqlite3.connect(DB_PATH)
    
    if full_rebuild:
        db.executescript("DROP TABLE IF EXISTS companies; DROP TABLE IF EXISTS docs;")
    
    init_db(db)
    
    md_files = list(Path(COMPANIES_DIR).glob("*.md"))
    print(f"Found {len(md_files)} MD files")
    
    for i, fp in enumerate(md_files):
        sync_file(db, str(fp))
        if (i + 1) % 1000 == 0:
            db.commit()
            print(f"  synced {i + 1}/{len(md_files)}")
    
    db.commit()
    db.close()
    print("Sync complete.")


if __name__ == "__main__":
    rebuild = "--rebuild" in sys.argv
    sync_all(full_rebuild=rebuild)
```

### 运行方式

```bash
# 全量重建
python sync_db.py --rebuild

# 增量同步（默认，UPSERT）
python sync_db.py
```

---

## 4. CLI 命令一：company-search

文件：`company_search.py`（安装为 `company-search` 命令）

### 功能

对 `companies` 表做结构化条件筛选。

### 接口定义

```
company-search [OPTIONS]

OPTIONS:
  --location TEXT        所在地过滤（前缀匹配，如 "東京" 匹配 "東京都渋谷区"）
  --industry TEXT        行业过滤（精确匹配）
  --min-employees INT    最小员工数
  --max-employees INT    最大员工数
  --min-revenue INT      最小营收（日元）
  --max-revenue INT      最大营收（日元）
  --funding-stage TEXT   融资阶段（精确匹配）
  --founded-after INT    成立年份 >= 此值
  --founded-before INT   成立年份 <= 此值
  --tags TEXT            标签过滤（包含匹配，逗号分隔视为 OR）
  --tech TEXT            技术栈过滤（包含匹配）
  --sort TEXT            排序字段（默认 dr_score）
  --desc                 降序排列
  --limit INT            最大返回数（默认 50）
  --count                仅返回匹配数量
  --ids-only             仅返回 company_id 列表（用于管道传递）
```

### 输出格式

标准模式（TSV，方便 Agent 解析）：

```
ID	NAME	INDUSTRY	LOCATION	EMPLOYEES	DR_SCORE
JP-00123	株式会社Example	SaaS	東京都渋谷区	35	78
JP-00456	ABCテック株式会社	SaaS	東京都港区	120	65
---
Found: 187 companies (showing top 50)
```

Count 模式：
```
Count: 187
```

IDs 模式：
```
JP-00123
JP-00456
JP-00789
```

### 实现要点

```python
#!/usr/bin/env python3
"""company-search: 企业结构化检索"""

import argparse
import sqlite3
import sys

DB_PATH = "companies.db"


def build_query(args) -> tuple[str, list]:
    """根据命令行参数动态构建 SQL WHERE 子句。"""
    conditions = []
    params = []

    if args.location:
        conditions.append("location LIKE ?")
        params.append(f"{args.location}%")
    
    if args.industry:
        conditions.append("industry = ?")
        params.append(args.industry)

    if args.min_employees is not None:
        conditions.append("employees >= ?")
        params.append(args.min_employees)

    if args.max_employees is not None:
        conditions.append("employees <= ?")
        params.append(args.max_employees)

    if args.min_revenue is not None:
        conditions.append("revenue >= ?")
        params.append(args.min_revenue)

    if args.max_revenue is not None:
        conditions.append("revenue <= ?")
        params.append(args.max_revenue)

    if args.funding_stage:
        conditions.append("funding_stage = ?")
        params.append(args.funding_stage)

    if args.founded_after is not None:
        conditions.append("founded >= ?")
        params.append(args.founded_after)

    if args.founded_before is not None:
        conditions.append("founded <= ?")
        params.append(args.founded_before)

    if args.tags:
        # tags 字段是逗号分隔的字符串，用 LIKE 做包含匹配
        # 多个 tag 之间是 OR 关系
        tag_list = [t.strip() for t in args.tags.split(",")]
        tag_conditions = ["tags LIKE ?" for _ in tag_list]
        conditions.append(f"({' OR '.join(tag_conditions)})")
        params.extend([f"%{t}%" for t in tag_list])

    if args.tech:
        conditions.append("tech_stack LIKE ?")
        params.append(f"%{args.tech}%")

    where = " AND ".join(conditions) if conditions else "1=1"
    return where, params


def main():
    parser = argparse.ArgumentParser(description="企业结构化检索")
    parser.add_argument("--location")
    parser.add_argument("--industry")
    parser.add_argument("--min-employees", type=int)
    parser.add_argument("--max-employees", type=int)
    parser.add_argument("--min-revenue", type=int)
    parser.add_argument("--max-revenue", type=int)
    parser.add_argument("--funding-stage")
    parser.add_argument("--founded-after", type=int)
    parser.add_argument("--founded-before", type=int)
    parser.add_argument("--tags")
    parser.add_argument("--tech")
    parser.add_argument("--sort", default="dr_score")
    parser.add_argument("--desc", action="store_true")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--count", action="store_true")
    parser.add_argument("--ids-only", action="store_true")
    args = parser.parse_args()

    # 白名单校验 sort 字段，防止 SQL 注入
    allowed_sorts = {
        "dr_score", "employees", "revenue", "founded", "name_ja", "company_id"
    }
    sort_field = args.sort if args.sort in allowed_sorts else "dr_score"
    sort_dir = "DESC" if args.desc else "ASC"

    where, params = build_query(args)

    db = sqlite3.connect(DB_PATH)

    if args.count:
        row = db.execute(
            f"SELECT COUNT(*) FROM companies WHERE {where}", params
        ).fetchone()
        print(f"Count: {row[0]}")
        return

    if args.ids_only:
        sql = f"SELECT company_id FROM companies WHERE {where} ORDER BY {sort_field} {sort_dir} LIMIT ?"
    else:
        sql = f"""
            SELECT company_id, name_ja, industry, location, employees, dr_score 
            FROM companies WHERE {where} 
            ORDER BY {sort_field} {sort_dir} LIMIT ?
        """

    params.append(args.limit)
    rows = db.execute(sql, params).fetchall()

    if args.ids_only:
        for row in rows:
            print(row[0])
    else:
        print("ID\tNAME\tINDUSTRY\tLOCATION\tEMPLOYEES\tDR_SCORE")
        for row in rows:
            print(f"{row[0]}\t{row[1]}\t{row[2]}\t{row[3]}\t{row[4]}\t{row[5]}")
        
        total = db.execute(
            f"SELECT COUNT(*) FROM companies WHERE {where}", params[:-1]
        ).fetchone()[0]
        print(f"---\nFound: {total} companies (showing top {min(args.limit, total)})")

    db.close()


if __name__ == "__main__":
    main()
```

---

## 5. CLI 命令二：company-grep

文件：`company_grep.py`（安装为 `company-grep` 命令）

### 功能

对 `docs` 表（FTS5）做全文检索，替代 `grep -r`。

### 接口定义

```
company-grep [QUERY] [OPTIONS]

POSITIONAL:
  QUERY                 FTS5 搜索表达式（支持 AND/OR/NOT/短语/前缀）

OPTIONS:
  -E, --regexp TEXT     正则表达式模式（可与 QUERY 组合使用）
  -l, --files-only      仅输出文件路径
  -c, --count           仅输出匹配数量
  --top INT             返回前 N 条结果（默认 50，按 BM25 排序）
  --ids-only            仅返回 company_id 列表
```

### FTS5 查询语法（Agent 需要了解）

```
# 关键词（隐式 AND）
company-grep "東京 AI"               → 同时包含「東京」和「AI」

# 显式 AND
company-grep "DX推進 AND 製造業"

# OR
company-grep "AI OR 機械学習 OR MLOps"

# NOT
company-grep "東京 NOT 大企業"

# 短语（精确词序）
company-grep '"資金調達をした"'

# 前缀
company-grep 'AI*'                    → AI, AIスタートアップ, AI活用 ...

# 组合
company-grep "(AI OR 機械学習) AND 東京 NOT コンサル"
```

### 输出格式

标准模式：
```
RANK	ID	NAME	SCORE	SNIPPET
1	JP-00456	DXソリューション株式会社	-12.35	...DX推進に取り組んでおり、製造業向けの...
2	JP-00789	スマートファクトリー株式会社	-10.21	...工場のDX推進を支援する...
---
Found: 342 matches (showing top 50)
```

> SCORE 是 FTS5 的 `rank` 值（BM25），值越小（负数越大）越相关。

### 实现要点

```python
#!/usr/bin/env python3
"""company-grep: 企业全文检索（grep 替代）"""

import argparse
import sqlite3
import re
import sys

DB_PATH = "companies.db"


def regexp_func(pattern, text):
    """SQLite REGEXP 函数实现。"""
    if text is None:
        return False
    return bool(re.search(pattern, text))


def main():
    parser = argparse.ArgumentParser(description="企业全文检索")
    parser.add_argument("query", nargs="?", help="FTS5 搜索表达式")
    parser.add_argument("-E", "--regexp", help="正则表达式模式")
    parser.add_argument("-l", "--files-only", action="store_true")
    parser.add_argument("-c", "--count", action="store_true")
    parser.add_argument("--top", type=int, default=50)
    parser.add_argument("--ids-only", action="store_true")
    args = parser.parse_args()

    if not args.query and not args.regexp:
        print("Error: 请提供搜索关键词或正则表达式", file=sys.stderr)
        sys.exit(1)

    db = sqlite3.connect(DB_PATH)
    db.create_function("REGEXP", 2, regexp_func)

    if args.query and not args.regexp:
        # 模式 1：纯 FTS5 搜索（最快）
        sql = """
            SELECT company_id, name_ja, rank, 
                   snippet(docs, 2, '<<', '>>', '...', 30)
            FROM docs
            WHERE docs MATCH ?
            ORDER BY rank
            LIMIT ?
        """
        rows = db.execute(sql, (args.query, args.top)).fetchall()

    elif args.regexp and not args.query:
        # 模式 2：纯正则搜索（比 grep -r 快，但比 FTS5 慢）
        sql = """
            SELECT company_id, name_ja, 0 as rank, 
                   substr(body, 1, 200)
            FROM docs
            WHERE body REGEXP ?
            LIMIT ?
        """
        rows = db.execute(sql, (args.regexp, args.top)).fetchall()

    else:
        # 模式 3：FTS5 粗筛 + REGEXP 精筛（又快又准）
        sql = """
            SELECT company_id, name_ja, rank, 
                   snippet(docs, 2, '<<', '>>', '...', 30)
            FROM docs
            WHERE docs MATCH ?
            AND body REGEXP ?
            ORDER BY rank
            LIMIT ?
        """
        rows = db.execute(sql, (args.query, args.regexp, args.top)).fetchall()

    # 输出
    if args.count:
        print(f"Count: {len(rows)}")
    elif args.files_only:
        for row in rows:
            print(f"/companies/{row[0]}.md")
    elif args.ids_only:
        for row in rows:
            print(row[0])
    else:
        print("RANK\tID\tNAME\tSCORE\tSNIPPET")
        for i, row in enumerate(rows, 1):
            snippet = (row[3] or "").replace("\n", " ")[:100]
            print(f"{i}\t{row[0]}\t{row[1]}\t{row[2]:.2f}\t{snippet}")
        print(f"---\nFound: {len(rows)} matches (showing top {args.top})")

    db.close()


if __name__ == "__main__":
    main()
```

---

## 6. 安装为 CLI 命令

```bash
# 方式一：符号链接（开发环境）
chmod +x company_search.py company_grep.py sync_db.py
ln -s $(pwd)/company_search.py /usr/local/bin/company-search
ln -s $(pwd)/company_grep.py /usr/local/bin/company-grep

# 方式二：wrapper 脚本
cat > /usr/local/bin/company-search << 'EOF'
#!/bin/bash
python3 /path/to/company_search.py "$@"
EOF
chmod +x /usr/local/bin/company-search

cat > /usr/local/bin/company-grep << 'EOF'
#!/bin/bash
python3 /path/to/company_grep.py "$@"
EOF
chmod +x /usr/local/bin/company-grep
```

---

## 7. 目录结构

```
enterprise-search/
├── companies.db              # SQLite 数据库（生成文件，不入 git）
├── sync_db.py                # MD → SQLite 同步脚本
├── company_search.py         # CLI: company-search
├── company_grep.py           # CLI: company-grep
├── check_env.py              # 环境检查脚本（FTS5、ICU 可用性）
├── tests/
│   ├── test_sync.py          # 同步脚本测试
│   ├── test_search.py        # company-search 测试
│   ├── test_grep.py          # company-grep 测试
│   └── fixtures/
│       ├── JP-TEST-001.md    # 测试用 MD 文件
│       ├── JP-TEST-002.md
│       └── JP-TEST-003.md
└── README.md
```

---

## 8. 实现顺序

按以下顺序编码和验证：

### Step 1：环境检查（check_env.py）

检查 Python 版本、SQLite 版本、FTS5 支持、ICU tokenizer 支持。输出诊断信息。

### Step 2：Sync 脚本（sync_db.py）

1. 建表（companies + docs FTS5）
2. 解析 MD frontmatter（用 `yaml.safe_load`，需要 `pip install pyyaml`）
3. UPSERT 到两张表
4. 用 `tests/fixtures/` 下的测试文件验证

### Step 3：company-search

1. 实现参数解析
2. 动态 SQL 构建（注意 SQL 注入防护：sort 字段白名单，值用参数化查询）
3. 格式化输出
4. 测试：基础筛选、多条件组合、count 模式、排序

### Step 4：company-grep

1. 实现 FTS5 查询（模式 1）
2. 实现 REGEXP 查询（模式 2）
3. 实现 FTS5 + REGEXP 组合（模式 3）
4. 注册 REGEXP 函数
5. 测试：关键词、布尔逻辑、正则、组合、输出格式

### Step 5：集成测试

1. 用 fixtures 建库
2. 跑 company-search 各种条件组合
3. 跑 company-grep 各种查询模式
4. 验证两者管道组合：`company-search --ids-only ... | xargs -I{} company-grep ...`

---

## 9. 依赖

```
Python >= 3.9
sqlite3         （标准库，需支持 FTS5）
pyyaml          （pip install pyyaml）
```

无其他外部依赖。不需要向量数据库、GPU、embedding 模型。

---

## 10. 注意事项

1. **SQL 注入防护**：所有用户输入必须用参数化查询（`?` 占位符），`sort` 字段用白名单校验。
2. **FTS5 ICU 降级**：如果 ICU tokenizer 不可用，自动降级到 `unicode61`，需在建表时处理。
3. **大文件性能**：单个 MD 文件如果超过 100KB，body 可以截断到前 50KB 入 FTS5。
4. **编码**：所有文件读写使用 `utf-8`。
5. **错误处理**：MD 文件解析失败时 skip 并打印 stderr 警告，不中断同步流程。
6. **TSV 输出**：字段中如果包含 tab 字符，替换为空格。
