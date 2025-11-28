# backend/app/scripts/build_training_pairs.py
# -*- coding: utf-8 -*-
import os, json, random
from typing import List, Tuple, Optional, Dict, Any, Set
from sqlalchemy import func, or_, and_, desc
from datetime import datetime, date, timedelta
from decimal import Decimal
import numpy as np

from app.database import SessionLocal
from app.services.recommend_service import RecommendService
from app.models.user import (
    UserAccount, UserProfilePublic, UserIntention, UserLifestyle,
    UserQna, UserMedia, UserLike, Match, UserBlacklist, UserRelationStage
)
# 兼容两种认证模型
try:
    from app.models.user import UserCertification  # 推荐
except Exception:
    UserCertification = None
try:
    from app.models.platform import UserVerification  # 旧
except Exception:
    UserVerification = None

from app.models.platform import RiskAssessment

# =============== 可调参数 ===============
OUT = "data/training_pairs.jsonl"

USE_MUTUAL_LIKE    = True
USE_MATCH          = True
USE_RELATION_STAGE = True   # dating / exclusive / off_the_shelf
USE_EVENTS         = True   # video / date

# 放宽时间窗（None 表示不限；否则整数天）
TIME_WINDOW_DAYS: Optional[int] = None

# 是否允许同性（数据少时建议 True）
ALLOW_SAME_GENDER = True

# 写双向
WRITE_BOTH_DIRECTIONS = True

# 上限与配比
POS_LIMIT_TOTAL = 20000
NEG_PER_POS     = 3
OVER_SAMPLE_K   = 8
MAX_POS_PER_USER = 500

# 近邻负样本阈值
NEAR_AGE_DIFF   = 3
NEAR_HEIGHT_DIFF = 5

# 高风险判定阈值（0~1）
HIGH_RISK_TH = 0.75

# 放宽的“正向 like 状态”映射
LIKE_POS_STATUSES = {
    "pending", "accepted", "agree", "ok", "mutual", "success", "liked", "like",
    "y", "yes", "1", "true"
}
# 明确的负向屏蔽（遇到这些就不计入互赞）
LIKE_NEG_STATUSES = {"rejected", "blocked", "cancelled", "2", "no", "false"}

def _json_default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (set, tuple)):
        return list(o)
    return str(o)

def _within_window(dt: Optional[datetime]) -> bool:
    if TIME_WINDOW_DAYS is None:
        return True
    if not dt:
        return True
    try:
        return (datetime.utcnow() - dt) <= timedelta(days=TIME_WINDOW_DAYS)
    except Exception:
        return True

def _age_from_birth(b: Optional[date]) -> Optional[int]:
    if not b: return None
    today = date.today()
    return today.year - b.year - ((today.month, today.day) < (b.month, b.day))

def _near_neighbor(a: UserAccount, b: UserAccount) -> bool:
    aa = _age_from_birth(a.birth_date) or 0
    bb = _age_from_birth(b.birth_date) or 0
    try:
        ha = int(a.height_cm or 0); hb = int(b.height_cm or 0)
    except Exception:
        ha = hb = 0
    same_city = (a.city and b.city and a.city == b.city)
    return (abs(aa - bb) <= NEAR_AGE_DIFF) or (ha and hb and abs(ha - hb) <= NEAR_HEIGHT_DIFF) or same_city

def _gender_compatible(a: UserAccount, b: UserAccount) -> bool:
    if ALLOW_SAME_GENDER:
        return True
    ga = (str(a.gender or "").lower())
    gb = (str(b.gender or "").lower())
    if not ga or not gb: return True
    return ga != gb

def _normalize_risk_value(v_raw: float) -> float:
    try:
        v = float(v_raw)
    except Exception:
        return 0.0
    if v > 1.5:   # 0~100 的情况
        v = v / 100.0
    return max(0.0, min(1.0, v))

