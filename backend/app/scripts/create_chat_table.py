# backend/app/scripts/create_chat_table.py
from app.database import engine
from app.models.user import ChatMessage

def main():
    # 只创建这一张表，若已存在则跳过
    ChatMessage.__table__.create(bind=engine, checkfirst=True)
    print("✅ chat_message 表已在主库（SQLite / MySQL）创建完成")

if __name__ == "__main__":
    main()
