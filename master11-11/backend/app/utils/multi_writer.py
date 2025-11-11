# backend/app/utils/multi_writer.py
import asyncio
import threading
from datetime import datetime, date
from typing import Any, Dict, Iterable, Optional, Set
import json
from decimal import Decimal
import enum

from sqlalchemy.inspection import inspect as sa_inspect
from sqlalchemy.orm import object_mapper, Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text, or_



from app.models.user import (
    UserAccount, UserIntention, UserLifestyle, UserQna, UserMedia, 
    UserCertification, UserProfilePublic,
    UserBlacklist, UserPrivacy, UserRelationStage, UserLike, Match,
)
from app.models.platform import (
    UserVerification, RiskAssessment
)

from app.database import SessionLocal, SessionDoris


# 仅允许镜像到 Doris 的表（参与度相关）
MIRROR_ALLOWED: Set[str] = {
    UserAccount.__tablename__,
    UserIntention.__tablename__,
    UserLifestyle.__tablename__,
    UserQna.__tablename__,
    UserMedia.__tablename__,
    UserCertification.__tablename__,
    UserProfilePublic.__tablename__,

    UserLike.__tablename__,
    UserRelationStage.__tablename__,
    UserPrivacy.__tablename__,
    UserBlacklist.__tablename__,
    RiskAssessment.__tablename__,
    UserVerification.__tablename__,
    Match.__tablename__,
}

UPSERT_KEYS: dict[str, tuple[str, ...]] = {
    # 都有 id 主键，直接用 id
    "user_account": ("id",),
    "user_intention": ("id",),
    "user_lifestyle": ("id",),
    "user_qna": ("id",),
    "user_media": ("id",),
    "user_certification": ("id",),
    "user_profile_public": ("id",),

    # 新表
    "user_like": ("id",),    
    "user_relation_stage": ("id",),
    "user_privacy": ("id",),
    "user_blacklist": ("id",),
    "risk_assessment": ("id",),
    "user_verification": ("id",),
    "match": ("user_a", "user_b"),
}

def _doris_dbname(sess: Session) -> str:
    """从 Session 取当前连接的库名（来自 MARRY_DORIS_URL）"""
    try:
        return str(sess.bind.url.database or "")
    except Exception:
        return ""

def _qualify(table: str, dbname: str) -> str:
    """拼接成 `db`.`table`，dbname 为空则退化为 `table`"""
    return f"`{dbname}`.`{table}`" if dbname else f"`{table}`"

def _is_orm(obj) -> bool:
    return hasattr(obj, "__table__") and hasattr(obj, "__mapper__")

def _to_row(obj: Any) -> Dict[str, Any]:
    """
    将 SQLAlchemy ORM 实例或 dict 拍成可直接写 Doris 的纯 dict。
    - datetime/date -> 'YYYY-MM-DD HH:MM:SS' 字符串
    - list/dict     -> JSON 字符串（Doris JSONB 也能接收字符串后解析）
    """
    if isinstance(obj, dict):
        src = obj
    elif _is_orm(obj):
        mp = sa_inspect(obj).mapper
        src = {c.key: getattr(obj, c.key, None) for c in mp.column_attrs}
    else:
        raise TypeError(f"unsupported object type: {type(obj)}")

    out: Dict[str, Any] = {}
    for k, v in src.items():
        if isinstance(v, (datetime, date)):
            out[k] = v.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(v, (list, dict)):
            out[k] = json.dumps(v, ensure_ascii=False)
        elif isinstance(v, Decimal):
            out[k] = float(v)  # 或 str(v) 按你 Doris 列类型决定
        elif isinstance(v, enum.Enum):
            out[k] = v.value if not isinstance(v.value, enum.Enum) else str(v.value)
        else:
            out[k] = v
    return out