def _risk_level_to_score(level: str) -> float:
    s = (level or "").strip().lower()
    if s in ("", "low", "safe", "normal"): return 0.05
    if s in ("mid", "medium"): return 0.35
    if s == "high": return 0.65
    if s in ("very_high", "extreme"): return 0.9
    return 0.35

def _risk_to_dict(session, user_id: int) -> Dict[str, Any]:
    q = session.query(RiskAssessment).filter(
        or_(
            RiskAssessment.target_id == str(user_id),
            getattr(RiskAssessment, "target_id", None) == user_id
        )
    )
    if hasattr(RiskAssessment, "updated_at"):
        q = q.order_by(desc(RiskAssessment.updated_at))
    elif hasattr(RiskAssessment, "created_at"):
        q = q.order_by(desc(RiskAssessment.created_at))
    else:
        q = q.order_by(desc(RiskAssessment.id))
    r = q.first()
    if not r:
        return {}
    for k in ("score", "risk_score", "risk"):
        if hasattr(r, k):
            try:
                return {"score": _normalize_risk_value(getattr(r, k))}
            except Exception:
                pass
    lvl_text = getattr(r, "risk_level", None) or getattr(r, "action", None) or getattr(r, "reason", None)
    return {"score": _risk_level_to_score(lvl_text or "")}

def _veri_to_dict(session, user_id: int) -> Dict[str, Any]:
    # 优先 UserCertification
    if UserCertification is not None:
        rows = session.query(UserCertification).filter_by(user_id=user_id).all()
        flags = {
            "id_verified": False, "education_verified": False,
            "income_verified": False, "job_verified": False,
            "house_verified": False, "face_verified": False
        }
        for r in rows or []:
            status_ok = str(getattr(r, "status", "")).lower() == "approved"
            t = str(getattr(r, "cert_type", "")).lower()
            if t == "identity": flags["id_verified"] |= status_ok
            elif t == "education": flags["education_verified"] |= status_ok
            elif t == "employment": flags["job_verified"] |= status_ok
            elif t == "income": flags["income_verified"] |= status_ok
            elif t == "asset": flags["house_verified"] |= status_ok
            elif t in ("photo_liveness", "video_liveness"): flags["face_verified"] |= status_ok
        return {k: v for k, v in flags.items() if v}
    # 兼容旧 UserVerification（可能只有一个总字段）
    if UserVerification is not None:
        v = session.query(UserVerification).filter_by(user_id=user_id).order_by(desc(UserVerification.id)).first()
        if not v: return {}
        d = {}
        for k in ("id_verified","education_verified","income_verified","job_verified","house_verified","face_verified"):
            if hasattr(v, k) and getattr(v, k):
                d[k] = True
        return d
    return {}

def _media_stub_list(medias: List[UserMedia]) -> List[Dict[str, Any]]:
    return [{"id": getattr(m, "id", i), "type": getattr(m, "media_type", None)} for i, m in enumerate(medias or [])]

def _pack_user(rs: RecommendService, session, u: UserAccount):
    prof  = session.query(UserProfilePublic).filter_by(user_id=u.id).one_or_none()
    it    = session.query(UserIntention).filter_by(user_id=u.id).one_or_none()
    life  = session.query(UserLifestyle).filter_by(user_id=u.id).one_or_none()
    qnas  = session.query(UserQna).filter_by(user_id=u.id).all()
    medias = session.query(UserMedia).filter_by(user_id=u.id).all()
    packed = rs._pack(u, prof, it, life, qnas, medias, verification=None, risk=None)
    packed["_verification"] = _veri_to_dict(session, u.id)
    packed["_risk"] = _risk_to_dict(session, u.id)
    packed["_media_list"] = _media_stub_list(medias)
    packed["_has_avatar"] = bool(packed.get("_has_avatar", bool(u.avatar_url)))
    return packed

def _like_status_ok(x: Any) -> bool:
    s = str(x or "").strip().lower()
    if s in LIKE_NEG_STATUSES:
        return False
    return (s in LIKE_POS_STATUSES) or s.isdigit() and (s == "1" or s == "2")  # 兼容 1/2 表示通过

