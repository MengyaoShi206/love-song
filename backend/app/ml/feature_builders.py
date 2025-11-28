# backend/ml/feature_builders.py
from __future__ import annotations
from typing import Dict, Any, List, Optional
import math
import re
from datetime import date

# --- 一些小工具 ---
def _to_float(x, default: float = 0.0) -> float:
    if x is None:
        return default
    try:
        # 直接转 float，支持 int/float/Decimal/str 等
        return float(x)
    except Exception:
        return default
    
def _age_from_birth(b: Optional[date]) -> Optional[int]:
    if not b: return None
    today = date.today()
    return today.year - b.year - ((today.month, today.day) < (b.month, b.day))

def _norm_loc(s: Optional[str]) -> str:
    if not s: return ""
    t = str(s).strip().lower()
    for suf in ["省","市","区","县","特别行政区","自治州","盟"]:
        t = t.replace(suf, "")
    return t

def _same_loc(a: Optional[str], b: Optional[str]) -> bool:
    return _norm_loc(a) != "" and _norm_loc(a) == _norm_loc(b)

def _listify(x) -> List[str]:
    if not x: return []
    if isinstance(x, list): return [str(i).strip().lower() for i in x if str(i).strip()]
    return [str(x).strip().lower()]

def _jaccard(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb: return 0.0
    inter = len(sa & sb); union = len(sa | sb)
    return inter / union if union else 0.0

def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    return a / b if b not in (0, None) else default

# --- 核心：从“我方 + 候选”的 ORM 打包成“成对特征” ---
def build_pair_features(
    me: Dict[str, Any],
    other: Dict[str, Any],
) -> Dict[str, float]:
    """
    输入：recommend_service._pack 之后的 me_pack / other_pack 字典
    输出：一行“成对特征”用于 ML 排序
    注意：全部转为 float，便于统一标准化/喂给 DNN
    """
    # --- 基础，全部先转 float ---
    age_me = _to_float(me.get("age"))
    age_ot = _to_float(other.get("age"))
    h_me   = _to_float(me.get("height_cm"))
    h_ot   = _to_float(other.get("height_cm"))
    w_me   = _to_float(me.get("weight_kg"))
    w_ot   = _to_float(other.get("weight_kg"))

    # BMI —— 统一 float 后再算
    def _bmi(h, w):
        h = _to_float(h); w = _to_float(w)
        return (w / ((h/100.0)**2)) if (h > 0 and w > 0) else 0.0
    bmi_me = _bmi(h_me, w_me)
    bmi_ot = _bmi(h_ot, w_ot)

    # 城市/籍贯
    same_city = 1.0 if (me.get("city") and other.get("city") and me["city"] == other["city"]) else 0.0
    same_home = 1.0 if _same_loc(me.get("hometown"), other.get("hometown")) else 0.0

    # 关键词/兴趣相似度
    kw_me = me.get("kw_tokens") or []
    kw_ot = other.get("kw_tokens") or []
    kw_sim = _jaccard(kw_me, kw_ot)

    life_me = me.get("lifestyle") or {}
    life_ot = other.get("lifestyle") or {}
    int_sim = _jaccard(_listify(life_me.get("interests")), _listify(life_ot.get("interests")))
    travel_sim = _jaccard(_listify(life_me.get("travel_pref")), _listify(life_ot.get("travel_pref")))

    # 生活方式枚举一致数
    enum_fields = ["schedule","drinking","smoking","workout_freq","diet","pet_view","spending_view","saving_view"]
    enum_hit, enum_tot = 0, 0
    for f in enum_fields:
        va, vb = life_me.get(f), life_ot.get(f)
        if va is None or vb is None:
            continue
        enum_tot += 1
        if str(va).strip().lower() == str(vb).strip().lower():
            enum_hit += 1
    enum_ratio = (enum_hit / enum_tot) if enum_tot else 0.0

    # 意向（双向年龄/身高是否在对方偏好内）
    def _age_ok(target_age, pref_min, pref_max):
        ta = _to_float(target_age, None)
        pmin = _to_float(pref_min, None)
        pmax = _to_float(pref_max, None)
        if ta is None or pmin is None or pmax is None: return 0.0
        return 1.0 if (pmin <= ta <= pmax) else 0.0
    def _h_ok(target_h, ph_min, ph_max):
        th = _to_float(target_h, None)
        pmin = _to_float(ph_min, None)
        pmax = _to_float(ph_max, None)
        if th is None or pmin is None or pmax is None: return 0.0
        return 1.0 if (pmin <= th <= pmax) else 0.0

    aint = me.get("intent") or {}
    bint = other.get("intent") or {}
    age_in_me_pref = _age_ok(age_ot, aint.get("preferred_age_min"), aint.get("preferred_age_max"))
    age_in_ot_pref = _age_ok(age_me, bint.get("preferred_age_min"), bint.get("preferred_age_max"))
    h_in_me_pref   = _h_ok(h_ot, aint.get("preferred_height_min"), aint.get("preferred_height_max"))
    h_in_ot_pref   = _h_ok(h_me, bint.get("preferred_height_min"), bint.get("preferred_height_max"))

    # 完成度、头像
    comp_me = _to_float(me.get("completion_score")) / 100.0
    comp_ot = _to_float(other.get("completion_score")) / 100.0
    has_avatar_ot = 1.0 if other.get("avatar_url") else 0.0

    feats = {
        "age_diff": abs(age_me - age_ot),
        "height_diff": abs(h_me - h_ot),
        "bmi_diff": abs(bmi_me - bmi_ot),

        "same_city": same_city,
        "same_hometown": 1.0 if (same_home and same_city == 0.0) else 0.0,

        "kw_sim": float(kw_sim),
        "interest_sim": float(int_sim),
        "travel_sim": float(travel_sim),
        "lifestyle_enum_ratio": float(enum_ratio),

        "age_in_me_pref": age_in_me_pref,
        "age_in_ot_pref": age_in_ot_pref,
        "h_in_me_pref": h_in_me_pref,
        "h_in_ot_pref": h_in_ot_pref,

        "completion_me": float(comp_me),
        "completion_ot": float(comp_ot),
        "has_avatar_ot": float(has_avatar_ot),
    }

    # 1) 有符号差 & 年龄差高斯核（按性别设定期望差）
    feats["age_gap_signed"] = age_me - age_ot
    feats["height_gap_signed"] = h_me - h_ot
    g_me = (me.get("gender") or "").strip().lower()
    mu = 4.0 if g_me in ("male","m","男") else (-4.0 if g_me in ("female","f","女") else 0.0)
    sigma = 2.5
    feats["age_gap_gauss"] = math.exp(-0.5 * ((feats["age_gap_signed"] - mu) / sigma) ** 2)

    # 2) 生活方式逐项一致（8 个）
    for f in enum_fields:
        fa = life_me.get(f); fb = life_ot.get(f)
        feats[f"life_eq_{f}"] = 1.0 if (fa is not None and fb is not None and str(fa).strip().lower()==str(fb).strip().lower()) else 0.0

    # 3) MBTI 一致/互补
    def _mbti_score(a, b):
        if not a or not b: return 0.0
        a = a.strip().lower(); b = b.strip().lower()
        if a == b: return 1.0
        complements = {tuple(sorted(p)) for p in [("intj","enfp"),("entp","isfj"),("istp","enfj"),("infj","entp"),("enfj","istp"),("enfp","intj")]}
        return 0.6 if tuple(sorted((a,b))) in complements else 0.0
    feats["mbti_match"] = _mbti_score(life_me.get("personality"), life_ot.get("personality"))

    # 4) 偏好区间重叠度
    def _interval_overlap(a_min, a_max, b_min, b_max, norm=1.0):
        if None in (a_min, a_max, b_min, b_max): return 0.0
        L = max(0.0, min(_to_float(a_max), _to_float(b_max)) - max(_to_float(a_min), _to_float(b_min)))
        return min(1.0, max(0.0, L / norm))
    feats["pref_age_overlap"] = _interval_overlap(
        aint.get("preferred_age_min"), aint.get("preferred_age_max"),
        bint.get("preferred_age_min"), bint.get("preferred_age_max"),
        norm=30.0
    )
    feats["pref_height_overlap"] = _interval_overlap(
        aint.get("preferred_height_min"), aint.get("preferred_height_max"),
        bint.get("preferred_height_min"), bint.get("preferred_height_max"),
        norm=30.0
    )

    # 5) 城市偏好/异地兼容
    pref_cities_me = set(aint.get("preferred_cities") or [])
    pref_cities_ot = set(bint.get("preferred_cities") or [])
    feats["other_city_in_me_pref"] = 1.0 if (other.get("city") in pref_cities_me or other.get("hometown") in pref_cities_me) else 0.0
    feats["me_city_in_other_pref"] = 1.0 if (me.get("city") in pref_cities_ot or me.get("hometown") in pref_cities_ot) else 0.0
    accept_ld_me = aint.get("accept_long_distance")
    feats["accept_ld_compat"] = 1.0 if (accept_ld_me is not False or (me.get("city") and other.get("city") and me["city"]==other["city"])) else 0.0

    # 6) 婚育观一致
    feats["timeline_equal"] = 1.0 if (aint.get("marriage_timeline") and aint.get("marriage_timeline")==bint.get("marriage_timeline")) else 0.0
    feats["child_plan_equal"] = 1.0 if (aint.get("child_plan") and aint.get("child_plan")==bint.get("child_plan")) else 0.0

    # 7) 现实约束兼容（离异/带娃）
    marital_ot = (other.get("marital_status") or "").strip().lower()
    feats["divorce_acceptable_compat"] = 1.0 if (aint.get("accept_divorce") is not False or marital_ot != "divorced") else 0.0
    feats["children_acceptable_compat"] = 1.0 if (aint.get("accept_children") is not False or not other.get("has_children")) else 0.0

    # 8) 资料侧增强
    feats["completion_gap"] = abs(comp_me - comp_ot)
    feats["has_avatar_me"] = 1.0 if me.get("avatar_url") else 0.0

    # 统一转 float
    return {k: float(v) for k, v in feats.items()}