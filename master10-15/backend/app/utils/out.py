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

# 查询所有数据
df = pd.read_sql("SELECT * FROM user_account", conn)
print(df.head())

# 导出 Excel
df.to_excel("user_account_all.xlsx", index=False)
print("✅ 已导出 user_account_all.xlsx")

conn.close()
