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

# 默认：SQLite（本地调试）
DEFAULT_SQLITE_URL = f"sqlite:///{DB_PATH}"

# 环境变量优先（生产环境可切换 MySQL / Doris）
MYSQL_URL = os.getenv("MARRY_MYSQL_URL")  # e.g. mysql+pymysql://user:pwd@host:3306/marry
DORIS_URL = os.getenv("MARRY_DORIS_URL")  # e.g. mysql+pymysql://user:pwd@host:9030/marry_analytics
SQLITE_URL = os.getenv("MARRY_SQLITE_URL", DEFAULT_SQLITE_URL)

# 当前主库 URL
SQLALCHEMY_DATABASE_URL = MYSQL_URL or SQLITE_URL

# SQLite for FastAPI（同线程限制关闭）
engine_main = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={"check_same_thread": False}
    if SQLALCHEMY_DATABASE_URL.startswith("sqlite")
    else {},
)
engine = engine_main
# engine_doris = (
#     create_engine(DORIS_URL, pool_pre_ping=True, pool_recycle=3600)
#     if DORIS_URL
#     else None
# )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_main, expire_on_commit=False,)

# 初始化数据库连接
SessionDoris = None
if DORIS_URL:
    # 创建 Doris 引擎
    engine_doris = create_engine(
        DORIS_URL,
        pool_size=10,  # 可根据需求调整连接池大小
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_timeout=30  # 增加超时限制
    )
    SessionDoris = sessionmaker(autocommit=False, autoflush=False, bind=engine_doris)
else:
    print("[Doris] Doris 数据库未配置，无法连接到 Doris。")

Base = declarative_base()

def init_db():
    """
    1) 建表
    2) 若空库，则自动从 data/user_file + data/platform 导入 CSV
    """
    # 延迟导入，避免循环引用
    from .models import user as user_models
    from .models import platform as platform_models
    from .models import advantage as advantage_models

    Base.metadata.create_all(bind=engine_main)

    # 仅在 SQLite 模式下尝试导入 CSV
    if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
        try:
            from sqlalchemy import text

            with engine_main.connect() as conn:
                has_table = conn.execute(
                    text(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='user_account'"
                    )
                ).fetchone()

                if not has_table:
                    _seed_from_csv()
                else:
                    existing = conn.execute(
                        text("SELECT COUNT(1) FROM user_account")
                    ).scalar()
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

# 去seed_from_csv.py运行
