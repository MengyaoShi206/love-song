# backend/app/services/recommend_service.py
from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
import math
import re
from collections import defaultdict, Counter

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_, exists

from app.models.user import (
    UserAccount, UserProfilePublic, UserIntention,
    UserLifestyle, UserQna, UserBlacklist,
    UserMedia, UserLike, UserRelationStage, Match
)
from app.models.platform import (
    UserVerification, RiskAssessment
)
from app.services.ml_ranker import ml_ranker



# ============== 基础工具函数 ===========
def _age_from_birth(b: Optional[date]) -> Optional[int]:
    """根据生日计算年龄（按“过没过今年生日”精确到年）。"""
    if not b:
        return None
    today = date.today()
    return today.year - b.year - ((today.month, today.day) < (b.month, b.day))

def _listify(x) -> List[str]:
    """将输入统一转为字符串列表（去空白、去空项）。"""
    if not x:
        return []
    if isinstance(x, list):
        return [str(i).strip() for i in x if str(i).strip()]
    return [str(x).strip()]

def _norm_loc(s: Optional[str]) -> str:
    """地理字符串归一化：小写、去常见后缀。"""
    if not s:
        return ""
    t = str(s).strip().lower()
    for suf in ["省", "市", "区", "县", "特别行政区", "自治州", "盟"]:
        t = t.replace(suf, "")
    return t

def _same_loc(a: Optional[str], b: Optional[str]) -> bool:
    """判断两个地理字符串是否“同地”"""
    return _norm_loc(a) != "" and _norm_loc(a) == _norm_loc(b)

def _gender_opposite(g: Optional[str]) -> Optional[str]:
    """给定性别返回对向性别；未知返回 None。"""
    if not g:
        return None
    g = str(g).lower()
    if g in ("male", "m", "男"):
        return "female"
    if g in ("female", "f", "女"):
        return "male"
    return None

def _age_complement(a1: Optional[int], a2: Optional[int]) -> float:
    """年龄差舒适度：|Δ|<15 线性衰减"""
    if a1 is None or a2 is None:
        return 0.0
    diff = abs(a1 - a2)
    return max(0.0, 1.0 - diff / 15.0)

def _height_comfort(h1: Optional[int], h2: Optional[int]) -> float:
    """身高差舒适度：中心 12cm，容忍半宽 20cm"""
    if not h1 or not h2:
        return 0.0
    diff = abs(h1 - h2)
    center, width = 12.0, 20.0
    score = 1.0 - abs(diff - center) / width
    return max(0.0, min(1.0, score))

def _tokens_from_text(*fields: Optional[str]) -> List[str]:
    """
    从若干文本字段中提取“关键词 tokens”用于文本相似度：
    - 中文：连续 2 个及以上汉字
    - 英数：连续 2 个及以上字母/数字
    """
    text = " ".join([f or "" for f in fields]).lower()
    toks = re.findall(r'[\u4e00-\u9fff]{2,}|[a-z0-9]{2,}', text)
    return list(set(toks))

def _jaccard(a: List[str], b: List[str]) -> float:
    """Jaccard 相似度"""
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 0.0
    inter = len(sa & sb); union = len(sa | sb)
    return inter / union if union else 0.0

def _coalesce_enum(x: Optional[str]) -> Optional[str]:
    return str(x).strip().lower() if x else None

# ============== Lifestyle 评分 ==============
_LIKE_ENUM_FIELDS = [
    "schedule", "drinking", "smoking", "workout_freq", "diet",
    "pet_view", "spending_view", "saving_view"
]

_MB_TI_COMPLEMENTS = [
    ("intj", "enfp"), ("entp", "isfj"), ("istp", "enfj"),
    ("infj", "entp"), ("enfj", "istp"), ("enfp", "intj"),
]

def _mbti_score(a: Optional[str], b: Optional[str]) -> float:
    if not a or not b:
        return 0.0
    A, B = a.strip().lower(), b.strip().lower()
    if A == B:
        return 1.0
    pair = tuple(sorted([A, B]))
    for (x, y) in _MB_TI_COMPLEMENTS:
        if tuple(sorted([x, y])) == pair:
            return 0.6
    return 0.0

def _lifestyle_similarity(A: Dict[str, Any], B: Dict[str, Any]) -> Tuple[float, List[str]]:
    """生活方式相容度（0~1）：枚举一致 + 兴趣/旅行 Jaccard + MBTI"""
    reasons: List[str] = []
    la, lb = (A.get("lifestyle") or {}), (B.get("lifestyle") or {})
    if not la and not lb:
        return 0.0, reasons

    # 1) 枚举字段一致性
    hit = 0; tot = 0
    for f in _LIKE_ENUM_FIELDS:
        va = _coalesce_enum(la.get(f)); vb = _coalesce_enum(lb.get(f))
        if va is None or vb is None:
            continue
        tot += 1
        if va == vb:
            hit += 1
    enum_score = (hit / tot) if tot > 0 else 0.0
    if enum_score >= 0.6: reasons.append("生活方式偏好相近")

    # 2) 兴趣/旅行
    ja = _jaccard(_listify(la.get("interests")), _listify(lb.get("interests")))
    jt = _jaccard(_listify(la.get("travel_pref")), _listify(lb.get("travel_pref")))
    if ja >= 0.25: reasons.append("兴趣有交集")
    if jt >= 0.25: reasons.append("旅行偏好接近")

    # 3) MBTI
    mb = _mbti_score(la.get("personality"), lb.get("personality"))
    if mb >= 0.9: reasons.append("性格类型一致")
    elif mb >= 0.5: reasons.append("性格类型互补")

    score = 0.55 * enum_score + 0.25 * ja + 0.10 * jt + 0.10 * mb
    return max(0.0, min(1.0, score)), reasons

