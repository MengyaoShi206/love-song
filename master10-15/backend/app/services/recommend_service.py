# backend/app/services/recommend_service.py
from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
import math
import re

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_, exists


from app.models.user import (
    UserAccount, UserProfilePublic, UserIntention,
    UserLifestyle, UserQna, UserBlacklist,
    UserMedia, UserLike, UserRelationStage,
)
from app.models.platform import (
    UserVerification, RiskAssessment
)


# ============== 基础工具函数 ===========
def _age_from_birth(b: Optional[date]) -> Optional[int]:
    """
    根据生日计算年龄（按“过没过今年生日”精确到年）。
    """
    if not b:
        return None
    today = date.today()
    # 若当前月份-日小于生日月份-日，则年龄需减一
    return today.year - b.year - ((today.month, today.day) < (b.month, b.day))

def _listify(x) -> List[str]:
    """
    将输入统一转为字符串列表（去空白、去空项）。
    """
    if not x:
        return []
    if isinstance(x, list):
        return [str(i).strip() for i in x if str(i).strip()]
    return [str(x).strip()]

def _norm_loc(s: Optional[str]) -> str:
    """
    地理字符串归一化：小写、去常见后缀（省/市/区/县/...），
    目前是英文格式，但是后面会进行修改。
    """
    if not s:
        return ""
    t = str(s).strip().lower()
    for suf in ["省", "市", "区", "县", "特别行政区", "自治州", "盟"]:
        t = t.replace(suf, "")
    return t

def _same_loc(a: Optional[str], b: Optional[str]) -> bool:
    """
    判断两个地理字符串是否“同地”。
    """
    return _norm_loc(a) != "" and _norm_loc(a) == _norm_loc(b)

def _gender_opposite(g: Optional[str]) -> Optional[str]:
    """
    给定性别，返回“对向性别”用于异性优先场景。
    暂时考虑异性，后面可以做成自选。
    - male/m/男 -> female
    - female/f/女 -> male
    - 其他/未知 -> None（不强制）
    """
    if not g:
        return None
    g = str(g).lower()
    if g in ("male", "m", "男"):
        return "female"
    if g in ("female", "f", "女"):
        return "male"
    return None

def _age_complement(a1: Optional[int], a2: Optional[int]) -> float:
    """
    年龄差“舒适度”评分（互补性信号之一）。
    - 绝对差越小越好；15 岁内线性衰减到 0，超过则为 0。
    """
    if a1 is None or a2 is None:
        return 0.0
    diff = abs(a1 - a2)
    return max(0.0, 1.0 - diff / 15.0)  # 15 岁作为衰减尺度