# ================ 主类：MultiWriter ================
class MultiWriter:
    """
    主库同步 + Doris 异步镜像写入封装
    用法：
        from app.utils.multi_writer import MultiWriter
        MultiWriter.write(user_instance)
    """

    @staticmethod
    def write(model_instance: Any, db: Optional[Session] = None, mirror: bool = True):
        """
        写入主库；可选异步镜像到 Doris。
        - db: 复用外部 Session；不传则内部创建并关闭
        """
        own = False
        if db is None:
            db = SessionLocal()
            own = True

        try:
            db.add(model_instance)
            db.commit()
            db.refresh(model_instance)
        except Exception as e:
            db.rollback()
            print(f"[MultiWriter] 主库写入失败: {e}")
            raise
        finally:
            if own:
                db.close()

        # 异步镜像 Doris（只有配置了 MARRY_DORIS_URL 时 SessionDoris 才会存在）
        if mirror and SessionDoris is not None:
            tbl = getattr(type(model_instance), "__tablename__", "")
            if tbl in MIRROR_ALLOWED:
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(MultiWriter._async_mirror(model_instance))
                except RuntimeError:
                    # 当前线程没有事件循环（常见于 FastAPI 同步路由内）
                    t = threading.Thread(
                        target=lambda: asyncio.run(MultiWriter._async_mirror(model_instance)),
                        daemon=True,
                    )
                    t.start()

        return model_instance

    @staticmethod
    def mirror_only(model_instance: Any):
        """
        只做异步镜像到 Doris（利用 _async_mirror），不改主库、不提交事务。
        适用于你在主库已 db.commit() 之后，需要把变更同步到 Doris 的场景。
        """
        if SessionDoris is None:
            return
        tbl = getattr(type(model_instance), "__tablename__", "")
        if tbl not in MIRROR_ALLOWED:
            return

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(MultiWriter._async_mirror(model_instance))
        except RuntimeError:
            t = threading.Thread(
                target=lambda: asyncio.run(MultiWriter._async_mirror(model_instance)),
                daemon=True,
            )
            t.start()

    @staticmethod
    async def _async_mirror(instance: Any):
        """异步镜像写入 Doris（先删后插的伪 upsert，避免会话依赖）"""
        if SessionDoris is None:
            return
        doris_sess: Session = SessionDoris()
        try:
            table = getattr(type(instance), "__tablename__", None) if _is_orm(instance) \
                    else instance.get("__tablename__") if isinstance(instance, dict) else None
            if not table or table not in MIRROR_ALLOWED:
                return

            # 1) 拍平为 dict（彻底摆脱 ORM Session）
            row: Dict[str, Any] = _to_row(instance)

            # 2) 拉 Doris 列集合，并取交集（防 Unknown column）
            doris_cols = _doris_columns(doris_sess, table)
            if not doris_cols:
                print(f"[MultiWriter] Doris 未找到表或列：{table}")
                return

            filtered = {k: v for k, v in row.items() if k in doris_cols}
            if not filtered:
                print(f"[MultiWriter] 过滤后无可写列：{table}")
                return

            # 3) upsert 键
            key_cols = UPSERT_KEYS.get(table, ("id",))
            for k in key_cols:
                if k not in filtered or filtered[k] is None:
                    raise ValueError(f"[MultiWriter] upsert 键缺失：table={table}, key={k}, row={filtered}")

            # 4) 构建 SQL（delete + insert）
            dbname = _doris_dbname(doris_sess)
            qname = _qualify(table, dbname)

            # delete
            where = " AND ".join([f"`{k}` = :__key_{k}" for k in key_cols])
            del_params = {f"__key_{k}": filtered[k] for k in key_cols}
            doris_sess.execute(text(f"DELETE FROM {qname} WHERE {where}"), del_params)

            # insert
            cols = ", ".join(f"`{k}`" for k in filtered.keys())
            vals = ", ".join(f":{k}" for k in filtered.keys())
            doris_sess.execute(text(f"INSERT INTO {qname} ({cols}) VALUES ({vals})"), filtered)

            doris_sess.commit()
            print(f"[MultiWriter] 已镜像到 Doris: {qname}")
        except SQLAlchemyError as e:
            doris_sess.rollback()
            print(f"[MultiWriter] Doris 写入失败: {str(e)}")
        except Exception as e:
            print(f"[MultiWriter] Doris 异步写入异常: {e}")
        finally:
            doris_sess.close()