# ============== Like ==============
def _recent_like_stats(db: Session, uid: int, days: int = 30):
    """最近 N 天内的点赞映射"""
    since = datetime.utcnow() - timedelta(days=days)
    likes_me_rows = (
        db.query(UserLike)
        .filter(UserLike.likee_id == uid, UserLike.created_at >= since)
        .all()
    )
    likes_me = {r.liker_id: (r.status or "").lower() for r in likes_me_rows}

    my_ops_rows = (
        db.query(UserLike)
        .filter(UserLike.liker_id == uid, UserLike.created_at >= since)
        .all()
    )
    my_ops = {r.likee_id: (r.status or "").lower() for r in my_ops_rows}

    liked_sub = (
        db.query(UserLike.likee_id.label("uid"), func.count(UserLike.id).label("like_count"))
        .filter(UserLike.created_at >= since)
        .group_by(UserLike.likee_id)
        .subquery()
    )
    liked_map = {row.uid: row.like_count for row in db.query(liked_sub).all()}
    return likes_me, my_ops, liked_map

# ============== 可信与安全评分辅助 ==============
def _verification_score(v: Optional[UserVerification]) -> Tuple[float, List[str]]:
    """多维认证加分"""
    if not v:
        return 0.0, []
    reasons = []; score = 0.0
    def add(cond, pts, msg):
        nonlocal score
        if cond: score += pts; reasons.append(msg)

    add(getattr(v, "id_verified", False),        0.25, "实名已认证")
    add(getattr(v, "education_verified", False), 0.15, "学历已认证")
    add(getattr(v, "income_verified", False),    0.12, "收入已认证")
    add(getattr(v, "job_verified", False),       0.10, "职业已认证")
    add(getattr(v, "house_verified", False),     0.08, "房产已认证")
    add(getattr(v, "car_verified", False),       0.05, "车辆已认证")
    return min(1.0, score), reasons

def _risk_penalty(r: Optional[RiskAssessment]) -> Tuple[float, List[str]]:
    """风险折扣系数"""
    if not r:
        return 1.0, []
    level = (getattr(r, "risk_level", "") or "").lower()
    reasons = []; coef = 1.0
    if level in ("low", "safe", "normal", ""):
        coef = 1.0
    elif level in ("mid", "medium"):
        coef = 0.85; reasons.append("中等风险降权")
    elif level in ("high",):
        coef = 0.65; reasons.append("高风险降权")
    elif level in ("very_high", "extreme"):
        coef = 0.40; reasons.append("极高风险强降权")
    return coef, reasons

def _media_score(medias: List[UserMedia], has_avatar: bool) -> Tuple[float, List[str]]:
    """媒体充足度：头像 + 相册数"""
    cnt = len(medias or []); base = 0.0; reasons = []
    if has_avatar: base += 0.15; reasons.append("有头像")
    if cnt >= 3: base += 0.20; reasons.append("相册丰富")
    elif cnt == 2: base += 0.12; reasons.append("相册较为充足")
    elif cnt == 1: base += 0.06; reasons.append("有相册")
    return min(0.35, base), reasons

def _like_signal(me_id: int, other_id: int, likes_me: Dict[int, str],
                 my_ops: Dict[int, str]) -> Tuple[float, List[str]]:
    """社交信号加减分"""
    reasons = []; score = 0.0
    s_other = (likes_me.get(other_id) or "").lower()
    s_mine  = (my_ops.get(other_id)  or "").lower()
    if s_other in ("pending", "accepted"):
        score += 0.35; reasons.append("对方已喜欢你")
    if s_mine in ("pending", "accepted"):
        score += 0.10; reasons.append("你也对TA有好感")
    if s_mine in ("rejected",):
        score -= 0.25; reasons.append("你曾拒绝TA")
    return max(-0.25, min(0.45, score)), reasons

def _relstage_filter_or_penalty(me_id: int, other_id: int,
                                stage_row: Optional[UserRelationStage]) -> Tuple[bool, float, List[str]]:
    """
    关系阶段过滤/降权：
    - exclusive/relationship/engaged/married: 过滤
    - chatting/met: 轻微降权
    """
    if not stage_row:
        return False, 0.0, []
    reasons: List[str] = []
    pair_stage = (getattr(stage_row, "stage", "") or "").lower()
    if pair_stage in ("exclusive", "relationship", "engaged", "married"):
        reasons.append("你们已进入稳定关系，已从推荐中过滤")
        return True, 0.0, reasons
    if pair_stage in ("chatting", "met"):
        reasons.append("你们已互动，轻微降权")
        return False, -0.08, reasons
    return False, 0.0, reasons

# ================== 🔶 多路召回 · 工具函数 ==================

# 维度重要性权重（关联规则召回用）
_TAG_DIM_WEIGHT = {
    "int": 1.00,      # interests
    "per": 1.15,      # personality
    "city": 0.85,     # 城市
    "home": 0.85,     # 籍贯
}

def _tagify_from_user(u: UserAccount,
                      life: Optional[UserLifestyle],
                      prof: Optional[UserProfilePublic]) -> Dict[str, List[str]]:
    """
    为“关联规则”抽取用户标签：
    - interests -> int:xxx
    - personality(MBTI或自定义字符串) -> per:xxx
    - city/hometown -> city:xxx / home:xxx
    """
    tags: Dict[str, List[str]] = defaultdict(list)
    if life:
        for it in _listify(life.interests):
            tags["int"].append(str(it).strip().lower())
        if life.personality:
            tags["per"].append(str(life.personality).strip().lower())
    if u.city:
        tags["city"].append(_norm_loc(u.city))
    if getattr(u, "hometown", None):
        tags["home"].append(_norm_loc(u.hometown))
    return tags

def _flatten_tag_dict(d: Dict[str, List[str]]) -> List[str]:
    """{'int':['球','咖啡'], 'per':['intj']} -> ['int:球','int:咖啡','per:intj']"""
    out: List[str] = []
    for k, arr in d.items():
        for v in arr:
            if v:
                out.append(f"{k}:{v}")
    return out