def _height_comfort(h1: Optional[int], h2: Optional[int]) -> float:
    """
    身高差“舒适度”评分（互补性信号之一）。
    - 经验：常见异性身高差的舒适中心约 12cm，容忍半宽取 20cm。
    - 以三角形函数近似，>~40cm 记为 0。
    """
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
    - 去重、小写
    这个后面再修改修改！！！
    """
    text = " ".join([f or "" for f in fields]).lower()
    toks = re.findall(r'[\u4e00-\u9fff]{2,}|[a-z0-9]{2,}', text)
    return list(set(toks))

def _jaccard(a: List[str], b: List[str]) -> float:
    """
    Jaccard 相似度：|A∩B| / |A∪B|
    """
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0

def _coalesce_enum(x: Optional[str]) -> Optional[str]:
    return str(x).strip().lower() if x else None


# ============== Lifestyle 评分 ==============
_LIKE_ENUM_FIELDS = [
    "schedule", "drinking", "smoking", "workout_freq", "diet",
    "pet_view", "spending_view", "saving_view"
]

# MBTI 粗略互补表（可按需扩展/替换）
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
    comp_norm = tuple(sorted([x.lower() for x in pair]))
    for (x, y) in _MB_TI_COMPLEMENTS:
        if tuple(sorted([x, y])) == comp_norm:
            return 0.6
    return 0.0

def _lifestyle_similarity(A: Dict[str, Any], B: Dict[str, Any]) -> Tuple[float, List[str]]:
    """
    生活方式相容度（0~1）：类别一致 + 兴趣/旅行 Jaccard + MBTI
    """
    reasons: List[str] = []
    la, lb = (A.get("lifestyle") or {}), (B.get("lifestyle") or {})
    if not la and not lb:
        return 0.0, reasons

    # 1) 枚举字段一致性
    hit = 0
    tot = 0
    for f in _LIKE_ENUM_FIELDS:
        va = _coalesce_enum(la.get(f))
        vb = _coalesce_enum(lb.get(f))
        if va is None or vb is None:
            continue
        tot += 1
        if va == vb:
            hit += 1
    enum_score = (hit / tot) if tot > 0 else 0.0
    if enum_score >= 0.6:
        reasons.append("生活方式偏好相近")

    # 2) 兴趣/旅行 Jaccard
    ja = _jaccard(_listify(la.get("interests")), _listify(lb.get("interests")))
    jt = _jaccard(_listify(la.get("travel_pref")), _listify(lb.get("travel_pref")))
    if ja >= 0.25:
        reasons.append("兴趣有交集")
    if jt >= 0.25:
        reasons.append("旅行偏好接近")

    # 3) MBTI（可选）
    mb = _mbti_score(la.get("personality"), lb.get("personality"))
    if mb >= 0.9:
        reasons.append("性格类型一致")
    elif mb >= 0.5:
        reasons.append("性格类型互补")

    # 聚合（可按需调权）
    score = 0.55 * enum_score + 0.25 * ja + 0.10 * jt + 0.10 * mb
    return max(0.0, min(1.0, score)), reasons

# ============== Like ==============
def _recent_like_stats(db: Session, uid: int, days: int = 30):
    """
    获取最近 N 天内的点赞数据：
      - likes_me: 谁喜欢我（对方 -> 我）
      - my_ops: 我喜欢谁（我 -> 对方）
      - liked_map: 每个用户最近被喜欢的次数（衡量受欢迎度）
    """
    since = datetime.utcnow() - timedelta(days=days)

    # 对方在近 N 天喜欢我
    likes_me_rows = (
        db.query(UserLike)
        .filter(UserLike.likee_id == uid, UserLike.created_at >= since)
        .all()
    )
    likes_me = {r.liker_id: (r.status or "").lower() for r in likes_me_rows}

    # 我在近 N 天喜欢了谁
    my_ops_rows = (
        db.query(UserLike)
        .filter(UserLike.liker_id == uid, UserLike.created_at >= since)
        .all()
    )
    my_ops = {r.likee_id: (r.status or "").lower() for r in my_ops_rows}

    # 最近 N 天内被喜欢次数统计（所有用户）
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
    """
    多维认证加分：每命中一项+权重，满分 ~ 1.0（通常很难满）。
    """
    if not v:
        return 0.0, []
    reasons = []
    score = 0.0
    def add(cond, pts, msg):
        nonlocal score
        if cond:
            score += pts
            reasons.append(msg)

    add(getattr(v, "id_verified", False),        0.25, "实名已认证")
    add(getattr(v, "education_verified", False), 0.15, "学历已认证")
    add(getattr(v, "income_verified", False),    0.12, "收入已认证")
    add(getattr(v, "job_verified", False),       0.10, "职业已认证")
    add(getattr(v, "house_verified", False),     0.08, "房产已认证")
    add(getattr(v, "car_verified", False),       0.05, "车辆已认证")

    return min(1.0, score), reasons

def _risk_penalty(r: Optional[RiskAssessment]) -> Tuple[float, List[str]]:
    """
    风险折扣（返回 [0,1] 的折扣系数，不是加分）：高风险 -> 折扣更小。
    """
    if not r:
        return 1.0, []
    level = (getattr(r, "risk_level", "") or "").lower()
    reasons = []
    coef = 1.0
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
    """
    媒体充足度：头像 + 相册数。
    """
    cnt = len(medias or [])
    base = 0.0
    reasons = []
    if has_avatar:
        base += 0.15
        reasons.append("有头像")
    if cnt >= 3:
        base += 0.20; reasons.append("相册丰富")
    elif cnt == 2:
        base += 0.12; reasons.append("相册较为充足")
    elif cnt == 1:
        base += 0.06; reasons.append("有相册")
    return min(0.35, base), reasons

def _like_signal(me_id: int, other_id: int, likes_me: Dict[int, str],
                 my_ops: Dict[int, str]) -> Tuple[float, List[str]]:
    """
    社交信号：
    - 对方喜欢我：+0.35
    - 我已喜欢对方：+0.10
    - 我已pass对方：-0.25
    未出现则 0。
    """
    reasons = []
    score = 0.0

    s_other = (likes_me.get(other_id) or "").lower()  # 对方 -> 我 的状态
    s_mine  = (my_ops.get(other_id)  or "").lower()   # 我   -> 对方 的状态

    # 对方喜欢我
    if s_other in ("pending", "accepted"):
        score += 0.35
        reasons.append("对方已喜欢你")

    # 我也喜欢对方（轻微加分）
    if s_mine in ("pending", "accepted"):
        score += 0.10
        reasons.append("你也对TA有好感")

    # 我拒绝过对方（降权）
    if s_mine in ("rejected",):
        score -= 0.25
        reasons.append("你曾拒绝TA")

    return max(-0.25, min(0.45, score)), reasons

def _relstage_filter_or_penalty(me_id: int, other_id: int, stage_row: Optional[UserRelationStage]) -> Tuple[bool, float, List[str]]:
    """
    只根据“我与对方”的成对关系 stage 来处理：
    - chatting/met: 轻微降权
    - exclusive/relationship/engaged/married: 直接过滤
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



