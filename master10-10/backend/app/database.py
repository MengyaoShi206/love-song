# backend/app/database.py
from __future__ import annotations
import os
from pathlib import Path
from sqlalchemy import create_engine # type: ignore
from sqlalchemy.orm import sessionmaker, declarative_base # type: ignore

# 项目根目录：.../master/
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 把 DB 放在 data/ 下，便于和 CSV 放一起
DB_PATH = DATA_DIR / "marry.db"

# 允许通过环境变量覆盖（可选）
SQLALCHEMY_DATABASE_URL = os.getenv(
    "MARRY_DB_URL",
    f"sqlite:///{DB_PATH}"
)

# SQLite for FastAPI（同线程限制关闭）
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    """
    1) 建表
    2) 若空库，则自动从 data/user_file + data/platform 导入 CSV
    """
    # 延迟导入，避免循环引用
    from .models import user as user_models
    from .models import platform as platform_models
    Base.metadata.create_all(bind=engine)

    # 检查是否需要导入
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            # 是否已有用户
            has_user_table = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='user_account'")
            ).fetchone()
            if not has_user_table:
                # 刚刚才建表，直接导入
                _seed_from_csv()
            else:
                existing = conn.execute(text("SELECT COUNT(1) FROM user_account")).scalar()
                if (existing or 0) == 0:
                    _seed_from_csv()
    except Exception as e:
        print(f"[init_db] 初始化时未能检查/导入数据（可忽略）：{e}")

def _seed_from_csv():
    """调用项目内的导入脚本，把 data/ 下 CSV 全部导入到 data/marry.db。"""
    try:
        from .seed_from_csv import main as seed_main # type: ignore
        seed_main()
        print("[init_db] 已从 CSV 导入到 data/marry.db")
    except Exception as e:
        print(f"[init_db] 自动导入 CSV 失败：{e}")

# def _seed_from_csv():
#     """调用项目内的导入脚本，把 data/ 下 CSV 全部导入到 data/marry.db。"""
#     from .seed_from_csv import main as seed_main # type: ignore
#     seed_main()
#     print("[init_db] 已从 CSV 导入到 data/marry.db")

if __name__ == "__main__":
    print(BASE_DIR)
    init_db()
