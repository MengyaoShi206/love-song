import pymysql
import pandas as pd

# 连接 Doris
conn = pymysql.connect(
    host="127.0.0.1",
    port=9030,
    user="root",
    password="123456",
    database="marry_analytics"
)

# 查询并按 id 升序排列
query = "SELECT * FROM user_account ORDER BY id ASC"
df = pd.read_sql(query, conn)

# 显示前几行
print(df.head())

# 导出为 CSV
df.to_csv("user_account_all.csv", index=False)
print("✅ 已导出 user_account_all.csv（已按 id 从小到大排序）")

conn.close()
