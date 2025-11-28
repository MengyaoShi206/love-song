# dump_doris_sql.py
import pymysql
import os
from datetime import datetime

# ====== 连接 Doris（MySQL 协议）======
conn = pymysql.connect(
    host="127.0.0.1",
    port=9030,            # Doris FE 默认 9030
    user="root",
    password="123456",
    database="marry_analytics",
    charset="utf8mb4",
    cursorclass=pymysql.cursors.Cursor
)

# ====== 导出设置 ======
OUTPUT_DIR = "/home/qssss/haozong/hunlian/dorisdata/sql_dump"
SINGLE_FILE = True  # True: 全库一个 .sql；False: 每表一个 .sql
BATCH_VALUES = 1000 # INSERT 批量条数，按数据量可适当调大/调小

os.makedirs(OUTPUT_DIR, exist_ok=True)

def qname(name: str) -> str:
    """反引号引用表/列名"""
    return f"`{name}`"

def write_header(f, dbname):
    f.write("-- --------------------------------------------------\n")
    f.write(f"-- Dump of database {dbname}\n")
    f.write(f"-- Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write("-- --------------------------------------------------\n\n")
    # Doris 基本支持的设置（尽量保守）
    f.write("SET NAMES utf8mb4;\n")
    f.write("\n")

def dump_one_table(table: str, conn, fp):
    with conn.cursor() as cur:
        # 1) DDL
        cur.execute(f"SHOW CREATE TABLE {qname(table)}")
        row = cur.fetchone()
        if not row or len(row) < 2:
            print(f"⚠️  跳过 {table}：SHOW CREATE TABLE 结果异常")
            return 0

        ddl = row[1]
        fp.write(f"\n-- -----------------------\n")
        fp.write(f"-- Table structure for {table}\n")
        fp.write(f"-- -----------------------\n")
        fp.write(f"DROP TABLE IF EXISTS {qname(table)};\n")
        fp.write(f"{ddl};\n\n")

        # 2) 数据
        # 用服务端游标流式读取，避免一次性拉全表
        stream_cur = conn.cursor(pymysql.cursors.SSCursor)
        stream_cur.execute(f"SELECT * FROM {qname(table)}")
        cols = [desc[0] for desc in stream_cur.description]
        col_list = ", ".join(qname(c) for c in cols)
        placeholders = "(" + ", ".join(["%s"] * len(cols)) + ")"

        fp.write(f"-- -----------------------\n")
        fp.write(f"-- Data for {table}\n")
        fp.write(f"-- -----------------------\n")

        count = 0
        batch_vals = []
        while True:
            rows = stream_cur.fetchmany(BATCH_VALUES)
            if not rows:
                break

            # 用连接自带的转义，确保字符串/NULL/二进制安全
            values_sql_parts = []
            for r in rows:
                # conn.escape 会把每个值安全转成 SQL 字面量（含引号/NULL）
                escaped = [conn.escape(v) for v in r]
                values_sql_parts.append("(" + ", ".join(map(str, escaped)) + ")")
            insert_sql = f"INSERT INTO {qname(table)} ({col_list}) VALUES\n" + ",\n".join(values_sql_parts) + ";\n"
            fp.write(insert_sql)
            count += len(rows)

        stream_cur.close()
        if count == 0:
            fp.write(f"-- (no rows)\n")
        fp.write("\n")
        return count

def main():
    with conn.cursor() as cur:
        cur.execute("SHOW TABLES")
        tables = [r[0] for r in cur.fetchall()]

    print(f"📋 共发现 {len(tables)} 张表：{tables}")

    total_rows = 0
    if SINGLE_FILE:
        out_path = os.path.join(OUTPUT_DIR, f"marry_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql")
        with open(out_path, "w", encoding="utf-8") as f:
            write_header(f, "marry_analytics")
            for t in tables:
                print(f"🚀 导出 {t} …")
                try:
                    n = dump_one_table(t, conn, f)
                    print(f"✅ {t} 导出完成（{n} 行）")
                    total_rows += n
                except Exception as e:
                    print(f"❌ {t} 导出失败：{e}")
        print(f"\n🎉 导出完成：{out_path}（合计 {total_rows} 行）")
    else:
        # 每表单独一个 .sql
        for t in tables:
            out_path = os.path.join(OUTPUT_DIR, f"{t}.sql")
            print(f"🚀 导出 {t} …")
            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    write_header(f, "marry_analytics")
                    n = dump_one_table(t, conn, f)
                print(f"✅ {t} 导出完成：{out_path}（{n} 行）")
                total_rows += n
            except Exception as e:
                print(f"❌ {t} 导出失败：{e}")
        print(f"\n🎉 全部完成，目录：{OUTPUT_DIR}（合计 {total_rows} 行）")

if __name__ == "__main__":
    try:
        main()
    finally:
        conn.close()