def build_samples():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    rs = RecommendService()
    db = SessionLocal()

    try:
        # 1) 汇总正样本（无向）
        pos_pairs_undir: Set[Tuple[int, int]] = set()

        # ---- 互赞 ----
        like_total, like_window, like_dir = 0, 0, {}
        if USE_MUTUAL_LIKE:
            likes = db.query(UserLike).all()
            for r in likes:
                like_total += 1
                if not _within_window(getattr(r, "created_at", None)):  # created_at 可能为 None
                    continue
                like_window += 1
                if _like_status_ok(getattr(r, "status", None)):
                    like_dir[(r.liker_id, r.likee_id)] = True
            for (a, b) in list(like_dir.keys()):
                if (b, a) in like_dir:
                    pos_pairs_undir.add((min(a, b), max(a, b)))
        print(f"[STAT] UserLike 总计={like_total}, 时间窗内={like_window}, 互赞对数={len(pos_pairs_undir)}")

        # ---- Match ----
        match_cnt = 0
        if USE_MATCH:
            rows = db.query(Match).all()
            for r in rows:
                if _within_window(getattr(r, "created_at", None)):
                    pos_pairs_undir.add((min(r.user_a, r.user_b), max(r.user_a, r.user_b)))
                    match_cnt += 1
        print(f"[STAT] Match 记录（时间窗内计）={match_cnt}")

        # ---- 关系阶段 ----
        stage_cnt = 0
        if USE_RELATION_STAGE:
            rows = db.query(UserRelationStage).all()
            for r in rows or []:
                if not _within_window(getattr(r, "updated_at", None)):  # 宽松
                    continue
                st = str(getattr(r, "stage", "")).lower()
                if st in ("dating", "exclusive", "off_the_shelf", "met"):
                    pos_pairs_undir.add((min(r.user_a_id, r.user_b_id), max(r.user_a_id, r.user_b_id)))
                    stage_cnt += 1
        print(f"[STAT] RelationStage 命中（时间窗内计）={stage_cnt}")

        # ---- 事件（如有 UserEvent，可加上；这里保持可选导入）----
        event_cnt = 0
        try:
            from app.models.user import UserEvent
            if USE_EVENTS:
                rows = db.query(UserEvent).all()
                for e in rows or []:
                    if not _within_window(getattr(e, "start_at", None)):
                        continue
                    tp = str(getattr(e, "type", "")).lower()
                    if tp in ("video", "date"):
                        pos_pairs_undir.add((min(e.user_id, e.counterpart_id), max(e.user_id, e.counterpart_id)))
                        event_cnt += 1
            print(f"[STAT] UserEvent(video/date) 命中（时间窗内计）={event_cnt}")
        except Exception:
            print("[STAT] 未定义 UserEvent，跳过事件来源。")

        if not pos_pairs_undir:
            print("[WARN] 没找到任何正样本来源（互赞/Match/关系阶段/事件）。")
            with open(OUT, "w", encoding="utf-8") as f:
                pass
            return

        # 2) 载入用户、过滤性别、限制单用户占比
        user_ids = list({uid for ab in pos_pairs_undir for uid in ab})
        users: Dict[int, UserAccount] = {
            u.id: u for u in db.query(UserAccount).filter(UserAccount.id.in_(user_ids)).all()
        }
        before_gender = len(pos_pairs_undir)
        pos_pairs_undir = {
            (a, b) for (a, b) in pos_pairs_undir
            if (a in users and b in users and users[a].is_active and users[b].is_active and _gender_compatible(users[a], users[b]))
        }
        print(f"[STAT] 性别/活跃过滤：{before_gender} -> {len(pos_pairs_undir)}")

        cnt_per_user: Dict[int, int] = {}
        clamped: List[Tuple[int, int]] = []
        for (a, b) in sorted(list(pos_pairs_undir)):
            if cnt_per_user.get(a, 0) >= MAX_POS_PER_USER: continue
            if cnt_per_user.get(b, 0) >= MAX_POS_PER_USER: continue
            clamped.append((a, b))
            cnt_per_user[a] = cnt_per_user.get(a, 0) + 1
            cnt_per_user[b] = cnt_per_user.get(b, 0) + 1
        print(f"[STAT] 单用户上限裁剪：{len(pos_pairs_undir)} -> {len(clamped)} (MAX_POS_PER_USER={MAX_POS_PER_USER})")

        # 3) 写 JSONL：正负样本
        written_dir: Set[Tuple[int, int]] = set()
        n_pos_written = 0

        with open(OUT, "w", encoding="utf-8") as f:
            for (a, b) in clamped:
                if n_pos_written >= POS_LIMIT_TOTAL:
                    break
                ua = users.get(a); ub = users.get(b)
                if not ua or not ub:
                    continue
                dirs = [(ua, ub)]
                if WRITE_BOTH_DIRECTIONS:
                    dirs.append((ub, ua))

                for me_u, other_u in dirs:
                    if (me_u.id, other_u.id) in written_dir:
                        continue
                    me    = _pack_user(rs, db, me_u)
                    other = _pack_user(rs, db, other_u)
                    f.write(json.dumps({"me": me, "other": other, "label": 1},
                                       ensure_ascii=False, default=_json_default) + "\n")
                    written_dir.add((me_u.id, other_u.id))
                    n_pos_written += 1
                    if n_pos_written >= POS_LIMIT_TOTAL:
                        break

                    # 负样本
                    need = NEG_PER_POS
                    # (a) 随机
                    cands_rand = (
                        db.query(UserAccount)
                        .filter(
                            UserAccount.is_active == True,
                            UserAccount.id != me_u.id,
                            # 性别兼容：如果只允许异性，这里用 !=；允许同性则不加条件
                            *( [] if ALLOW_SAME_GENDER else [func.lower(UserAccount.gender) != func.lower(me_u.gender)] )
                        )
                        .order_by(func.random())
                        .limit(need * OVER_SAMPLE_K)
                        .all()
                    )
                    # (b) 近邻
                    cands_near = (
                        db.query(UserAccount)
                        .filter(
                            UserAccount.is_active == True,
                            UserAccount.id != me_u.id,
                            *( [] if ALLOW_SAME_GENDER else [func.lower(UserAccount.gender) != func.lower(me_u.gender)] )
                        )
                        .order_by(desc(UserAccount.updated_at))
                        .limit(need * OVER_SAMPLE_K)
                        .all()
                    )
                    cands_near = [x for x in cands_near if _near_neighbor(me_u, x)]

                    pool, seen = [], set()
                    for lst in (cands_near, cands_rand):
                        for v in lst:
                            if v.id in seen: continue
                            seen.add(v.id); pool.append(v)
                    random.shuffle(pool)

                    for v in pool:
                        if need <= 0:
                            break
                        # 跳过已是正样本
                        if (min(me_u.id, v.id), max(me_u.id, v.id)) in pos_pairs_undir:
                            continue
                        if (me_u.id, v.id) in written_dir:
                            continue
                        # 黑名单作为“硬负”
                        blk = db.query(UserBlacklist).filter(
                            or_(
                                and_(UserBlacklist.user_id == me_u.id, UserBlacklist.blocked_user_id == v.id),
                                and_(UserBlacklist.user_id == v.id,   UserBlacklist.blocked_user_id == me_u.id),
                            )
                        ).first()
                        v_other = _pack_user(rs, db, v)
                        label0 = 0
                        f.write(json.dumps({"me": me, "other": v_other, "label": label0},
                                           ensure_ascii=False, default=_json_default) + "\n")
                        written_dir.add((me_u.id, v.id))
                        need -= 1

        print(f"[OK] 写出正样本（有向）{n_pos_written} 条，每条配 {NEG_PER_POS} 个负样本 -> {OUT}")

    finally:
        db.close()

if __name__ == "__main__":
    build_samples()