def _cosine(a: List[float], b: List[float]) -> float:
    """余弦相似度（软依赖 numpy，缺失则用纯 Python）"""
    try:
        import numpy as np
        va = np.array(a, dtype=float); vb = np.array(b, dtype=float)
        na = float(np.linalg.norm(va)); nb = float(np.linalg.norm(vb))
        if na == 0.0 or nb == 0.0:
            return 0.0
        return float(np.dot(va, vb) / (na * nb))
    except Exception:
        # 纯 Python 兜底
        num = sum(x*y for x, y in zip(a, b))
        da = math.sqrt(sum(x*x for x in a)); db = math.sqrt(sum(y*y for y in b))
        if da == 0.0 or db == 0.0:
            return 0.0
        return num / (da * db)

def _build_core_vector(u: UserAccount,
                       prof: Optional[UserProfilePublic],
                       life: Optional[UserLifestyle]) -> List[float]:
    """
    “核心特征向量”（尽量贴近你说的12变量；缺失则置0）：
    [ age, height, bmi, city_flag, hometown_flag,
      per_is_set, interests_len, completion_score_norm ]
    - 你可以把这里替换成你有的人格/问卷分量表；现版对你库友好。
    """
    age = float(_age_from_birth(u.birth_date) or 0)
    height = float(u.height_cm or 0)
    weight = float(getattr(u, "weight_kg", 0) or 0)
    bmi = (weight / ((height/100.0)**2)) if height and weight else 0.0
    city_flag = 1.0 if u.city else 0.0
    home_flag = 1.0 if getattr(u, "hometown", None) else 0.0
    per_flag = 1.0 if (life and life.personality) else 0.0
    interests_len = float(len(_listify(life.interests)) if life and life.interests else 0.0)
    completion = float((prof.completion_score or 0) if prof else 0) / 100.0
    # 简单归一：年龄/身高按常见范围粗归一
    age_n = age / 60.0
    height_n = height / 200.0
    bmi_n = min(1.5, max(0.0, bmi / 30.0))
    return [age_n, height_n, bmi_n, city_flag, home_flag, per_flag, interests_len/20.0, completion]

# ================== 🔶 三路召回实现 ==================

def _mine_tag_rules_from_matches(db: Session,
                                 min_support: int = 3,
                                 min_conf: float = 0.15,
                                 topk_per_tag: int = 5) -> Dict[str, List[Tuple[str, float]]]:
    """
    从 Match 表挖“标签 → 标签”的跨性别关联规则（双向）。
    返回： antecedent_tag -> [(consequent_tag, weight_conf), ...]
    """
    # 1) 拉出一批历史成对（或你也可以拉 user_like 的 accepted）
    pairs: List[Tuple[int, int]] = []
    for m in db.query(Match).all():
        if not m.user_a or not m.user_b:
            continue
        pairs.append((m.user_a, m.user_b))

    if not pairs:
        return {}

    # 2) 批量取四张表
    ids = list(set([i for ab in pairs for i in ab]))
    acc_map = {u.id: u for u in db.query(UserAccount).filter(UserAccount.id.in_(ids)).all()}
    life_map = {l.user_id: l for l in db.query(UserLifestyle).filter(UserLifestyle.user_id.in_(ids)).all()}
    prof_map = {p.user_id: p for p in db.query(UserProfilePublic).filter(UserProfilePublic.user_id.in_(ids)).all()}

    # 3) 统计 co-occurrence
    # a_tag -> count
    ante_cnt: Counter[str] = Counter()
    # (a_tag, b_tag) -> count
    pair_cnt: Counter[Tuple[str, str]] = Counter()

    for a_id, b_id in pairs:
        ua = acc_map.get(a_id); ub = acc_map.get(b_id)
        if not ua or not ub:
            continue
        ta = _flatten_tag_dict(_tagify_from_user(ua, life_map.get(a_id), prof_map.get(a_id)))
        tb = _flatten_tag_dict(_tagify_from_user(ub, life_map.get(b_id), prof_map.get(b_id)))
        # 双向都统计一遍，保证男女互为规则来源
        for t in set(ta):
            ante_cnt[t] += 1
        for t in set(tb):
            ante_cnt[t] += 1
        for ta1 in set(ta):
            for tb1 in set(tb):
                pair_cnt[(ta1, tb1)] += 1
                pair_cnt[(tb1, ta1)] += 1

    # 4) 生成规则
    rules: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    for (a_tag, b_tag), c in pair_cnt.items():
        if c < min_support:
            continue
        a_total = ante_cnt.get(a_tag, 0) or 1
        conf = c / a_total  # 置信度
        if conf < min_conf:
            continue
        # 维度加权
        a_dim = a_tag.split(":", 1)[0]
        w = _TAG_DIM_WEIGHT.get(a_dim, 1.0)
        rules[a_tag].append((b_tag, conf * w))

    # 5) 每个前件只保留 topk
    for k in list(rules.keys()):
        arr = sorted(rules[k], key=lambda x: x[1], reverse=True)[:topk_per_tag]
        rules[k] = arr
    return rules

def _recall_by_association(db: Session,
                           me: UserAccount,
                           base_candidates: List[UserAccount],
                           limit_each: int = 30) -> List[int]:
    """路一：关联规则·标签召回 —— 返回 user_id 列表"""
    # 1) 我的标签
    me_life = db.query(UserLifestyle).filter(UserLifestyle.user_id == me.id).first()
    me_prof = db.query(UserProfilePublic).filter(UserProfilePublic.user_id == me.id).first()
    my_tags = _flatten_tag_dict(_tagify_from_user(me, me_life, me_prof))
    if not my_tags:
        return []

    # 2) 规则（可考虑做缓存，这里直接现挖）
    rules = _mine_tag_rules_from_matches(db)
    if not rules:
        return []

    # 3) 由我的标签推扩展标签
    target_tag_weight: Counter[str] = Counter()
    for t in my_tags:
        for (tt, w) in rules.get(t, []):
            target_tag_weight[tt] += w

    if not target_tag_weight:
        return []

    # 4) 候选人打分：拥有的目标标签匹配越多，分越高
    # 预取候选侧的 lifestyle/profile
    pool_ids = [u.id for u in base_candidates]
    life_map = {l.user_id: l for l in db.query(UserLifestyle).filter(UserLifestyle.user_id.in_(pool_ids)).all()}
    prof_map = {p.user_id: p for p in db.query(UserProfilePublic).filter(UserProfilePublic.user_id.in_(pool_ids)).all()}

    scored: List[Tuple[int, float]] = []
    for u in base_candidates:
        tags = _flatten_tag_dict(_tagify_from_user(u, life_map.get(u.id), prof_map.get(u.id)))
        if not tags:
            continue
        s = 0.0
        for t in set(tags):
            s += target_tag_weight.get(t, 0.0)
        if s > 0.0:
            scored.append((u.id, float(s)))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [uid for uid, _ in scored[:limit_each]]

