# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json
from typing import Dict, Any, List, Tuple, Optional

import numpy as np

def _to_bool(x) -> bool:
    s = str(x or "").strip().lower()
    return s in ("1", "true", "y", "yes", "on")

ML_DEBUG = _to_bool(os.getenv("ML_DEBUG", "0"))
CALIB_MODE = os.getenv("ML_CALIB", "auto").strip().lower()  # auto|platt|iso|pct|none

# ========== 第三方依赖（做可选导入，便于环境不完整时退化运行） ==========
try:
    from xgboost import XGBClassifier
    _HAS_XGB = True
except Exception:
    _HAS_XGB = False

try:
    from sklearn.neural_network import MLPClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    from sklearn.metrics import roc_auc_score, log_loss
    from sklearn.model_selection import GroupShuffleSplit
    from sklearn.linear_model import LogisticRegression
    from sklearn.isotonic import IsotonicRegression
    import joblib
    _HAS_SK = True
except Exception:
    _HAS_SK = False

# ========== 轻量工具：与 recommend_service 口径一致 ==========
def _jaccard(a, b):
    sa, sb = set(a or []), set(b or [])
    if not sa and not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0

def _same_loc(h1, h2):
    s1 = str(h1 or "").strip().lower()
    s2 = str(h2 or "").strip().lower()
    return bool(s1 and s2 and s1 == s2)

def _norm_gender(g):
    g = (str(g or "").strip().lower())
    if g in ("m", "male", "man"): return "male"
    if g in ("f", "female", "woman"): return "female"
    return ""

def _gender_opposite(g):
    g = _norm_gender(g)
    return "female" if g == "male" else ("male" if g == "female" else "")

def _age_complement(a1, a2):
    """年龄差舒适度：|Δ|<15 线性衰减"""
    if a1 is None or a2 is None:
        return 0.0
    try:
        diff = abs(float(a1) - float(a2))
    except Exception:
        return 0.0
    return max(0.0, 1.0 - diff / 15.0)

def _height_comfort(h1, h2):
    try:
        diff = abs(float(h1) - float(h2))
    except Exception:
        return 0.0
    center, width = 12.0, 20.0
    score = 1.0 - abs(diff - center) / width
    return max(0.0, min(1.0, score))

def _verification_score(v):
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
    return min(1.0, score), []

def _risk_penalty(r):
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
    return coef, []

def _media_score(medias, has_avatar):
    cnt = len(medias or []); base = 0.0
    if has_avatar: base += 0.15
    if cnt >= 3: base += 0.20
    elif cnt == 2: base += 0.12
    elif cnt == 1: base += 0.06
    return min(0.35, base), []

def _like_signal(uid, oid, likes_me, my_ops):  # 训练/离线不计实时 like
    return 0.0, []

def _coalesce_enum(x: Optional[str]) -> Optional[str]:
    return str(x).strip().lower() if x else None

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

def _listify(x) -> List[str]:
    if not x: return []
    if isinstance(x, list):
        return [str(i).strip() for i in x if str(i).strip()]
    return [str(x).strip()]

def _lifestyle_similarity(A: Dict[str, Any], B: Dict[str, Any]) -> Tuple[float, List[str]]:
    reasons: List[str] = []
    la, lb = (A.get("lifestyle") or {}), (B.get("lifestyle") or {})
    if not la and not lb:
        return 0.0, reasons
    # 1) 枚举一致
    hit = 0; tot = 0
    for f in _LIKE_ENUM_FIELDS:
        va = _coalesce_enum(la.get(f)); vb = _coalesce_enum(lb.get(f))
        if va is None or vb is None: continue
        tot += 1
        if va == vb: hit += 1
    enum_score = (hit / tot) if tot > 0 else 0.0
    if enum_score >= 0.6: reasons.append("生活方式偏好相近")
    # 2) 兴趣/旅行 Jaccard
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

# ========== 模型与特征 ==========
MODEL_DIR = os.getenv("ML_MODEL_DIR", "data/models")
XGB_PATH  = os.path.join(MODEL_DIR, "xgb_ranker.json")
DNN_PATH  = os.path.join(MODEL_DIR, "dnn_ranker.pkl")
META_PATH = os.path.join(MODEL_DIR, "hybrid_meta.json")
ISO_PATH  = os.path.join(MODEL_DIR, "iso_calib.pkl")

