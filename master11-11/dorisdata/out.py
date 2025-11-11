import pymysql
import pandas as pd
import os

# 连接 Doris / MySQL
conn = pymysql.connect(
    host="127.0.0.1",
    port=9030,           # Doris 默认 9030
    user="root",
    password="123456",
    database="marry_analytics",
    charset="utf8mb4"
)

# 输出目录
output_dir = "/home/qssss/haozong/hunlian/dorisdata"
os.makedirs(output_dir, exist_ok=True)

# 获取所有表名
with conn.cursor() as cur:
    cur.execute("SHOW TABLES")
    tables = [row[0] for row in cur.fetchall()]

print(f"📋 共找到 {len(tables)} 张表：{tables}")

for table in tables:
    print(f"🚀 正在导出 {table} ...")
    try:
        # 尝试按 id 排序；如果表没有 id 列，会自动跳过排序
        try:
            query = f"SELECT * FROM {table} ORDER BY id ASC"
            df = pd.read_sql(query, conn)
        except Exception:
            query = f"SELECT * FROM {table}"
            df = pd.read_sql(query, conn)

        # 导出为 CSV
        csv_path = os.path.join(output_dir, f"{table}.csv")
        df.to_csv(csv_path, index=False)
        print(f"✅ 已导出 {csv_path} ({len(df)} 行)")
    except Exception as e:
        print(f"❌ 导出 {table} 失败：{e}")

conn.close()
print("\n🎉 所有表已导出完成，文件保存在：", os.path.abspath(output_dir))