# ============ 推荐主服务 =============
class RecommendService:
    """
    为您推荐（去除 UserLifestyle 依赖）的内聚服务：
    - 召回：性别 + 异地策略（city/hometown 兜底） + 活跃排序
    - 打分：相似度（文本/同城/同乡） + 互补性（性别/年龄/身高） + 双向意向
    - 重排：MMR 多样性，限制单城占比
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

    def _recall_candidates(self, db: Session, me: UserAccount, limit_pool: int = 500) -> List[UserAccount]:
        """
        候选召回（硬筛）：
        1) 过滤本人与非活跃
        2) 若可推断对向性别，则按性别过滤
        3) 若“不接受异地”，优先同城（无 city 用 hometown 兜底）
        4) 黑名单互斥（我拉黑对方 / 对方拉黑我）
        5) 按更新鲜度（updated_at）倒序取前 N
        """
        intent = db.query(UserIntention).filter(UserIntention.user_id == me.id).first()
        q = db.query(UserAccount).filter(UserAccount.is_active == True, UserAccount.id != me.id)

        # 性别过滤
        opp = _gender_opposite(me.gender)
        if opp:
            q = q.filter(func.lower(UserAccount.gender) == opp)

        # 异地策略：不接受异地 -> 同城；若无 city，用 hometown 兜底
        if intent and intent.accept_long_distance is False:
            if me.city:
                q = q.filter(UserAccount.city == me.city)
            elif me.hometown:
                q = q.filter(UserAccount.hometown == me.hometown)

        # 黑名单互斥：两条 not exists
        q = q.filter(
            ~exists().where(and_(UserBlacklist.user_id == me.id,
                                 UserBlacklist.blocked_user_id == UserAccount.id))
        ).filter(
            ~exists().where(and_(UserBlacklist.user_id == UserAccount.id,
                                 UserBlacklist.blocked_user_id == me.id))
        )

        # 活跃度近似：更新时间倒序
        return q.order_by(desc(UserAccount.updated_at)).limit(limit_pool).all()

    def _pack(self, u: UserAccount,
              prof: Optional[UserProfilePublic],
              it: Optional[UserIntention],
              life: Optional[UserLifestyle],
              qna_list: Optional[List[UserQna]],
              medias: Optional[List[UserMedia]],
              verification: Optional[UserVerification],
              risk: Optional[RiskAssessment]) -> Dict[str, Any]:
            """
            打包单个用户的“用于打分/展示的特征字典”。
            - 清洗基础属性（年龄、身高、城市/籍贯、婚育等）
            - 从文案（tagline/bio）提取关键词 tokens
            - 打包意向字段（年龄/身高区间、异地/城市、婚恋时间线/生育计划等）
            - 生活方式 + QnA tokens

            ！！！！！！！！！！！！！！！！！！！！
            """
            tagline = (prof.tagline if prof else "") or ""
            bio = (prof.bio if prof else "") or ""
            # 把 QnA 文本加入 tokens
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

    def _intention_fit(self, A: Dict[str, Any], B: Dict[str, Any]) -> Tuple[float, List[str]]:
        """
        双向意向契合评分（我对你 + 你对我），尽量让意向的每个字段都参与。
        规则：
            - 年龄区间：A 偏好里是否接受 B 的年龄；反之亦然
            - 身高区间：同上
            - 城市/异地：若不接受异地 -> 同城或同乡；否则偏好城市命中加分
            - 婚育观：A 不接受离异/带娃 -> 若 B 为离异/带娃则扣分
            - 婚恋时间线/生育计划：一致性加分
        """
        reasons: List[str] = []
        aint, bint = A["intent"] or {}, B["intent"] or {}
        score = 0.0

        # 年龄区间（双向）
        def _age_ok(target: Dict[str, Any], pref: Dict[str, Any]) -> bool:
            pa_min, pa_max = pref.get("preferred_age_min"), pref.get("preferred_age_max")
            return (target.get("age") is not None and pa_min is not None and pa_max is not None
                    and pa_min <= target["age"] <= pa_max)

        if _age_ok(B, aint):
            score += 0.35; reasons.append("对方年龄在你的偏好内")
        if _age_ok(A, bint):
            score += 0.20

        # 身高区间（双向）
        def _height_ok(target: Dict[str, Any], pref: Dict[str, Any]) -> bool:
            ph_min, ph_max = pref.get("preferred_height_min"), pref.get("preferred_height_max")
            return (target.get("height_cm") and ph_min is not None and ph_max is not None
                    and ph_min <= target["height_cm"] <= ph_max)

        if _height_ok(B, aint):
            score += 0.15; reasons.append("身高合你偏好")
        if _height_ok(A, bint):
            score += 0.10

        # 城市/异地（双向）
        def _city_fit(me: Dict[str, Any], other: Dict[str, Any], pref: Dict[str, Any]) -> bool:
            accept_ld = pref.get("accept_long_distance")
            pref_cities = set(pref.get("preferred_cities") or [])
            if accept_ld is False:
                # 不接受异地：同城或同乡即可
                return bool(me.get("city") and other.get("city") and me["city"] == other["city"]) or \
                        bool(_same_loc(me.get("hometown"), other.get("hometown")))
            # 接受异地：若设置了偏好城市，则命中城市/籍贯即满足；未设置则不限制
            if pref_cities:
                return (other.get("city") in pref_cities) or (other.get("hometown") in pref_cities)
            return True

        if _city_fit(A, B, aint):
            score += 0.10
            if A.get("city") and B.get("city") and A["city"] == B["city"]:
                reasons.append("同城匹配你的偏好")
            elif _same_loc(A.get("hometown"), B.get("hometown")):
                reasons.append("籍贯相近更有共鸣")
        if _city_fit(B, A, bint):
            score += 0.05

        # 婚育观（单/双向扣分）
        acc_div = aint.get("accept_divorce")
        if acc_div is False and str(B.get("marital_status") or "").lower() == "divorced":
            score -= 0.15; reasons.append("你不接受离异（扣分）")
        acc_child = aint.get("accept_children")
        if acc_child is False and bool(B.get("has_children")):
            score -= 0.15; reasons.append("你不接受带娃（扣分）")

        # 计划与时间线（双向加分）
        if aint.get("marriage_timeline") and bint.get("marriage_timeline") \
            and aint["marriage_timeline"] == bint["marriage_timeline"]:
            score += 0.07; reasons.append("婚恋时间线一致")
        if aint.get("child_plan") and bint.get("child_plan") \
            and aint["child_plan"] == bint["child_plan"]:
            score += 0.08; reasons.append("生育计划一致")

        # 归一化到 [0, 1]（防御式截断）
        score = max(0.0, min(1.0, score))
        return score, reasons

    def _score_one(
        self,
        me: Dict[str, Any],
        other: Dict[str, Any],
        likes_me: Optional[Dict[int, str]] = None,
        my_ops: Optional[Dict[int, str]] = None,
        pair_stage_map: Optional[Dict[int, "UserRelationStage"]] = None,
        liked_map: Optional[Dict[int, int]] = None,
    ) -> Tuple[float, Dict[str, Any], bool]:
        """
        单候选样本打分：
        - 相似度：文本关键词相似 + 同城 + 同乡
        - 互补性：性别互补 + 年龄差舒适 + 身高差舒适
        - 意向契合：双向

        ！！！！！！！！！！！！！！
        """
        likes_me = likes_me or {}
        my_ops = my_ops or {}
        pair_stage_map = pair_stage_map or {}

        reasons: List[str] = []

        # 1) 关系阶段过滤/降权
        stage_row = pair_stage_map.get(other["id"])
        should_filter = False
        rel_penalty = 0.0
        if stage_row is not None:
            should_filter, rel_penalty, rel_reasons = _relstage_filter_or_penalty(
                me_id=me["id"], other_id=other["id"], stage_row=stage_row
            )
            if should_filter:
                return 0.0, {"reasons": rel_reasons}, True
            reasons.extend(rel_reasons)
        
        # 2) 相似度信号
        sim_kw = _jaccard(me.get("kw_tokens", []), other.get("kw_tokens", []))
        if sim_kw >= 0.25:
            reasons.append(f"资料关键词相近 {int(sim_kw*100)}%")
        sim_city = 1.0 if me.get("city") and me["city"] == other.get("city") else 0.0
        if sim_city == 1.0:
            reasons.append("同城更易线下见面")
        sim_home = 1.0 if _same_loc(me.get("hometown"), other.get("hometown")) else 0.0
        if sim_home == 1.0 and sim_city == 0.0:
            reasons.append("同乡更有话题")
        sim_score = 0.55 * sim_kw + 0.25 * sim_city + 0.20 * sim_home


        # 3) 互补性信号
        comp_gender = 1.0 if (_gender_opposite(me.get("gender")) == str(other.get("gender")).lower()
                                or _gender_opposite(other.get("gender")) == str(me.get("gender")).lower()) else 0.5
        comp_age = _age_complement(me.get("age"), other.get("age"))
        comp_height = _height_comfort(me.get("height_cm"), other.get("height_cm"))

        if comp_gender >= 0.9:
            reasons.append("性别互补")
        if comp_age >= 0.6:
            reasons.append("年龄差舒适")
        if comp_height >= 0.6:
            reasons.append("身高差舒适")

        comp_score = 0.34 * comp_gender + 0.33 * comp_age + 0.33 * comp_height

        # 4) 双向意向契合
        intent_score, intent_reasons = self._intention_fit(me, other)
        reasons.extend(intent_reasons)

        # 5) 生活方式相容度
        life_score, life_reasons = _lifestyle_similarity(me, other)
        reasons.extend(life_reasons)

        # 6) 可信与安全（认证/风险/媒体/社交）
        ver_score, ver_reasons = _verification_score(other.get("_verification"))
        risk_coef, risk_reasons = _risk_penalty(other.get("_risk"))
        med_score, med_reasons = _media_score(other.get("_media_list", []), other.get("_has_avatar", False))
        like_score, like_reasons = _like_signal(me["id"], other["id"], likes_me, my_ops)

        trust_raw = 0.55 * ver_score + 0.25 * med_score + 0.20 * max(0.0, like_score)
        trust_safety = max(0.0, min(1.0, trust_raw)) * risk_coef  # 风险以折扣形式作用

        reasons.extend(ver_reasons + med_reasons + like_reasons + risk_reasons)

        # 总分融合
        total = (self.w["similarity"] * sim_score +
                self.w["complementarity"] * comp_score +
                self.w["intention"] * intent_score +
                self.w["lifestyle"] * life_score +
                self.w["trust_safety"]    * trust_safety +
                rel_penalty
            )
        
        # 7) 受欢迎度微加成（基于最近30天被喜欢次数）
        if liked_map is not None:
            popularity = math.log1p(liked_map.get(other["id"], 0)) / 5.0  # 0~0.3
            total += 0.05 * min(1.0, popularity)

        detail = {
            "similarity": round(sim_score, 4),
            "complementarity": round(comp_score, 4),
            "intention_fit": round(intent_score, 4),
            "lifestyle": round(life_score, 4),
            "trust_safety": round(trust_safety, 4),
            "reasons": reasons[:4],  # 仅取前几条用于展示
        }
        return float(total), detail, False

    def _mmr_rerank(self, items: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
        """
        多样性重排（MMR）：
        - 用“文本关键词相似 + 地域相似”近似项间相似度
        - 限制单一城市的占比（≤ 50%），避免同城刷屏
        """
        if not items:
            return []

        def pair_sim(a, b) -> float:
            # 关键词 Jaccard + 地域（同城/同乡各占 50%）
            s_kw = _jaccard(a.get("kw_tokens", []), b.get("kw_tokens", []))
            s_loc = 0.5 * (1.0 if a.get("city") and a["city"] == b.get("city") else 0.0) + \
                    0.5 * (1.0 if _same_loc(a.get("hometown"), b.get("hometown")) else 0.0)
            return float(max(0.0, min(1.0, 0.7 * s_kw + 0.3 * s_loc)))

        selected: List[Dict[str, Any]] = []
        pool = items[:]  # 拷贝
        city_cnt: Dict[str, int] = {}

        total = min(k, len(pool))
        city_limit = max(2, int(total * 0.5))  # 单城上限 50%

        while pool and len(selected) < k:
            best_idx, best_val = 0, -1e9
            # 仅在头部窗口中做 MMR 以控算力
            for i, c in enumerate(pool[:80]):
                city = (c.get("city") or "").strip()
                # 城市占比控制
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

    def recommend_for_user(self, db: Session, uid: int, limit: int = 20, page: int = 1, min_completion: int = 30) -> Dict[str, Any]:
        """
        主流程：
            1) 读我方资料/意向/生活方式/QnA
            2) 候选召回（含黑名单互斥）
            3) 批量查询候选的 profile/intention/lifestyle/qna 并逐个打分
            4) 初排 -> MMR 多样性重排
            5) 冷启动补齐
        """
        # 安全边界
        limit = max(1, min(int(limit or 20), 100))   # 每页 1~100
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

        # 预取“社交”映射：谁喜欢我、我对谁操作过
        likes_me, my_ops, liked_map = _recent_like_stats(db, uid, days=30)

        # 我与他人的关系阶段（若表结构不同可改为 pair 表或用两个方向查询）
        pair_stage_rows = db.query(UserRelationStage).filter(
            or_(UserRelationStage.user_a_id == uid, UserRelationStage.user_b_id == uid)
        ).all()

        pair_stage_map: Dict[int, UserRelationStage] = {}
        for r in pair_stage_rows:
            other_id = r.user_b_id if r.user_a_id == uid else r.user_a_id
            pair_stage_map[other_id] = r


        # 2) 候选召回
        pool = self._recall_candidates(db, me, limit_pool=max(3 * limit, 500))
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

        # 每个用户的媒体（仅计数/存在性用于评分，不在返回中泄露）
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
                "id": x["id"],
                "nickname": x["nickname"],
                "gender": x["gender"],
                "city": x["city"],
                "hometown": x["hometown"],
                "age": x["age"],
                "height_cm": x["height_cm"],
                "avatar_url": x["avatar_url"],
                "tagline": x["tagline"],
                "bio": x["bio"],
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
                    "id": x["id"],
                    "nickname": x["nickname"],
                    "gender": x["gender"],
                    "city": x["city"],
                    "hometown": x["hometown"],
                    "age": x["age"],
                    "height_cm": x["height_cm"],
                    "avatar_url": x["avatar_url"],
                    "tagline": x["tagline"],
                    "bio": x["bio"],
                    "completion_score": x["completion_score"],
                    "kw_tokens": x["kw_tokens"],
                    "signals": detail,
                })

        # 4) 初排 -> 多样性重排（保持你上一版实现）
        scored.sort(key=lambda d: d["_score"], reverse=True)
        # 这一步很关键：为了保证第 N 页仍然是全局多样性后的顺序，
        # 我们用 MMR 先取到前 page*limit 个，再分页切片
        need_top = min(page * limit, len(scored))
        reranked_topN = self._mmr_rerank(scored, k=need_top)

        # 5) 冷启动补齐（若你有 _coldstart_fill）
        if len(reranked_topN) < need_top and hasattr(self, "_coldstart_fill"):
            exclude = {uid} | {x["id"] for x in reranked_topN}
            fill_ids = self._coldstart_fill(db, uid, exclude_ids=exclude, need=need_top - len(reranked_topN))
            if fill_ids:
                scored_map = {x["id"]: x for x in scored}
                for fid in fill_ids:
                    if fid in scored_map and scored_map[fid] not in reranked_topN:
                        reranked_topN.append(scored_map[fid])
                        if len(reranked_topN) >= need_top:
                            break
                        
        # 6) 组装返回
        total = len(scored)  # 或 len(reranked_topN) 也行，这里代表可分页总量
        start = (page - 1) * limit
        end = start + limit
        page_items_raw = reranked_topN[start:end]


        items: List[Dict[str, Any]] = []
        for it in page_items_raw:
            reasons = it["signals"].get("reasons", [])
            items.append({
                "id": it["id"],
                "nickname": it["nickname"],
                "gender": it["gender"],
                "city": it["city"],
                "hometown": it["hometown"],
                "age": it["age"],
                "height_cm": it["height_cm"],
                "avatar_url": it["avatar_url"],
                "tagline": it["tagline"],
                "bio": it["bio"],
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
        return {"items": items, "total": total}