def _recall_by_similarity_second_order(db: Session,
                                       me: UserAccount,
                                       base_candidates: List[UserAccount],
                                       limit_each: int = 30) -> List[int]:
    """
    路二：二阶特征相似度召回
    - 一阶：core_vector(me) vs core_vector(other)
    - 二阶：构造“邻域均值向量”（同性别、与我最相似的前 K=50 位），
            用 other_vector 与该均值的余弦再加权融合
    """
    # 预取
    ids = [u.id for u in base_candidates]
    life_map = {l.user_id: l for l in db.query(UserLifestyle).filter(UserLifestyle.user_id.in_(ids + [me.id])).all()}
    prof_map = {p.user_id: p for p in db.query(UserProfilePublic).filter(UserProfilePublic.user_id.in_(ids + [me.id])).all()}

    me_vec = _build_core_vector(me, prof_map.get(me.id), life_map.get(me.id))

    # 同性别的“锚点用户”作为邻域（控制规模）
    same_gender_q = db.query(UserAccount).filter(
        UserAccount.is_active == True,
        UserAccount.id != me.id,
        func.lower(UserAccount.gender) == func.lower(me.gender)
    ).order_by(desc(UserAccount.updated_at)).limit(600).all()

    # 计算与我最相近的 K 个锚点，做邻域均值
    anchor_vecs: List[List[float]] = []
    for u in same_gender_q:
        v = _build_core_vector(u, prof_map.get(u.id), life_map.get(u.id))
        anchor_vecs.append((v, _cosine(me_vec, v)))
    anchor_vecs.sort(key=lambda x: x[1], reverse=True)
    K = 50
    anchors = [vec for vec, _ in anchor_vecs[:K]] or [me_vec]

    # 均值向量
    try:
        import numpy as np
        neigh_mean = list(np.mean(np.array(anchors, dtype=float), axis=0))
    except Exception:
        # 纯 Python 平均
        dim = len(anchors[0])
        acc = [0.0] * dim
        for v in anchors:
            for i in range(dim):
                acc[i] += v[i]
        neigh_mean = [x / len(anchors) for x in acc]

    # 对候选人打分：一阶 + 二阶
    scored: List[Tuple[int, float]] = []
    for u in base_candidates:
        v = _build_core_vector(u, prof_map.get(u.id), life_map.get(u.id))
        s1 = _cosine(me_vec, v)
        s2 = _cosine(neigh_mean, v)
        s = 0.7 * s1 + 0.3 * s2
        if s > 0:
            scored.append((u.id, float(s)))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [uid for uid, _ in scored[:limit_each]]

def _recall_by_kmeans(db: Session,
                      me: UserAccount,
                      base_candidates: List[UserAccount],
                      limit_each: int = 30,
                      k: int = 10) -> List[int]:
    """
    路三：KMeans 聚类召回（无 sklearn 则回退到年龄±3/身高±5 的近似簇）
    """
    ids = [u.id for u in base_candidates]
    life_map = {l.user_id: l for l in db.query(UserLifestyle).filter(UserLifestyle.user_id.in_(ids + [me.id])).all()}
    prof_map = {p.user_id: p for p in db.query(UserProfilePublic).filter(UserProfilePublic.user_id.in_(ids + [me.id])).all()}

    # 特征矩阵
    pool = base_candidates[:]
    X = [_build_core_vector(u, prof_map.get(u.id), life_map.get(u.id)) for u in pool]
    me_vec = _build_core_vector(me, prof_map.get(me.id), life_map.get(me.id))

    try:
        import numpy as np
        from sklearn.cluster import KMeans
        X_np = np.array(X, dtype=float)
        # 简易 KMeans
        km = KMeans(n_clusters=k, random_state=42, n_init="auto")
        labels = km.fit_predict(X_np)
        me_label = km.predict(np.array([me_vec]))[0]

        # 取与我同簇的候选，按与我距离升序（近的优先）
        def dist(a, b):
            # 欧氏距离
            return float(np.linalg.norm(np.array(a) - np.array(b)))

        same_cluster = [(pool[i].id, -dist(X[i], me_vec)) for i in range(len(pool)) if labels[i] == me_label]
        same_cluster.sort(key=lambda x: x[1], reverse=True)
        return [uid for uid, _ in same_cluster[:limit_each]]

    except Exception:
        # 回退：粗近邻（年龄±3岁 & 身高±5cm）
        me_age = _age_from_birth(me.birth_date) or 0
        me_h = int(me.height_cm or 0)
        tmp = []
        for u in pool:
            ua = _age_from_birth(u.birth_date) or 0
            uh = int(u.height_cm or 0)
            if abs(ua - me_age) <= 3 and (me_h == 0 or uh == 0 or abs(uh - me_h) <= 5):
                tmp.append(u.id)
        return tmp[:limit_each]