def _doris_columns(sess: Session, table: str) -> Set[str]:
    """
    拉 Doris 端表结构，返回列名集合。
    优先 DESCRIBE；失败再试 SHOW FULL COLUMNS。
    """
    cols: Set[str] = set()
    dbname = _doris_dbname(sess)
    qname = _qualify(table, dbname)
    try:
        rs = sess.execute(text(f"DESCRIBE {qname}"))
        for row in rs:
            # Doris 的第一列是字段名（Field）
            name = row[0]
            if isinstance(name, str) and name:
                cols.add(name)
        if cols:
            return cols
    except Exception as e:
        print(f"[MultiWriter] DESCRIBE 失败：{qname} -> {e}")

    try:
        rs = sess.execute(text(f"SHOW FULL COLUMNS FROM {qname}"))
        for row in rs:
            name = row[0]
            if isinstance(name, str) and name:
                cols.add(name)
        if cols:
            return cols
    except Exception as e:
        print(f"[MultiWriter] SHOW FULL COLUMNS 失败：{qname} -> {e}")

    # 兜底：information_schema（能明确看出到底连到了哪个库）
    try:
        rs = sess.execute(
            text("""
                SELECT COLUMN_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = :db AND TABLE_NAME = :tbl
                ORDER BY ORDINAL_POSITION
            """),
            {"db": dbname, "tbl": table},
        )
        for row in rs:
            name = row[0]
            if isinstance(name, str) and name:
                cols.add(name)
        if cols:
            return cols
    except Exception as e:
        print(f"[MultiWriter] information_schema 查询失败：db={dbname}, table={table} -> {e}")

    # 打印调试信息，快速定位“连错库/库空”的问题
    try:
        curdb = sess.execute(text("SELECT DATABASE()")).scalar()
        tbls = list(sess.execute(text("SHOW TABLES")))
        print(f"[MultiWriter] ❌ 未找到表或列：{table} | 当前库={curdb} | SHOW TABLES={tbls[:10]}")
    except Exception:
        pass

    return cols


# ================ 扩展功能：用户参与度数据写入 Doris ================
def sync_user_participation_data_to_doris(db: Session, user_id: int):
    """
    这个函数用于将用户的参与度数据写入 Doris
    """
    # 获取用户的各类数据
    user_account = db.query(UserAccount).filter(UserAccount.id == user_id).first()
    user_intention = db.query(UserIntention).filter(UserIntention.user_id == user_id).first()
    user_lifestyle = db.query(UserLifestyle).filter(UserLifestyle.user_id == user_id).first()
    user_qna = db.query(UserQna).filter(UserQna.user_id == user_id).all()
    user_media = db.query(UserMedia).filter(UserMedia.user_id == user_id).all()
    user_certification = db.query(UserCertification).filter(UserCertification.user_id == user_id).all()
    user_profile_public = db.query(UserProfilePublic).filter(UserProfilePublic.user_id == user_id).first()

    # 确保数据已经加载并写入 Doris
    if user_account:
        MultiWriter.write(user_account, db=db, mirror=True)
    if user_intention:
        MultiWriter.write(user_intention, db=db, mirror=True)
    if user_lifestyle:
        MultiWriter.write(user_lifestyle, db=db, mirror=True)
    if user_qna:
        for qna in user_qna:
            MultiWriter.write(qna, db=db, mirror=True)
    if user_media:
        for media in user_media:
            MultiWriter.write(media, db=db, mirror=True)
    if user_certification:
        for cert in user_certification:
            MultiWriter.write(cert, db=db, mirror=True)
    if user_profile_public:
        MultiWriter.write(user_profile_public, db=db, mirror=True)

    # ------- 2) 喜欢关系（双向）UserLike -------
    # 你给的模式是以 id 为主键；若要（liker_id, likee_id）唯一，可以在 UPSERT_KEYS 改掉
    likes_from_me = db.query(UserLike).filter(UserLike.liker_id == user_id).all()
    likes_to_me   = db.query(UserLike).filter(UserLike.likee_id == user_id).all()
    for r in likes_from_me + likes_to_me:
        MultiWriter.write(r, db=db, mirror=True)

    # ------- 3) 关系阶段（双向）UserRelationStage -------
    rel_a = db.query(UserRelationStage).filter(UserRelationStage.user_a_id == user_id).all()
    rel_b = db.query(UserRelationStage).filter(UserRelationStage.user_b_id == user_id).all()
    for r in rel_a + rel_b:
        MultiWriter.write(r, db=db, mirror=True)

    # ------- 4) 隐私设置（单条或少量）UserPrivacy -------
    privacy = db.query(UserPrivacy).filter(UserPrivacy.user_id == user_id).all()
    for p in privacy:
        MultiWriter.write(p, db=db, mirror=True)

    # ------- 5) 黑名单（我拉黑谁）UserBlacklist -------
    bl = db.query(UserBlacklist).filter(UserBlacklist.user_id == user_id).all()
    for b in bl:
        MultiWriter.write(b, db=db, mirror=True)

    # ------- 6) 风险评估 RiskAssessment -------
    # 你的表定义：target_type=0 表示“用户”；target_id 为字符串 user_id
    risk_rows = db.query(RiskAssessment).filter(
        RiskAssessment.target_type == 0,
        RiskAssessment.target_id == str(user_id)
    ).all()
    for r in risk_rows:
        MultiWriter.write(r, db=db, mirror=True)

    # ------- 7) 审核/实名 UserVerification -------
    ver = db.query(UserVerification).filter(UserVerification.user_id == user_id).all()
    for v in ver:
        MultiWriter.write(v, db=db, mirror=True)
    
    # ------- 8) 匹配关系 Match -------
    match_rows = db.query(Match).filter(
        or_(Match.user_a == user_id, Match.user_b == user_id)
    ).all()
    for m in match_rows:
        MultiWriter.write(m, db=db, mirror=True)