FEATURES_MAIN = [
    # 五大主维度
    "similarity", "complementarity", "intention_fit", "lifestyle", "trust_safety",
    # 相似度细分
    "sim_kw", "sim_city", "sim_home",
    # 互补性细分
    "comp_gender", "comp_age", "comp_height",
    # 可信安全构成
    "ver_score", "med_score", "like_score", "risk_coef",
    # 衍生/交叉
    "age_diff_abs", "height_diff_abs",
    "sim_kw_x_life", "intent_x_trust", "comp_x_trust",
]

def _safe_float(x, default=0.0):
    try:
        if x is None: return float(default)
        return float(x)
    except Exception:
        return float(default)

# ========== 主类 ==========
class HybridXgbDnnRanker:
    """
    两阶段：
    1) XGB 做特征选择（重要性），仅用于选子集；
    2) DNN(MLP) 在子集上训练，输出概率；再做概率校准（Platt/Isotonic/pct）。
    """
    def __init__(self, load_existing: bool = True):
        self.xgb = None
        self.dnn = None
        self.selected_feats = []
        self.expected_dim = None
        self.calib = None
        self.iso = None
        self.last_error = None
        if load_existing:          # ★ 允许不加载旧模型（用于CV每折训练）
            self._load_if_exists()

    # ----- 外部可用性 -----
    def available(self) -> bool:
        return self.dnn is not None

    # ----- 概率校准 -----
    @staticmethod
    def _sigmoid(z: float) -> float:
        return float(1.0 / (1.0 + np.exp(-z)))

    def _apply_calib(self, p: float) -> float:
        """训练用原始 p，应用也用原始 p。"""
        if not self.calib:
            return p
        kind, a, b = self.calib
        if kind == "platt":
            z = a * p + b
            return self._sigmoid(z)
        if kind == "pct":
            p5, p95 = a, b
            if p95 <= p5: return p
            return float(np.clip((p - p5) / (p95 - p5), 0.0, 1.0))
        if kind == "iso":
            # a 是 ISO_PATH
            if self.iso is None:
                try:
                    self.iso = joblib.load(ISO_PATH)
                except Exception:
                    return p
            try:
                return float(self.iso.predict([p])[0])
            except Exception:
                return p
        return p

    # ----- 预测 -----
    def predict_pair(self, me: Dict[str, Any], other: Dict[str, Any]) -> float:
        if not self.available():
            self.last_error = self.last_error or "not_available"
            return 0.0
        try:
            x = self._extract_features(me, other, return_names=False)
            exp = self.expected_dim or (len(self.selected_feats) if self.selected_feats else len(FEATURES_MAIN))
            if x.shape[-1] != exp:
                self.last_error = f"predict_dim_mismatch: got={x.shape[-1]} expect={exp}"
                if ML_DEBUG:
                    print("[ml_ranker] dim mismatch:", x.shape[-1], "vs", exp,
                          "selected_feats_len=", len(self.selected_feats))
                return 0.0
            p = self.dnn.predict_proba(x.reshape(1, -1))[0, 1]
            p = float(np.clip(p, 0.0, 1.0))
            p = self._apply_calib(p)
            return float(np.clip(p, 0.0, 1.0))
        except Exception as e:
            self.last_error = f"predict_error: {e!r}"
            if ML_DEBUG:
                print("[ml_ranker] predict_error:", repr(e))
            return 0.0

    # ----- 训练入口 -----
    def fit(self,
            samples: List[Tuple[Dict[str, Any], Dict[str, Any], int]],
            xgb_top_k: int = 16,
            dnn_hidden=(64, 32),
            random_state: int = 42,
            split_mode: str = "by_me",  # "by_me" 或 "user_disjoint"
            save_model: bool = True,       # ★ 新增：是否落盘
            calibrate: bool = True         # ★ 新增：是否在fit内做标定
            ) -> Dict[str, Any]:

        assert _HAS_SK, "scikit-learn 未安装"
        os.makedirs(MODEL_DIR, exist_ok=True)

        # 1) 构造特征矩阵
        X_full, y = self._build_matrix(samples)
        feat_names = FEATURES_MAIN[:]

        # 2) 先做“零方差过滤”，再做 Pearson 去共线，并把 NaN/Inf 兜底
        keep_var = self._variance_filter(X_full, eps=1e-8)
        X_var = X_full[:, keep_var]
        feat_names_var = [feat_names[i] for i in keep_var]

        corr = np.corrcoef(X_var, rowvar=False)
        corr = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0)

        keep = []
        banned = set()
        for i in range(corr.shape[0]):
            if i in banned:
                continue
            keep.append(i)
            for j in range(i + 1, corr.shape[0]):
                if abs(corr[i, j]) >= 0.92:
                    banned.add(j)

        X = X_var[:, keep]
        feat_names = [feat_names_var[i] for i in keep]

        # 3) XGB 重要性选子集（若无 xgboost，则全量）
        if _HAS_XGB:
            self.xgb = XGBClassifier(
                n_estimators=120, max_depth=4, learning_rate=0.08,
                subsample=0.9, colsample_bytree=0.9, reg_lambda=1.0,
                objective="binary:logistic", n_jobs=4, random_state=random_state
            )
            self.xgb.fit(X, y)
            importances = self.xgb.feature_importances_
            idx_sorted = np.argsort(importances)[::-1]
            sel_idx = idx_sorted[:min(xgb_top_k, X.shape[1])]
            X = X[:, sel_idx]
            self.selected_feats = [feat_names[i] for i in sel_idx]
            try:
                if hasattr(self.xgb, "save_model"):
                    self.xgb.save_model(XGB_PATH)
            except Exception:
                pass
        else:
            self.selected_feats = feat_names

        self.expected_dim = len(self.selected_feats)

        # 4) 分组切分（避免同一用户泄漏到训练与验证）
        X_tr, X_val, y_tr, y_val = self._split_train_val(
            samples, X, y, test_size=0.15, mode=split_mode, random_state=random_state
        )

        # 类平衡 sample_weight
        pos_ratio = float((y_tr == 1).mean()) if len(y_tr) else 0.5
        w_pos = 0.5 / max(pos_ratio, 1e-6)
        w_neg = 0.5 / max(1.0 - pos_ratio, 1e-6)
        sw_tr = np.where(y_tr == 1, w_pos, w_neg).astype(np.float32)

        # 5) DNN / LR 训练（新增：dnn_hidden 为 (0,) 或空时走 LR）
        use_lr = (len(dnn_hidden) == 0) or (len(dnn_hidden) == 1 and dnn_hidden[0] == 0)

        if use_lr:
            base_clf = LogisticRegression(
                penalty="l2", C=0.9, solver="liblinear",
                max_iter=1000, random_state=random_state
            )
        else:
            base_clf = MLPClassifier(
                hidden_layer_sizes=dnn_hidden,
                activation="relu",
                solver="adam",
                # ★ 更强正则 + 更小初始学习率 + 自适应学习率
                alpha=1e-2,
                batch_size=128,
                learning_rate="adaptive",
                learning_rate_init=5e-3,
                max_iter=300,
                random_state=random_state,
                verbose=False
            )

        self.dnn = Pipeline([
            ("scaler", StandardScaler(with_mean=True, with_std=True)),
            ("mlp", base_clf)  # 名字仍叫 mlp，下面的 mlp__sample_weight 可复用
        ])
        self.dnn.fit(X_tr, y_tr, mlp__sample_weight=sw_tr)

        # 6) 训练内评估
        p_tr  = self.dnn.predict_proba(X_tr)[:, 1]
        p_val = self.dnn.predict_proba(X_val)[:, 1]
        try:
            auc_tr  = roc_auc_score(y_tr,  p_tr)
            auc_val = roc_auc_score(y_val, p_val)
        except Exception:
            auc_tr = auc_val = None

        # 7) 概率校准（auto: 先试 platt，若无改善试 iso；仍无则 pct 或 none）
        self.calib = None
        self.iso = None

        def _try_platt() -> Tuple[bool, float, float]:
            try:
                lr = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000, class_weight="balanced")
                lr.fit(p_val.reshape(-1, 1), y_val)
                a = float(lr.coef_[0, 0]); b = float(lr.intercept_[0])
                p_before = p_val
                ll_before = log_loss(y_val, p_before, labels=[0, 1])
                p_after  = 1.0 / (1.0 + np.exp(-(a * p_before + b)))
                ll_after = log_loss(y_val, p_after, labels=[0, 1])
                if ML_DEBUG:
                    print(f"[ml_ranker] platt calib: logloss {ll_before:.5f} -> {ll_after:.5f}, a={a:.4f}, b={b:.4f}")
                improved = (ll_after + 1e-4 < ll_before) and (abs(a) >= 0.5)
                if improved:
                    self.calib = ("platt", a, b)
                return improved, ll_before, ll_after
            except Exception as e:
                if ML_DEBUG:
                    print("[ml_ranker] platt failed:", repr(e))
                return False, float("inf"), float("inf")

        def _try_iso() -> Tuple[bool, float, float]:
            try:
                iso = IsotonicRegression(out_of_bounds="clip")
                iso.fit(p_val, y_val)
                p_before = p_val
                ll_before = log_loss(y_val, p_before, labels=[0, 1])
                p_after  = iso.predict(p_before)
                ll_after = log_loss(y_val, p_after, labels=[0, 1])
                if ML_DEBUG:
                    print(f"[ml_ranker] iso calib:   logloss {ll_before:.5f} -> {ll_after:.5f}")
                improved = (ll_after + 1e-4 < ll_before)
                if improved:
                    self.iso = iso
                    try:
                        joblib.dump(self.iso, ISO_PATH)
                    except Exception:
                        pass
                    # 以路径占位写进 meta
                    self.calib = ("iso", float("nan"), float("nan"))
                return improved, ll_before, ll_after
            except Exception as e:
                if ML_DEBUG:
                    print("[ml_ranker] iso failed:", repr(e))
                return False, float("inf"), float("inf")

        used = "none"
        if calibrate:
            if CALIB_MODE == "platt":
                ok, _, _ = _try_platt()
                used = "platt" if ok else "none"
            elif CALIB_MODE == "iso":
                ok, _, _ = _try_iso()
                used = "iso" if ok else "none"
            elif CALIB_MODE == "pct":
                used = "pct"
            elif CALIB_MODE == "none":
                used = "none"
            else:  # auto
                ok, llb, lla = _try_platt()
                if ok:
                    used = "platt"
                else:
                    ok2, _, _ = _try_iso()
                    if ok2:
                        used = "iso"
                    else:
                        used = "pct"

            if used == "pct":
                p5, p95 = float(np.percentile(p_tr, 5)), float(np.percentile(p_tr, 95))
                self.calib = ("pct", p5, p95)
            elif used == "none":
                self.calib = None
        else:
            used = "none"
            self.calib =  None
            self.iso = None

        # 8) 持久化
        if save_model and _HAS_SK:
            try:
                joblib.dump(self.dnn, DNN_PATH)
            except Exception:
                pass
        meta = {
            "features_all": FEATURES_MAIN,
            "features_used": self.selected_feats,
            "expected_dim": self.expected_dim,
            # calib 存储：platt/pct 直接数值；iso 仅标记类型，具体模型另存 ISO_PATH
            "calib": (list(self.calib) if self.calib else None),
            "calib_mode": used,
            "auc_train": auc_tr, "auc_val": auc_val,
        }
        if save_model:
            if ML_DEBUG:
                print("[ml_ranker] meta =", meta)
            with open(META_PATH, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)

        return {
            "train_auc": auc_tr, "val_auc": auc_val,
            "n_samples": int(len(y)), "n_feats_used": len(self.selected_feats),
            "calib_mode": used
        }

    # ----- 特征构造（与 recommend_service 一致口径） -----
    def _extract_features(self, me: Dict[str, Any], other: Dict[str, Any], return_names=True):
        # 相似度细项
        sim_kw = _jaccard(me.get("kw_tokens", []), other.get("kw_tokens", []))
        sim_city = 1.0 if me.get("city") and me.get("city") == other.get("city") else 0.0
        sim_home = 1.0 if _same_loc(me.get("hometown"), other.get("hometown")) else 0.0
        similarity = 0.55 * sim_kw + 0.25 * sim_city + 0.20 * sim_home

        # 互补性细项
        comp_gender = 1.0 if (_gender_opposite(me.get("gender")) == str(other.get("gender")).lower()
                              or _gender_opposite(other.get("gender")) == str(me.get("gender")).lower()) else 0.5
        comp_age = _age_complement(me.get("age"), other.get("age"))
        comp_height = _height_comfort(me.get("height_cm"), other.get("height_cm"))
        complementarity = 0.34 * comp_gender + 0.33 * comp_age + 0.33 * comp_height

        # 意向与生活方式
        intent_score, _ = self._intention_proxy(me, other)
        life_score, _ = _lifestyle_similarity(me, other)

        # 可信与安全
        ver_score, _ = _verification_score(other.get("_verification"))
        risk_coef, _ = _risk_penalty(other.get("_risk"))
        med_score, _ = _media_score(other.get("_media_list", []), other.get("_has_avatar", False))
        like_score, _ = _like_signal(me.get("id"), other.get("id"), {}, {})
        trust_raw = 0.55 * ver_score + 0.25 * med_score + 0.20 * max(0.0, like_score)
        trust_safety = max(0.0, min(1.0, trust_raw)) * _safe_float(risk_coef, 1.0)

        # 衍生交叉
        age1 = _safe_float(me.get("age"));      age2 = _safe_float(other.get("age"))
        h1   = _safe_float(me.get("height_cm")); h2 = _safe_float(other.get("height_cm"))
        age_diff_abs    = abs(age1 - age2) if (age1 and age2) else 0.0
        height_diff_abs = abs(h1 - h2) if (h1 and h2) else 0.0

        sim_kw_x_life = sim_kw * life_score
        intent_x_trust = intent_score * trust_safety
        comp_x_trust   = complementarity * trust_safety

        row = {
            "similarity": similarity,
            "complementarity": complementarity,
            "intention_fit": intent_score,
            "lifestyle": life_score,
            "trust_safety": trust_safety,
            "sim_kw": sim_kw, "sim_city": sim_city, "sim_home": sim_home,
            "comp_gender": comp_gender, "comp_age": comp_age, "comp_height": comp_height,
            "ver_score": ver_score, "med_score": med_score, "like_score": like_score, "risk_coef": risk_coef,
            "age_diff_abs": age_diff_abs, "height_diff_abs": height_diff_abs,
            "sim_kw_x_life": sim_kw_x_life, "intent_x_trust": intent_x_trust, "comp_x_trust": comp_x_trust,
        }
        if ML_DEBUG:
            pr = {k: (round(float(v), 4) if isinstance(v, (int, float)) else v) for k, v in row.items()}
            print("[ml_ranker] feat_row:", pr)

        feat_list = self.selected_feats if self.selected_feats else FEATURES_MAIN
        vec = np.array([_safe_float(row.get(k)) for k in feat_list], dtype=np.float32)
        return (vec, feat_list) if return_names else vec

    def _intention_proxy(self, me: Dict[str, Any], other: Dict[str, Any]) -> Tuple[float, List[str]]:
        """
        轻代理版“意向契合”，避免循环依赖；生产中可替换为 recommend_service 的纯函数版。
        """
        A = me.get("intent") or {}; B = other.get("intent") or {}

        def one_side_score(src_intent: Dict[str, Any], tgt: Dict[str, Any]) -> float:
            if not src_intent: return 0.5
            s = 0.0; w = 0.0
            # 年龄
            try:
                amin = src_intent.get("preferred_age_min"); amax = src_intent.get("preferred_age_max")
                age  = tgt.get("age")
                if age is not None and (amin is not None or amax is not None):
                    w += 1.0
                    if (amin is None or age >= amin) and (amax is None or age <= amax): s += 1.0
                    else:
                        if amin is not None and age < amin: s += max(0.0, 1.0 - (amin - age)/10.0)
                        elif amax is not None and age > amax: s += max(0.0, 1.0 - (age - amax)/10.0)
            except Exception: pass
            # 身高
            try:
                hmin = src_intent.get("preferred_height_min"); hmax = src_intent.get("preferred_height_max")
                ht   = tgt.get("height_cm")
                if ht is not None and (hmin is not None or hmax is not None):
                    w += 1.0
                    if (hmin is None or ht >= hmin) and (hmax is None or ht <= hmax): s += 1.0
                    else:
                        if hmin is not None and ht < hmin: s += max(0.0, 1.0 - (hmin - ht)/10.0)
                        elif hmax is not None and ht > hmax: s += max(0.0, 1.0 - (ht - hmax)/10.0)
            except Exception: pass
            # 城市/异地
            try:
                pref_cities = set((src_intent.get("preferred_cities") or []) + [])
                accept_ld = bool(src_intent.get("accept_long_distance"))
                w += 1.0
                if pref_cities:
                    s += 1.0 if str(tgt.get("city")) in pref_cities else (0.6 if accept_ld else 0.0)
                else:
                    s += 1.0 if accept_ld else 0.5
            except Exception: pass
            # 婚育接受度
            try:
                divorced_like = str(tgt.get("marital_status") or "").lower() in ("divorced", "widowed")
                has_children  = bool(tgt.get("has_children"))
                ok_divorce   = bool(src_intent.get("accept_divorce", False))
                ok_children  = bool(src_intent.get("accept_children", False))
                w += 1.0
                hit = 1.0
                if divorced_like and not ok_divorce:  hit -= 0.5
                if has_children  and not ok_children: hit -= 0.5
                s += max(0.0, hit)
            except Exception: pass
            return (s / w) if w > 0 else 0.5

        s_ab = one_side_score(A, other)
        s_ba = one_side_score(B, me)
        score = 0.5 * s_ab + 0.5 * s_ba
        return float(max(0.0, min(1.0, score))), []

    # ----- 训练辅助 -----
    def _build_matrix(self, samples: List[Tuple[Dict[str, Any], Dict[str, Any], int]]):
        X_list, y_list = [], []
        for me, other, label in samples:
            vec = self._extract_features(me, other, return_names=False)
            X_list.append(vec); y_list.append(int(label))
        X = np.vstack(X_list)
        y = np.array(y_list, dtype=np.int32)
        return X, y

    def _variance_filter(self, X: np.ndarray, eps: float = 1e-8):
        """去掉近似零方差特征，避免相关系数计算除零/NaN。"""
        var = X.var(axis=0)
        keep = np.where(var > eps)[0]
        return keep

    def _split_train_val(self,
                         samples: List[Tuple[Dict[str, Any], Dict[str, Any], int]],
                         X: np.ndarray, y: np.ndarray,
                         test_size: float = 0.15,
                         mode: str = "by_me",         # "by_me" 或 "user_disjoint"
                         random_state: int = 42):
        """
        by_me:    按 query 侧（me.id）分组，不让同一个 me 出现在 train+val（推荐）
        user_disjoint: 严格模式，把全体用户分成两份，仅保留“双方都在同一份”的样本（会丢弃跨分区样本）
        """
        me_ids    = np.array([s[0].get("id") for s in samples])
        other_ids = np.array([s[1].get("id") for s in samples])

        if mode == "user_disjoint":
            rng = np.random.RandomState(random_state)
            users = np.array(sorted(set(me_ids.tolist()) | set(other_ids.tolist())))
            rng.shuffle(users)
            cut = max(1, int(len(users) * (1 - test_size)))
            train_users = set(users[:cut].tolist())
            val_users   = set(users[cut:].tolist())
            train_mask = np.array([(m in train_users) and (o in train_users) for m, o in zip(me_ids, other_ids)])
            val_mask   = np.array([(m in val_users)   and (o in val_users)   for m, o in zip(me_ids, other_ids)])

            X_tr, y_tr = X[train_mask], y[train_mask]
            X_val, y_val = X[val_mask],  y[val_mask]
            # 样本太少或验证集单类，自动回退
            if (len(y_val) >= 20) and (len(set(y_val.tolist())) >= 2):
                return X_tr, X_val, y_tr, y_val
            # 回退
            mode = "by_me"

        # 默认：按 me.id 分组
        gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
        idx_tr, idx_val = next(gss.split(X, y, groups=me_ids))
        return X[idx_tr], X[idx_val], y[idx_tr], y[idx_val]

    # ----- 装载已训练模型 -----
    def _load_if_exists(self):
        try:
            if os.path.exists(DNN_PATH) and _HAS_SK:
                self.dnn = joblib.load(DNN_PATH)
            if os.path.exists(META_PATH):
                with open(META_PATH, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                self.selected_feats = meta.get("features_used") or []
                self.expected_dim = int(meta.get("expected_dim") or (len(self.selected_feats) or 0)) or None
                calib = meta.get("calib")
                if isinstance(calib, (list, tuple)) and len(calib) == 3:
                    kind = str(calib[0])
                    if kind == "iso" and os.path.exists(ISO_PATH):
                        # 仅在 iso 模式尝试加载
                        try:
                            self.iso = joblib.load(ISO_PATH)
                            self.calib = ("iso", float("nan"), float("nan"))
                        except Exception:
                            self.iso = None
                            self.calib = None
                    else:
                        # platt / pct
                        try:
                            a = float(calib[1]); b = float(calib[2])
                            self.calib = (kind, a, b)
                        except Exception:
                            self.calib = None
            if ML_DEBUG:
                print("[ml_ranker] loaded: available=", self.available(),
                      "used_dim=", self.expected_dim, "feat_cnt=", len(self.selected_feats),
                      "calib=", self.calib, "iso_loaded=", self.iso is not None)
        except Exception as e:
            self.last_error = f"load_error: {e!r}"
            self.dnn = None
            self.selected_feats = []
            self.expected_dim = None
            self.calib = None
            self.iso = None
            if ML_DEBUG:
                print("[ml_ranker] load_error:", repr(e))

# 单例
ml_ranker = HybridXgbDnnRanker()
