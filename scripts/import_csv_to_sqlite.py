#!/usr/bin/env python3
"""
CSV → SQLite 导入脚本
将 data/Kihonjoho_UTF-8.csv (579万行) 导入 SQLite 数据库
建立结构化索引 + FTS5 全文检索索引
"""

import csv
import sqlite3
import os
import sys
import time
import re

# 路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE_DIR, "data", "Kihonjoho_UTF-8.csv")
DB_PATH = os.path.join(BASE_DIR, "data", "enterprises.db")

# 只导入有用的列（CSV 列名 → DB 列名）
COLUMN_MAP = {
    "法人番号": "houjin_bangou",
    "商号または名称": "company_name",
    "商号または名称（カナ）": "company_name_kana",
    "商号または名称（英字）": "company_name_en",
    "登記住所": "address",
    "都道府県": "prefecture",
    "都道府県コード": "prefecture_code",
    "市区町村（郡）": "city",
    "代表者名称": "representative",
    "資本金": "capital",
    "従業員数": "employee_count",
    "事業概要": "business_summary",
    "WebサイトURL": "website",
    "事業種目": "business_type",
    "設立年月日": "established_date",
    "更新年月日": "updated_date",
}


def clean_number(val):
    """数值字段清洗：去掉非数字字符"""
    if not val:
        return None
    cleaned = re.sub(r'[^0-9]', '', val)
    return int(cleaned) if cleaned else None


def clean_prefecture_code(val):
    """都道府県コード清洗：转为整数"""
    if not val:
        return None
    cleaned = re.sub(r'[^0-9]', '', val)
    return int(cleaned) if cleaned else None


def create_tables(conn):
    """建表"""
    cur = conn.cursor()

    # 主表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS enterprises (
            houjin_bangou TEXT PRIMARY KEY,
            company_name TEXT,
            company_name_kana TEXT,
            company_name_en TEXT,
            address TEXT,
            prefecture TEXT,
            prefecture_code INTEGER,
            city TEXT,
            representative TEXT,
            capital INTEGER,
            employee_count INTEGER,
            business_summary TEXT,
            website TEXT,
            business_type TEXT,
            established_date TEXT,
            updated_date TEXT
        )
    """)

    # FTS5 全文检索虚拟表（用于事業概要 + 事業種目 + 商号 的关键词搜索）
    cur.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS enterprises_fts USING fts5(
            houjin_bangou UNINDEXED,
            company_name,
            business_summary,
            business_type,
            content='enterprises',
            content_rowid='rowid',
            tokenize='unicode61'
        )
    """)

    conn.commit()


def create_indexes(conn):
    """建结构化索引"""
    cur = conn.cursor()

    indexes = [
        ("idx_prefecture_code", "enterprises(prefecture_code)"),
        ("idx_employee_count", "enterprises(employee_count)"),
        ("idx_capital", "enterprises(capital)"),
        ("idx_established_date", "enterprises(established_date)"),
        ("idx_prefecture_emp", "enterprises(prefecture_code, employee_count)"),
    ]

    for idx_name, idx_def in indexes:
        print(f"  建索引: {idx_name}...")
        cur.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}")

    conn.commit()


def populate_fts(conn):
    """填充 FTS5 索引"""
    cur = conn.cursor()
    print("  填充 FTS5 全文索引...")
    cur.execute("""
        INSERT INTO enterprises_fts(rowid, houjin_bangou, company_name, business_summary, business_type)
        SELECT rowid, houjin_bangou, company_name, business_summary, business_type
        FROM enterprises
    """)
    conn.commit()


def import_csv(conn):
    """导入 CSV 数据"""
    cur = conn.cursor()

    # 读取 CSV header，建立列名到索引的映射
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        headers = next(reader)

    # CSV 列名 → 列索引
    csv_col_indices = {}
    for csv_col, db_col in COLUMN_MAP.items():
        try:
            csv_col_indices[db_col] = headers.index(csv_col)
        except ValueError:
            print(f"  警告: CSV 中找不到列 '{csv_col}'，跳过")

    print(f"  映射了 {len(csv_col_indices)} 列")

    # 批量导入
    batch_size = 50000
    batch = []
    total = 0
    start_time = time.time()

    db_columns = list(csv_col_indices.keys())
    placeholders = ','.join(['?'] * len(db_columns))
    insert_sql = f"INSERT OR REPLACE INTO enterprises ({','.join(db_columns)}) VALUES ({placeholders})"

    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader)  # 跳过 header

        for row in reader:
            # 提取需要的列
            values = []
            for db_col in db_columns:
                idx = csv_col_indices[db_col]
                val = row[idx].strip() if idx < len(row) else ""

                # 数值字段清洗
                if db_col == 'employee_count':
                    val = clean_number(val)
                elif db_col == 'capital':
                    val = clean_number(val)
                elif db_col == 'prefecture_code':
                    val = clean_prefecture_code(val)
                else:
                    val = val if val else None

                values.append(val)

            batch.append(values)
            total += 1

            if len(batch) >= batch_size:
                cur.executemany(insert_sql, batch)
                conn.commit()
                elapsed = time.time() - start_time
                speed = total / elapsed if elapsed > 0 else 0
                print(f"  已导入 {total:,} 行... ({speed:.0f} 行/秒)")
                batch = []

    # 写入剩余数据
    if batch:
        cur.executemany(insert_sql, batch)
        conn.commit()

    elapsed = time.time() - start_time
    print(f"  导入完成: {total:,} 行, 耗时 {elapsed:.1f} 秒")
    return total


def main():
    if not os.path.exists(CSV_PATH):
        print(f"错误: 找不到 CSV 文件 {CSV_PATH}")
        sys.exit(1)

    # 删除旧数据库（全量重建）
    if os.path.exists(DB_PATH):
        print(f"删除旧数据库: {DB_PATH}")
        os.remove(DB_PATH)

    print(f"=== CSV → SQLite 导入 ===")
    print(f"CSV: {CSV_PATH}")
    print(f"DB:  {DB_PATH}")
    print()

    conn = sqlite3.connect(DB_PATH)
    # 性能优化
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA cache_size=-2000000")  # 2GB cache
    conn.execute("PRAGMA temp_store=MEMORY")

    try:
        print("[1/4] 建表...")
        create_tables(conn)

        print("[2/4] 导入 CSV 数据...")
        total = import_csv(conn)

        print("[3/4] 建结构化索引...")
        create_indexes(conn)

        print("[4/4] 填充全文索引...")
        populate_fts(conn)

        # 统计
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM enterprises WHERE business_summary IS NOT NULL AND business_summary != ''")
        has_summary = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM enterprises WHERE employee_count IS NOT NULL")
        has_emp = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT prefecture_code) FROM enterprises WHERE prefecture_code IS NOT NULL")
        prefectures = cur.fetchone()[0]

        db_size = os.path.getsize(DB_PATH) / (1024 * 1024 * 1024)

        print()
        print(f"=== 完成 ===")
        print(f"总行数:          {total:,}")
        print(f"有事業概要:       {has_summary:,} ({has_summary/total*100:.1f}%)")
        print(f"有従業員数:       {has_emp:,} ({has_emp/total*100:.1f}%)")
        print(f"都道府県数:       {prefectures}")
        print(f"数据库大小:       {db_size:.2f} GB")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