# 调用这个函数进行数据同步
# 示例：同步用户ID为123的数据
if __name__ == "__main__":
    from app.database import SessionLocal as _SL
    _db = _SL()
    try:
        # 假设你想同步用户ID为123的数据
        sync_user_participation_data_to_doris(_db, user_id=123)
    finally:
        _db.close()

# ================ 队列类：DorisQueue（批量异步写）================
class DorisQueue:
    """
    用于行为日志、埋点事件等高频数据。
    异步队列批量刷入 Doris，每秒写一次，每次最多 100 条。
    用法：
        await DorisQueue.add(record)
    """

    _queue = asyncio.Queue()
    _started = False

    @classmethod
    async def worker(cls):
        """后台常驻任务：定期批量提交队列"""
        if SessionDoris is None:
            print("[DorisQueue] Doris 未配置，队列关闭。")
            return

        print("[DorisQueue] 后台异步写入任务已启动。")
        while True:
            try:
                batch: list[tuple[str, Dict[str, Any]]] = []
                while not cls._queue.empty() and len(batch) < 100:
                    batch.append(await cls._queue.get())

                if batch:
                    db = SessionDoris()
                    # 按表分组写入
                    by_table: dict[str, list[Dict[str, Any]]] = {}
                    for tbl, row in batch:
                        by_table.setdefault(tbl, []).append(row)

                    for tbl, rows in by_table.items():
                        doris_cols = _doris_columns(db, tbl)
                        rows2 = [{k: v for k, v in r.items() if k in doris_cols} for r in rows if r]
                        if not rows2:
                            continue

                        # 先逐行 delete（只用 UPSERT_KEYS），再批量 insert
                        key_cols = UPSERT_KEYS.get(tbl, ("id",))
                        qname = _qualify(tbl, _doris_dbname(db))

                        # delete（多行 delete 也可以循环执行；行数通常不大）
                        for r in rows2:
                            where = " AND ".join([f"`{k}` = :__key_{k}" for k in key_cols])
                            params = {f"__key_{k}": r[k] for k in key_cols}
                            db.execute(text(f"DELETE FROM {qname} WHERE {where}"), params)

                        # insert 批量
                        cols = list(rows2[0].keys())
                        col_sql = ", ".join(f"`{c}`" for c in cols)
                        val_sql = ", ".join(f":{c}" for c in cols)
                        sql = text(f"INSERT INTO {qname} ({col_sql}) VALUES ({val_sql})")
                        db.execute(sql, rows2)  # executemany
                    db.commit()
                    db.close()
                    print(f"[DorisQueue] ✅ 批量写入 {len(batch)} 条到 Doris。")
            except Exception as e:
                print(f"[DorisQueue] 批量写入异常: {e}")
            await asyncio.sleep(1)

    @classmethod
    def start(cls):
        """在 FastAPI 启动事件中调用"""
        if not cls._started:
            asyncio.create_task(cls.worker())
            cls._started = True

    @classmethod
    async def add(cls, table: str, record: Any):
        """record 可以是 ORM 或 dict；内部会拍平成 dict"""
        await cls._queue.put((table, _to_row(record)))
    
