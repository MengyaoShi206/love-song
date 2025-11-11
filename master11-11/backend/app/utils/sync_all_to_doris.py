# backend/app/utils/sync_all_to_doris.py
# 用法：
#   cd ~/haozong/hunlian/master/backend
#   export MARRY_DORIS_URL="mysql+pymysql://root:123456@127.0.0.1:9030/marry_analytics"
#   python -m app.utils.sync_all_to_doris

from typing import List, Dict

from sqlalchemy.orm import object_mapper
from sqlalchemy import text

from app.database import SessionLocal, SessionDoris
from app.models.user import (
    UserAccount,
    UserIntention,
    UserLifestyle,
    UserQna,
    UserMedia,
    UserCertification,
    UserProfilePublic,
    UserBlacklist,
    UserPrivacy,
    UserRelationStage,
    UserLike,
    Match,
)
from app.models.platform import (
    UserVerification,
    RiskAssessment,
)

# ====== 配置区域 ======
BATCH_SIZE = 500

# ORM 表名 → Doris 表名（只有不一致的才写进来）
TABLE_NAME_MAP: Dict[str, str] = {
    "match": "user_match",   # 关键：ORM 是 match，Doris 是 user_match
}

# 想在同步前清空的 Doris 表
TABLES_TO_TRUNCATE = [
    "marry_analytics.user_account",
    "marry_analytics.user_match",
    "marry_analytics.user_intention",
    "marry_analytics.user_lifestyle",
    "marry_analytics.user_qna",
    "marry_analytics.user_media",
    "marry_analytics.user_certification",
    "marry_analytics.user_profile_public",
    "marry_analytics.user_like",
    "marry_analytics.user_relation_stage",
    "marry_analytics.user_privacy",
    "marry_analytics.user_blacklist",
    "marry_analytics.risk_assessment",
    "marry_analytics.user_verification",
]
# ======================


def get_doris_session():
    """安全拿 Doris Session，没有就报错"""
    dst = SessionDoris()
    if dst is None:
        raise RuntimeError("❌ Doris 未配置，请先设置 MARRY_DORIS_URL 再运行同步脚本")
    return dst


def truncate_tables():
    """同步前清空需要清空的 Doris 表，避免重复数据"""
    dst = get_doris_session()
    for t in TABLES_TO_TRUNCATE:
        dst.execute(text(f"TRUNCATE TABLE {t}"))
        print(f"🧹 已清空 {t}")
    dst.commit()
    dst.close()


def insert_batch_to_doris_raw(dst, table_name: str, rows: List[dict]):
    """
    针对“ORM 表名和 Doris 表名不一致”的情况，用手动 SQL 插入
    rows: 每一条是 {col: val}
    """
    if not rows:
        return

    cols = list(rows[0].keys())
    # INSERT INTO user_match (id,user_a,...) VALUES (:id,:user_a,...)
    placeholders = ", ".join(f":{c}" for c in cols)
    col_list = ", ".join(cols)
    sql = text(f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders})")

    for row in rows:
        dst.execute(sql, row)

    dst.commit()


def copy_one_model(Model):
    """
    把主库中的 Model 全部复制到 Doris 里去
    """
    src = SessionLocal()
    dst = get_doris_session()

    # 真实要写进 Doris 的表名（有映射用映射，没有就用 ORM 自己的）
    src_table_name = Model.__tablename__
    doris_table_name = TABLE_NAME_MAP.get(src_table_name, src_table_name)

    print(f"\n=== 同步表: {src_table_name} → Doris: {doris_table_name} ===")

    last_id = 0
    total_inserted = 0

    while True:
        # 分批从主库取
        rows = (
            src.query(Model)
            .filter(Model.id > last_id)
            .order_by(Model.id)
            .limit(BATCH_SIZE)
            .all()
        )

        if not rows:
            break

        # 要插 Doris 的一批
        orm_batch = []   # 可以直接 add_all 的
        raw_batch = []   # 需要自己拼 INSERT 的（比如 match → user_match）

        for r in rows:
            mapper = object_mapper(r)
            data = {}
            for col in mapper.columns:
                v = getattr(r, col.key)
                # Enum → 取 value
                if hasattr(v, "value"):
                    v = v.value
                data[col.key] = v

            # 如果 Doris 表名跟 ORM 一样，就走 ORM 正常 add
            if doris_table_name == src_table_name:
                orm_batch.append(Model(**data))
            else:
                # 表名不一样，用手动 SQL（专门为了 match → user_match）
                raw_batch.append(data)

            # 更新分页游标
            if hasattr(r, "id"):
                last_id = r.id

        # 先插需要手动表名的
        if raw_batch:
            insert_batch_to_doris_raw(dst, doris_table_name, raw_batch)
            total_inserted += len(raw_batch)
            print(f"{doris_table_name}: +{len(raw_batch)} (共 {total_inserted})")

        # 再插正常的
        if orm_batch:
            dst.add_all(orm_batch)
            dst.commit()
            total_inserted += len(orm_batch)
            print(f"{doris_table_name}: +{len(orm_batch)} (共 {total_inserted})")

    src.close()
    dst.close()
    print(f"✅ 表 {src_table_name} → {doris_table_name} 同步完成，共 {total_inserted} 条")


def main():
    # 1) 可选：先清空 Doris 里已经存在的这几张表
    truncate_tables()

    # 2) 按顺序同步
    models: List[type] = [
        # 先主账户
        UserAccount,
        # 再资料类
        UserProfilePublic,
        UserIntention,
        UserLifestyle,
        UserMedia,
        UserQna,
        UserCertification,
        UserPrivacy,
        UserRelationStage,
        # 行为类
        UserLike,
        UserBlacklist,
        # 匹配关系（ORM: match → Doris: user_match）
        Match,
        # 平台 / 审核相关
        UserVerification,
        RiskAssessment,
        # 下面这些如果你项目里真有，可以放开
        # UserSubscription,
        # UserBehaviorLog,
        # MediaReview,
    ]

    for m in models:
        copy_one_model(m)


if __name__ == "__main__":
    main()