# ============ 推荐主服务 =============
class RecommendService:
    """
    为您推荐（多路召回版）：
    - 召回：三路并联（关联规则 / 二阶相似 / 聚类）各取30，合并≤90
    - 打分：相似度（文本/地域） + 互补性（年龄/身高） + 双向意向 + 可信安全
    - 重排：MMR 多样性
    - 冷启动：资料完善度 + 活跃度兜底
    """
    def __init__(self) -> None:
        self.w = {
            "similarity":      0.30,
            "complementarity": 0.20,
            "intention":       0.25,
            "lifestyle":       0.15,
            "trust_safety":    0.10,
        }
        self.mmr_lambda = 0.78  # 越大越重分数、越小越重多样性

    # ---------- 基础硬筛 ----------
    def _base_filter_query(self, db: Session, me: UserAccount):
        """构造“硬筛”查询（性别/异地/黑名单）作为三路召回的基础候选集"""
        intent = db.query(UserIntention).filter(UserIntention.user_id == me.id).first()
        q = db.query(UserAccount).filter(UserAccount.is_active == True, UserAccount.id != me.id)

        # 性别过滤
        opp = _gender_opposite(me.gender)
        if opp:
            q = q.filter(func.lower(UserAccount.gender) == opp)

        # 异地策略
        if intent and intent.accept_long_distance is False:
            if me.city:
                q = q.filter(UserAccount.city == me.city)
            elif me.hometown:
                q = q.filter(UserAccount.hometown == me.hometown)

        # 黑名单互斥
        q = q.filter(
            ~exists().where(and_(UserBlacklist.user_id == me.id,
                                 UserBlacklist.blocked_user_id == UserAccount.id))
        ).filter(
            ~exists().where(and_(UserBlacklist.user_id == UserAccount.id,
                                 UserBlacklist.blocked_user_id == me.id))
        )
        return q

    def _recall_candidates(self, db: Session, me: UserAccount, limit_pool: int = 500) -> List[UserAccount]:
        """
        多路召回（新）：
        1) 先用硬筛拿一大池（按活跃倒序）作为三路召回的“基底池”
        2) 三路各取 30：关联规则 / 二阶相似 / KMeans
        3) 合并去重 ≤ limit_pool
        """
        # 1) 基底池
        base_q = self._base_filter_query(db, me)
        base_pool = base_q.order_by(desc(UserAccount.updated_at)).limit(max(limit_pool, 1200)).all()
        if not base_pool:
            return []

        # 2) 三路召回（各取30）
        assoc_ids = _recall_by_association(db, me, base_pool, limit_each=30)
        sim2_ids  = _recall_by_similarity_second_order(db, me, base_pool, limit_each=30)
        km_ids    = _recall_by_kmeans(db, me, base_pool, limit_each=30, k=10)

        # 3) 合并去重（保留相对顺序：关联→相似→聚类）
        seen = set()
        merged_ids: List[int] = []
        for arr in (assoc_ids, sim2_ids, km_ids):
            for uid in arr:
                if uid not in seen:
                    seen.add(uid); merged_ids.append(uid)
                if len(merged_ids) >= min(90, limit_pool):
                    break

        if not merged_ids:
            # 回退：直接用基底池的前 N
            merged = base_pool[:min(90, limit_pool)]
        else:
            # 按 ID 拉对象，保证顺序
            acc_map = {u.id: u for u in db.query(UserAccount).filter(UserAccount.id.in_(merged_ids)).all()}
            merged = [acc_map[i] for i in merged_ids if i in acc_map]

        return merged

    # ---------- 打包特征 ----------
    def _pack(self, u: UserAccount,
              prof: Optional[UserProfilePublic],
              it: Optional[UserIntention],
              life: Optional[UserLifestyle],
              qna_list: Optional[List[UserQna]],
              medias: Optional[List[UserMedia]],
              verification: Optional[UserVerification],
              risk: Optional[RiskAssessment]) -> Dict[str, Any]:
        """打包用于打分/展示的特征字典"""
        tagline = (prof.tagline if prof else "") or ""
        bio = (prof.bio if prof else "") or ""
        qna_text = " ".join([(q.question or "") + " " + (q.answer or "")
                            for q in (qna_list or []) if getattr(q, "visible", True)])
        kw_tokens = _tokens_from_text(tagline, bio, qna_text)

        lifestyle_blob = {
            "schedule": life.schedule if life else None,
            "drinking": life.drinking if life else None,
            "smoking": life.smoking if life else None,
            "workout_freq": life.workout_freq if life else None,
            "diet": life.diet if life else None,
            "pet_view": life.pet_view if life else None,
            "spending_view": life.spending_view if life else None,
            "saving_view": life.saving_view if life else None,
            "travel_pref": list(life.travel_pref) if life and life.travel_pref else [],
            "interests": list(life.interests) if life and life.interests else [],
            "personality": life.personality if life else None,
        }

        has_avatar = bool(u.avatar_url)
        media_list = medias or []

        return {
            "id": u.id,
            "nickname": u.nickname,
            "gender": u.gender,
            "city": u.city,
            "hometown": getattr(u, "hometown", None),
            "age": _age_from_birth(u.birth_date),
            "height_cm": int(u.height_cm or 0) if u.height_cm is not None else None,
            "marital_status": u.marital_status,
            "has_children": bool(u.has_children),
            "avatar_url": u.avatar_url,
            "completion_score": int((prof.completion_score if prof else 0) or 0),
            "tagline": tagline,
            "bio": bio,
            "updated_at": (prof.updated_at if prof and prof.updated_at else u.updated_at),
            "kw_tokens": kw_tokens,
            "lifestyle": lifestyle_blob,
            "intent": {
                "preferred_age_min": it.preferred_age_min if it else None,
                "preferred_age_max": it.preferred_age_max if it else None,
                "preferred_height_min": it.preferred_height_min if it else None,
                "preferred_height_max": it.preferred_height_max if it else None,
                "preferred_cities": _listify(it.preferred_cities) if it else [],
                "accept_long_distance": it.accept_long_distance if it else None,
                "accept_divorce": it.accept_divorce if it else None,
                "accept_children": it.accept_children if it else None,
                "marriage_timeline": it.marriage_timeline if it else None,
                "child_plan": it.child_plan if it else None,
            },
            "_verification": verification,
            "_risk": risk,
            "_media_list": media_list,
            "_has_avatar": has_avatar,
        }

    # ---------- 打分 ----------
    def _intention_fit(self, A: Dict[str, Any], B: Dict[str, Any]) -> Tuple[float, List[str]]:
        """双向意向契合评分"""
        reasons: List[str] = []
        aint, bint = A["intent"] or {}, B["intent"] or {}
        score = 0.0

        # 年龄区间（双向）
        def _age_ok(target: Dict[str, Any], pref: Dict[str, Any]) -> bool:
            pa_min, pa_max = pref.get("preferred_age_min"), pref.get("preferred_age_max")
            return (target.get("age") is not None and pa_min is not None and pa_max is not None
                    and pa_min <= target["age"] <= pa_max)

        if _age_ok(B, aint): score += 0.35; reasons.append("对方年龄在你的偏好内")
        if _age_ok(A, bint): score += 0.20

        # 身高区间（双向）
        def _height_ok(target: Dict[str, Any], pref: Dict[str, Any]) -> bool:
            ph_min, ph_max = pref.get("preferred_height_min"), pref.get("preferred_height_max")
            return (target.get("height_cm") and ph_min is not None and ph_max is not None
                    and ph_min <= target["height_cm"] <= ph_max)

        if _height_ok(B, aint): score += 0.15; reasons.append("身高合你偏好")
        if _height_ok(A, bint): score += 0.10

        # 城市/异地（双向）
        def _city_fit(me: Dict[str, Any], other: Dict[str, Any], pref: Dict[str, Any]) -> bool:
            accept_ld = pref.get("accept_long_distance")
            pref_cities = set(pref.get("preferred_cities") or [])
            if accept_ld is False:
                return bool(me.get("city") and other.get("city") and me["city"] == other["city"]) or \
                       bool(_same_loc(me.get("hometown"), other.get("hometown")))
            if pref_cities:
                return (other.get("city") in pref_cities) or (other.get("hometown") in pref_cities)
            return True

        if _city_fit(A, B, aint):
            score += 0.10
            if A.get("city") and B.get("city") and A["city"] == B["city"]:
                reasons.append("同城匹配你的偏好")
            elif _same_loc(A.get("hometown"), B.get("hometown")):
                reasons.append("籍贯相近更有共鸣")
        if _city_fit(B, A, bint): score += 0.05

        # 婚育观
        acc_div = aint.get("accept_divorce")
        if acc_div is False and str(B.get("marital_status") or "").lower() == "divorced":
            score -= 0.15; reasons.append("你不接受离异（扣分）")
        acc_child = aint.get("accept_children")
        if acc_child is False and bool(B.get("has_children")):
            score -= 0.15; reasons.append("你不接受带娃（扣分）")

        # 计划与时间线
        if aint.get("marriage_timeline") and bint.get("marriage_timeline") \
            and aint["marriage_timeline"] == bint["marriage_timeline"]:
            score += 0.07; reasons.append("婚恋时间线一致")
        if aint.get("child_plan") and bint.get("child_plan") \
            and aint["child_plan"] == bint["child_plan"]:
            score += 0.08; reasons.append("生育计划一致")

        score = max(0.0, min(1.0, score))
        return score, reasons

    def _score_one(self,
        me: Dict[str, Any],
        other: Dict[str, Any],
        likes_me: Optional[Dict[int, str]] = None,
        my_ops: Optional[Dict[int, str]] = None,
        pair_stage_map: Optional[Dict[int, "UserRelationStage"]] = None,
        liked_map: Optional[Dict[int, int]] = None,
    ) -> Tuple[float, Dict[str, Any], bool]:
        """单候选样本打分"""

        import os
        ML_ALPHA = float(os.getenv("ML_WEIGHT", "0.4"))
        DEBUG_ML = os.getenv("ML_DEBUG", "0") == "1"

        likes_me = likes_me or {}
        my_ops = my_ops or {}
        pair_stage_map = pair_stage_map or {}

        reasons: List[str] = []

        # 1) 关系阶段过滤/降权
        stage_row = pair_stage_map.get(other["id"])
        should_filter = False; rel_penalty = 0.0
        if stage_row is not None:
            should_filter, rel_penalty, rel_reasons = _relstage_filter_or_penalty(
                me_id=me["id"], other_id=other["id"], stage_row=stage_row
            )
            if should_filter: return 0.0, {"reasons": rel_reasons}, True
            reasons.extend(rel_reasons)

        # 2) 相似度（文本&地域）
        sim_kw = _jaccard(me.get("kw_tokens", []), other.get("kw_tokens", []))
        if sim_kw >= 0.25: reasons.append(f"资料关键词相近 {int(sim_kw*100)}%")
        sim_city = 1.0 if me.get("city") and me["city"] == other.get("city") else 0.0
        if sim_city == 1.0: reasons.append("同城更易线下见面")
        sim_home = 1.0 if _same_loc(me.get("hometown"), other.get("hometown")) else 0.0
        if sim_home == 1.0 and sim_city == 0.0: reasons.append("同乡更有话题")
        sim_score = 0.55 * sim_kw + 0.25 * sim_city + 0.20 * sim_home

        # 3) 互补性
        comp_gender = 1.0 if (_gender_opposite(me.get("gender")) == str(other.get("gender")).lower()
                               or _gender_opposite(other.get("gender")) == str(me.get("gender")).lower()) else 0.5
        comp_age = _age_complement(me.get("age"), other.get("age"))
        comp_height = _height_comfort(me.get("height_cm"), other.get("height_cm"))
        if comp_gender >= 0.9: reasons.append("性别互补")
        if comp_age >= 0.6: reasons.append("年龄差舒适")
        if comp_height >= 0.6: reasons.append("身高差舒适")
        comp_score = 0.34 * comp_gender + 0.33 * comp_age + 0.33 * comp_height

        # 4) 双向意向契合
        intent_score, intent_reasons = self._intention_fit(me, other)
        reasons.extend(intent_reasons)

        # 5) 生活方式相容
        life_score, life_reasons = _lifestyle_similarity(me, other)
        reasons.extend(life_reasons)

        # 6) 可信与安全
        ver_score, ver_reasons = _verification_score(other.get("_verification"))
        risk_coef, risk_reasons = _risk_penalty(other.get("_risk"))
        med_score, med_reasons = _media_score(other.get("_media_list", []), other.get("_has_avatar", False))
        like_score, like_reasons = _like_signal(me["id"], other["id"], likes_me, my_ops)
        trust_raw = 0.55 * ver_score + 0.25 * med_score + 0.20 * max(0.0, like_score)
        trust_safety = max(0.0, min(1.0, trust_raw)) * risk_coef
        reasons.extend(ver_reasons + med_reasons + like_reasons + risk_reasons)

        # 7) 融合
        total_rule = (self.w["similarity"] * sim_score +
                 self.w["complementarity"] * comp_score +
                 self.w["intention"] * intent_score +
                 self.w["lifestyle"] * life_score +
                 self.w["trust_safety"] * trust_safety +
                 rel_penalty)
        # === 新增：XGB-DNN 排序分 ===
        ml_score = 0.00
        try:
            if ml_ranker.available():
                ml_score = ml_ranker.predict_pair(me, other)  # 0~1 概率
        except Exception:
            ml_score = 0.00

        # 8) 受欢迎度微加成
        if liked_map is not None:
            popularity = math.log1p(liked_map.get(other["id"], 0)) / 5.0  # 0~0.3
            total_rule += 0.05 * min(1.0, popularity)
            
        # 规则分与模型分加权融合（用环境变量控制）
        total = (1.0 - ML_ALPHA) * total_rule + ML_ALPHA * ml_score

        detail = {
            "similarity": round(sim_score, 4),
            "complementarity": round(comp_score, 4),
            "intention_fit": round(intent_score, 4),
            "lifestyle": round(life_score, 4),
            "trust_safety": round(trust_safety, 4),
            "reasons": reasons[:4],
        }
        if DEBUG_ML:
            detail["_ml"] = {
                "used": bool(ml_ranker.available()),
                "rule_score": round(total_rule, 4),
                "ml_score": round(ml_score, 4),
                "alpha": ML_ALPHA,
            }
        print("total_rule:",total_rule,"; ml_score:",ml_score,"; total:",total)
        return float(total), detail, False

    # ---------- MMR ----------
    def _mmr_rerank(self, items: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
        """MMR 多样性重排"""
        if not items:
            return []

        def pair_sim(a, b) -> float:
            s_kw = _jaccard(a.get("kw_tokens", []), b.get("kw_tokens", []))
            s_loc = 0.5 * (1.0 if a.get("city") and a["city"] == b.get("city") else 0.0) + \
                    0.5 * (1.0 if _same_loc(a.get("hometown"), b.get("hometown")) else 0.0)
            return float(max(0.0, min(1.0, 0.7 * s_kw + 0.3 * s_loc)))

        selected: List[Dict[str, Any]] = []
        pool = items[:]
        city_cnt: Dict[str, int] = {}
        total = min(k, len(pool))
        city_limit = max(2, int(total * 0.5))

        while pool and len(selected) < k:
            best_idx, best_val = 0, -1e9
            for i, c in enumerate(pool[:80]):  # 头部窗口控算力
                city = (c.get("city") or "").strip()
                if city and city_cnt.get(city, 0) >= city_limit:
                    continue
                if not selected:
                    mmr = c["_score"]
                else:
                    max_sim = max(pair_sim(c, s) for s in selected)
                    mmr = self.mmr_lambda * c["_score"] - (1 - self.mmr_lambda) * max_sim
                if mmr > best_val:
                    best_val, best_idx = mmr, i

            pick = pool.pop(best_idx)
            sel_city = (pick.get("city") or "").strip()
            if sel_city:
                city_cnt[sel_city] = city_cnt.get(sel_city, 0) + 1
            selected.append(pick)
        return selected

    # ---------- 主流程 ----------
    def recommend_for_user(self, db: Session, uid: int, limit: int = 20, page: int = 1,
                           min_completion: int = 30,
                           exclude_liked: bool = False,
                           exclude_matched: bool = False) -> Dict[str, Any]:
        """
        主流程：
        1) 读我方资料
        2) 三路召回（合并≤90）
        3) 批量查候选侧并逐个打分
        4) 初排 → MMR 重排
        5) 冷启动补齐
        """
        limit = max(1, min(int(limit or 20), 100))
        page  = max(1, int(page or 1))

        # 1) 我方
        me = db.query(UserAccount).filter(UserAccount.id == uid, UserAccount.is_active == True).first()
        if not me:
            return {"items": [], "total": 0}
        me_prof = db.query(UserProfilePublic).filter(UserProfilePublic.user_id == uid).first()
        me_int = db.query(UserIntention).filter(UserIntention.user_id == uid).first()
        me_life = db.query(UserLifestyle).filter(UserLifestyle.user_id == uid).first()
        me_qna = db.query(UserQna).filter(UserQna.user_id == uid, UserQna.visible == True).all()
        me_pack = self._pack(me, me_prof, me_int, me_life, me_qna, medias=[], verification=None, risk=None)

        # 社交映射
        likes_me, my_ops, liked_map = _recent_like_stats(db, uid, days=30)

        # 我与他人的关系阶段
        pair_stage_rows = db.query(UserRelationStage).filter(
            or_(UserRelationStage.user_a_id == uid, UserRelationStage.user_b_id == uid)
        ).all()
        pair_stage_map: Dict[int, UserRelationStage] = {}
        for r in pair_stage_rows:
            other_id = r.user_b_id if r.user_a_id == uid else r.user_a_id
            pair_stage_map[other_id] = r

        exclude_ids = set()
        if exclude_liked:
            liked_rows = db.query(UserLike).filter(UserLike.liker_id == uid).all()
            exclude_ids.update(r.likee_id for r in liked_rows if r.likee_id)
        if exclude_matched:
            match_rows = db.query(Match).filter(or_(Match.user_a == uid, Match.user_b == uid)).all()
            exclude_ids.update((m.user_b if m.user_a == uid else m.user_a) for m in match_rows)

        # 2) 多路召回
        pool = self._recall_candidates(db, me, limit_pool=max(3 * limit, 500))
        if not pool:
            return {"items": [], "total": 0}
        if exclude_ids:
            pool = [u for u in pool if u.id not in exclude_ids]
        if not pool:
            return {"items": [], "total": 0}

        # 3) 批量查候选侧并打分
        pool_ids = [u.id for u in pool]
        prof_map = {p.user_id: p for p in db.query(UserProfilePublic)
                    .filter(UserProfilePublic.user_id.in_(pool_ids)).all()}
        int_map = {i.user_id: i for i in db.query(UserIntention)
                   .filter(UserIntention.user_id.in_(pool_ids)).all()}
        life_map = {l.user_id: l for l in db.query(UserLifestyle)
                    .filter(UserLifestyle.user_id.in_(pool_ids)).all()}
        qna_rows = db.query(UserQna).filter(
            UserQna.user_id.in_(pool_ids), UserQna.visible == True
        ).all()
        qna_map: Dict[int, List[UserQna]] = {}
        for r in qna_rows:
            qna_map.setdefault(r.user_id, []).append(r)

        media_rows = db.query(UserMedia).filter(UserMedia.user_id.in_(pool_ids)).all()
        media_map: Dict[int, List[UserMedia]] = {}
        for m in media_rows:
            media_map.setdefault(m.user_id, []).append(m)

        ver_map = {v.user_id: v for v in db.query(UserVerification).filter(UserVerification.user_id.in_(pool_ids)).all()}
        risk_map = {r.target_id: r for r in db.query(RiskAssessment).filter(RiskAssessment.target_id.in_(pool_ids)).all()}

        scored: List[Dict[str, Any]] = []
        for u in pool:
            prof = prof_map.get(u.id)
            if prof and isinstance(prof.completion_score, int) and prof.completion_score < min_completion:
                continue

            x = self._pack(
                u, prof, int_map.get(u.id), life_map.get(u.id),
                qna_map.get(u.id), media_map.get(u.id, []),
                ver_map.get(u.id), risk_map.get(u.id)
            )
            s, detail, filtered = self._score_one(me_pack, x, likes_me, my_ops, pair_stage_map, liked_map)
            if filtered:
                continue

            scored.append({
                "_score": float(s),
                "id": x["id"], "nickname": x["nickname"], "gender": x["gender"],
                "city": x["city"], "hometown": x["hometown"],
                "age": x["age"], "height_cm": x["height_cm"],
                "avatar_url": x["avatar_url"], "tagline": x["tagline"], "bio": x["bio"],
                "completion_score": x["completion_score"],
                "kw_tokens": x["kw_tokens"],
                "signals": detail,
            })

        # 兜底
        if not scored:
            for u in pool:
                x = self._pack(
                    u, prof_map.get(u.id), int_map.get(u.id), life_map.get(u.id),
                    qna_map.get(u.id), media_map.get(u.id, []),
                    ver_map.get(u.id), risk_map.get(u.id)
                )
                s, detail, filtered = self._score_one(me_pack, x, likes_me, my_ops, pair_stage_map)
                if filtered:
                    continue
                scored.append({
                    "_score": float(s),
                    "id": x["id"], "nickname": x["nickname"], "gender": x["gender"],
                    "city": x["city"], "hometown": x["hometown"],
                    "age": x["age"], "height_cm": x["height_cm"],
                    "avatar_url": x["avatar_url"], "tagline": x["tagline"], "bio": x["bio"],
                    "completion_score": x["completion_score"],
                    "kw_tokens": x["kw_tokens"],
                    "signals": detail,
                })

        if exclude_ids:
            scored = [d for d in scored if d["id"] not in exclude_ids]
        if not scored:
            return {"items": [], "total": 0}

        # 4) 初排 -> 多样性重排（对前 page*limit 做 MMR）
        scored.sort(key=lambda d: (d["_score"], d["id"]), reverse=True)
        need_top = min(page * limit, len(scored))
        reranked_topN = self._mmr_rerank(scored, k=need_top)

        # 5) 冷启动补齐（如有）
        if len(reranked_topN) < need_top and hasattr(self, "_coldstart_fill"):
            exclude = {uid} | {x["id"] for x in reranked_topN} | set(exclude_ids)
            fill_ids = self._coldstart_fill(db, uid, exclude_ids=exclude, need=need_top - len(reranked_topN))
            if fill_ids:
                scored_map = {x["id"]: x for x in scored}
                for fid in fill_ids:
                    if fid in scored_map and scored_map[fid] not in reranked_topN:
                        reranked_topN.append(scored_map[fid])
                        if len(reranked_topN) >= need_top:
                            break

        # 6) 组装返回
        total = len(scored)
        start = (page - 1) * limit; end = start + limit
        page_items_raw = reranked_topN[start:end]

        items: List[Dict[str, Any]] = []
        for it in page_items_raw:
            reasons = it["signals"].get("reasons", [])
            items.append({
                "id": it["id"], "nickname": it["nickname"], "gender": it["gender"],
                "city": it["city"], "hometown": it["hometown"],
                "age": it["age"], "height_cm": it["height_cm"],
                "avatar_url": it["avatar_url"], "tagline": it["tagline"], "bio": it["bio"],
                "score": round(it["_score"], 4),
                "signals": {
                    "similarity": it["signals"]["similarity"],
                    "complementarity": it["signals"]["complementarity"],
                    "intention_fit": it["signals"]["intention_fit"],
                    "lifestyle": it["signals"].get("lifestyle", 0.0),
                    "trust_safety": it["signals"].get("trust_safety", 0.0),
                },
                "completion_score": it["completion_score"],
                "reason_summary": (reasons[0] if reasons else "多维度匹配度较高"),
                "reasons": reasons[:3],
            })
        # print(items,total)
        return {"items": items, "total": total}
