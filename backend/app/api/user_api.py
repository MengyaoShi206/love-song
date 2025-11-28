# backend/app/api/user.py
import json
from operator import and_
from fastapi import APIRouter, HTTPException, Depends # type: ignore
from sqlalchemy.orm import Session # type: ignore
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator
import re
from sqlalchemy import func, or_, desc # type: ignore
from app.utils.multi_writer import MultiWriter

from app.database import SessionLocal
from app.models.user import (UserAccount, UserProfilePublic, UserMedia,
                              UserQna, UserLifestyle, UserIntention,
                              UserSubscription, UserLike, Match, UserCertification
                            )
from app.models.platform import UserVerification, RiskAssessment
from datetime import date, datetime
from app.services.recommend_service import RecommendService
from app.models.advantage import Advantage


router = APIRouter()
recommend_service = RecommendService()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class LoginIn(BaseModel):
    username: str
    password_hash: str

PHONE_CN = re.compile(r"^1[3-9]\d{9}$")  # 简单大陆手机号校验

class UserCreate(BaseModel):
    username: str
    password_hash: str
    nickname: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    gender: Optional[str] = None
    city: Optional[str] = None
    avatar_url: Optional[str] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str):
        if not (3 <= len(v) <= 20):
            raise ValueError("用户名长度需在 3-20 之间")
        if not re.fullmatch(r"[A-Za-z0-9_]+", v):
            raise ValueError("用户名仅允许字母/数字/下划线")
        return v

    @field_validator("password_hash")
    @classmethod
    def validate_pwdhash(cls, v: str):
        if not v or len(v) < 4:
            raise ValueError("密码哈希长度至少 4（演示环境）")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]):
        if v and not PHONE_CN.fullmatch(v):
            raise ValueError("手机号格式不正确（大陆 11 位）")
        return v

class UserOut(BaseModel):
    id: int
    username: str
    nickname: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    avatar_url: Optional[str] = None
    class Config:
        from_attributes = True

class ProfileUpdateIn(BaseModel):
    nickname: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = None
    tagline: Optional[str] = None
    bio: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if v is None:
            return v
        import re
        if not re.fullmatch(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式不正确（大陆 11 位）")
        return v


def _filled(v) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return len(v.strip()) > 0
    return True

def _strlen(s) -> int:
    return len(s.strip()) if isinstance(s, str) else 0

def _build_payload(uid: int, db: Session) -> Dict[str, Any]:
    """聚合用户资料到 payload，便于评分"""
    ua = db.query(UserAccount).filter(UserAccount.id == uid).first()
    prof = db.query(UserProfilePublic).filter(UserProfilePublic.user_id == uid).first()
    ui = db.query(UserIntention).filter(UserIntention.user_id == uid).first()
    ul = db.query(UserLifestyle).filter(UserLifestyle.user_id == uid).first()
    media_count = db.query(UserMedia).filter(UserMedia.user_id == uid, UserMedia.audit_status == "approved").count()
    qna_count = db.query(UserQna).filter(UserQna.user_id == uid, UserQna.visible == True).count()

    return {
        "user_account": ua.__dict__ if ua else {},
        "user_profile_public": prof.__dict__ if prof else {},
        "user_intention": ui.__dict__ if ui else {},
        "user_lifestyle": ul.__dict__ if ul else {},
        "media_count": media_count,
        "qna_count": qna_count,
    }


def _compute_completion_score(payload: dict) -> tuple[int, dict]:
    """
    直接根据 /api/user/main/{uid} 返回的 payload 计算完善度
    返回: (score, breakdown)
    """
    ua = payload.get("user_account") or {}
    up = payload.get("user_profile_public") or {}
    ui = payload.get("user_intention") or {}
    ul = payload.get("user_lifestyle") or {}
    media_count = int(payload.get("media_count") or 0)
    qna_count = int(payload.get("qna_count") or 0)

    score = 0
    detail = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0}

    # ===== A. 基础信息 35 =====
    A_weights = {
        "avatar_url": 5, "phone": 5, "email": 5, "city": 3, "hometown": 2,
        "gender": 3, "birth_date": 3, "height_cm": 3, "weight_kg": 2,
        "nickname": 1, "marital_status": 2, "has_children": 1,
    }
    A = 0
    for f, w in A_weights.items():
        if _filled(ua.get(f)):
            A += w
    A = min(A, 35)
    detail["A"] = A
    score += A

    # ===== B. 公开资料 20 =====
    B = 0
    if _strlen(up.get("tagline")) >= 6:
        B += 6
    bio_len = _strlen(up.get("bio"))
    if bio_len >= 80:
        B += 14
    elif bio_len >= 40:
        B += 11
    elif bio_len >= 20:
        B += 7
    elif bio_len >= 10:
        B += 5
    B = min(B, 20)
    detail["B"] = B
    score += B

    # ===== C. 择偶意向 20 =====
    # 注意：此处不再对 accept_long_distance 二次计分（避免和 A 重复）
    C_weights = {
        "relationship_goal": 2,
        "preferred_age_min": 2, "preferred_age_max": 2,
        "preferred_height_min": 2, "preferred_height_max": 2,
        "preferred_cities": 2, 'accept_long_distance':2,
        "accept_divorce": 1, "accept_children": 1,
        "marriage_timeline": 1, "child_plan": 1,
        "family_view": 1, "religion": 1,
    }
    C = 0
    for f, w in C_weights.items():
        if _filled(ui.get(f)):
            C += w
    C = min(C, 20)
    detail["C"] = C
    score += C

    # ===== D. 生活方式 15 =====
    D_weights = {
        "schedule": 1, "workout_freq": 1, "diet": 1, "personality": 2,
        "drinking": 1, "smoking": 1, "pet_view": 1, "spending_view": 2,
        "saving_view": 1, "travel_pref": 2, "interests": 2,
    }
    D = 0
    for f, w in D_weights.items():
        if _filled(ul.get(f)):
            D += w
    D = min(D, 15)
    detail["D"] = D
    score += D

    # ===== E. 媒体 5 =====
    if media_count >= 3: E = 5
    elif media_count >= 1: E = 4
    else: E = 0
    detail["E"] = E
    score += E

    # ===== F. Q&A 5 =====
    if qna_count >= 3: F = 5
    elif qna_count >= 2: F = 4
    elif qna_count == 1: F = 3
    else: F = 0
    detail["F"] = F
    score += F

    return min(int(score), 100), detail

def _get_or_create_profile(uid: int, db: Session) -> UserProfilePublic:
    prof = db.query(UserProfilePublic).filter(UserProfilePublic.user_id == uid).first()
    if not prof:
        prof = UserProfilePublic(
            user_id=uid, tagline="", bio="", visibility_scope="public", completion_score=0
        )
        db.add(prof)
        db.commit()
        db.refresh(prof)
    return prof

def _age_from_birth(birth: Optional[date]) -> Optional[int]:
    if not birth: return None
    today = date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))

def _user_brief(u: UserAccount, prof: Optional[UserProfilePublic]) -> Dict[str, Any]:
    return {
        "id": u.id,
        "username": u.username,
        "nickname": u.nickname,
        "city": u.city,
        "gender": u.gender,
        "age": _age_from_birth(u.birth_date),
        "avatar_url": u.avatar_url,
        "tagline": (prof.tagline if prof else "") or "",
        "bio": (prof.bio if prof else "") or "",
    }


def _as_date_or_none(v):
    """把前端传来的 birth_date 统一成 date 或 None。允许 '', None, 'YYYY-MM-DD', datetime 等。"""
    if v in (None, "", "null", "None"):
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        s = v.strip()
        # 只取到日，兼容 "2025-10-08", "2025-10-08T00:00:00Z"
        try:
            return date.fromisoformat(s[:10])
        except Exception:
            pass
        # 兜底：严格格式
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except Exception:
            raise HTTPException(status_code=422, detail=f"birth_date 格式错误：{v!r}，期望 YYYY-MM-DD")
    raise HTTPException(status_code=422, detail=f"birth_date 类型不支持：{type(v).__name__}")

def _as_int_or_none(v, field, lo=None, hi=None):
    if v in (None, "", "null", "None"):
        return None
    try:
        n = int(v)
    except Exception:
        raise HTTPException(status_code=422, detail=f"{field} 需要整数")
    if lo is not None and n < lo: 
        raise HTTPException(status_code=422, detail=f"{field} 不能小于 {lo}")
    if hi is not None and n > hi:
        raise HTTPException(status_code=422, detail=f"{field} 不能大于 {hi}")
    return n

def _as_bool_or_none(v):
    if v in (None, "", "null", "None"):
        return None
    if isinstance(v, bool):
        return v
    if str(v).lower() in ("1","true","t","yes","y"):
        return True
    if str(v).lower() in ("0","false","f","no","n"):
        return False
    raise HTTPException(status_code=422, detail=f"布尔字段取值不正确：{v!r}")


# ---------- 路由 ----------
@router.post("/register", response_model=UserOut)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    """
    注册：
    1) 唯一约束检查（username / email / phone）
    2) 写入 user_account
    3) 创建 user_profile_public 占位（用于资料完善度）
    """
    # 唯一性检查（按需增删）
    if db.query(UserAccount).filter(UserAccount.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    if payload.email and db.query(UserAccount).filter(UserAccount.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    if payload.phone and db.query(UserAccount).filter(UserAccount.phone == payload.phone).first():
        raise HTTPException(status_code=400, detail="Phone already exists")

    # 写入 user_account
    new_user = UserAccount(
        username=payload.username,
        nickname=payload.nickname,
        email=payload.email,
        phone=payload.phone,
        gender=payload.gender,
        city=payload.city,
        avatar_url=payload.avatar_url,
        password_hash=payload.password_hash,
        is_active=True,
        is_verified=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    prof = UserProfilePublic(
        user_id=new_user.id,
        tagline="",
        bio="",
        visibility_scope="public",
        completion_score=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    lifestyle = UserLifestyle(
        user_id=new_user.id,
        schedule=None,
        drinking=None,
        smoking=None,
        workout_freq=None,
        diet=None,
        pet_view=None,
        spending_view=None,
        saving_view=None,
        travel_pref=None,
        interests=None,
        personality=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    intention = UserIntention(
        user_id=new_user.id,
        relationship_goal=None,
        preferred_age_min=None,
        preferred_age_max=None,
        preferred_height_min=None,
        preferred_height_max=None,
        preferred_cities=None,
        accept_long_distance=None,
        accept_divorce=None,
        accept_children=None,
        marriage_timeline=None,
        child_plan=None,
        family_view=None,
        religion=None,
        must_not_accept=None,
        bonus_points=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add_all([prof, lifestyle, intention])
    db.commit()

    # 注册完立即计算完善度
    payload_for_score = {
        "user_account": {
            "id": new_user.id,
            "username": new_user.username,
            "nickname": new_user.nickname,
            "phone": new_user.phone,
            "email": new_user.email,
            "gender": new_user.gender,
            "city": new_user.city,
            "avatar_url": new_user.avatar_url,
            "marital_status": new_user.marital_status,
            "has_children": new_user.has_children,
            "accept_long_distance": new_user.accept_long_distance,
        },
        "user_profile_public": {
            "tagline": prof.tagline,
            "bio": prof.bio,
            "visibility_scope": prof.visibility_scope,
        },
        "user_intention": {},
        "user_lifestyle": {},
        "media_count": 0,
        "qna_count": 0,
    }

    # === 5️⃣ 调用新的 _compute_completion_score ===
    try:
        score, detail = _compute_completion_score(payload_for_score)
    except Exception as e:
        print(f"⚠️ 完善度计算出错: {e}")
        score, detail = 0, {}

    prof.completion_score = score
    print(score)
    prof.updated_at = datetime.utcnow()
    db.commit()

    # 同步 MySQL + 异步 Doris
    MultiWriter.write(new_user, db=db, mirror=True)  
    MultiWriter.write(prof, db=db, mirror=True)
    MultiWriter.write(lifestyle, db=db, mirror=True)
    MultiWriter.write(intention, db=db, mirror=True)
    
    return {
        "id": new_user.id,
        "username": new_user.username,
        "completion_score": score,
        "breakdown": detail
    }


@router.post("/login", response_model=UserOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    """
    登录（演示版）：
    - 通过 username 查找用户
    - 直接比对 password_hash 字段
    生产建议：使用 bcrypt/argon2 等校验哈希，返回 JWT 或 Session。
    """
    user = db.query(UserAccount).filter(UserAccount.username == payload.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user.password_hash != payload.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return user


# --------- 新接口：main/{uid} ---------
@router.get("/main/{uid}")
def main_profile(uid: int, db: Session = Depends(get_db)):
    """主界面资料展示"""
    print(uid)
    user = db.query(UserAccount).filter(UserAccount.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    profile = db.query(UserProfilePublic).filter(UserProfilePublic.user_id == uid).first()
    # print(profile)
    intention = db.query(UserIntention).filter(UserIntention.user_id == uid).first()
    # print(intention)
    lifestyle = db.query(UserLifestyle).filter(UserLifestyle.user_id == uid).first()
    # print(lifestyle)
    qna = db.query(UserQna).filter(UserQna.user_id == uid, UserQna.visible == True).all()
    # print(qna)
    # 数据计数
    media_count = db.query(func.count(UserMedia.id)).filter(
        UserMedia.user_id == uid, UserMedia.audit_status == "approved"
    ).scalar() or 0
    print(media_count)
    qna_count = len(qna)

    # --- 新增：会员订阅信息 ---
    subscription = db.query(UserSubscription).filter(UserSubscription.user_id == uid).first()
    plan_code = subscription.plan_code if subscription else None


    # 资料完善度
    completion = profile.completion_score if profile else 0
    print(plan_code)
    return {
        "user_account": {
            "id": user.id,
            "username": user.username,
            "nickname": user.nickname,
            "phone": user.phone,
            "email": user.email,
            "gender": user.gender,
            "birth_date": user.birth_date,
            "height_cm": user.height_cm,
            "weight_kg": user.weight_kg,
            "avatar_url": user.avatar_url,
            "city": user.city,
            "hometown": user.hometown,
            "marital_status": user.marital_status,
            "has_children": user.has_children,
            "accept_long_distance": user.accept_long_distance,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        },
        "user_profile_public": {
            "tagline": profile.tagline if profile else "",
            "bio": profile.bio if profile else "",
            "visibility_scope": profile.visibility_scope if profile else "public",
            "completion_score": completion,
            "created_at": profile.created_at if profile else None,
            "updated_at": profile.updated_at if profile else None,
        },
        "user_intention": {
            "relationship_goal": intention.relationship_goal if intention and intention.relationship_goal else "dating",
            "preferred_age_min": intention.preferred_age_min if intention else None,
            "preferred_age_max": intention.preferred_age_max if intention else None,
            "preferred_height_min": intention.preferred_height_min if intention else None,
            "preferred_height_max": intention.preferred_height_max if intention else None,
            "preferred_cities": intention.preferred_cities if intention else None,
            "accept_long_distance": intention.accept_long_distance if intention else None,
            "accept_divorce": intention.accept_divorce if intention else None,
            "accept_children": intention.accept_children if intention else None,
            "marriage_timeline": intention.marriage_timeline if intention else None,
            "child_plan": intention.child_plan if intention else None,
            "family_view": intention.family_view if intention else None,
            "religion": intention.religion if intention else None,
            "must_not_accept": intention.must_not_accept if intention else None,
            "bonus_points": intention.bonus_points if intention else None,
            "created_at": intention.created_at if intention else None,
            "updated_at": intention.updated_at if intention else None,
        },
        "user_lifestyle": {
            "schedule": lifestyle.schedule if lifestyle else None,
            "drinking": lifestyle.drinking if lifestyle else None,
            "smoking": lifestyle.smoking if lifestyle else None,
            "workout_freq": lifestyle.workout_freq if lifestyle else None,
            "diet": lifestyle.diet if lifestyle else None,
            "pet_view": lifestyle.pet_view if lifestyle else None,
            "spending_view": lifestyle.spending_view if lifestyle else None,
            "saving_view": lifestyle.saving_view if lifestyle else None,
            "travel_pref": lifestyle.travel_pref if lifestyle else None,
            "interests": lifestyle.interests if lifestyle else None,
            "personality": lifestyle.personality if lifestyle else None,
            "created_at": lifestyle.created_at if lifestyle else None,
            "updated_at": lifestyle.updated_at if lifestyle else None,
        },
        "user_qna": [
            {
                "question": item.question,
                "answer": item.answer,
                "created_at": item.created_at,
            }
            for item in qna
        ],
        "media_count": media_count,
        "qna_count": qna_count,
        "plan_code": plan_code,
    }


# --------- 更新资料 + 重算分数 ---------
@router.put("/profile/{uid}")
def update_profile(uid: int, payload: Dict[str, Any], db: Session = Depends(get_db)):
    """
    更新用户资料 + 重新计算完善度
    """
    u = db.query(UserAccount).filter(UserAccount.id == uid).first()
    if not u:
        raise HTTPException(404, "用户不存在")

    # ---------- 读取嵌套或扁平 ----------
    ua_in = payload.get("user_account") or payload
    up_in: Dict[str, Any] = payload.get("user_profile_public") or {}
    ul_in: Dict[str, Any] = payload.get("user_lifestyle") or {}

    # 顶层兜底（如果是扁平进来的）
    def g(key: str, default=None):
        return payload.get(key, default)

    # ---------- 唯一性检查（支持嵌套） ----------
    new_email = ua_in.get("email", g("email"))
    new_phone = ua_in.get("phone", g("phone"))

    if new_email and new_email != u.email:
        if db.query(UserAccount).filter(UserAccount.email == new_email).first():
            raise HTTPException(400, "Email 已被占用")
    if new_phone and new_phone != u.phone:
        if db.query(UserAccount).filter(UserAccount.phone == new_phone).first():
            raise HTTPException(400, "手机号已被占用")

    # ---------- 更新账户基础字段（从嵌套或扁平读取） ----------
    for f in ("nickname","city","phone","email","avatar_url","hometown","gender","marital_status","has_children"):
        if f in ua_in:
            setattr(u, f, ua_in.get(f))

    # 关键：birth_date 要转成 date
    if "birth_date" in ua_in:
        u.birth_date = _as_date_or_none(ua_in.get("birth_date"))

    if "height_cm" in ua_in:
        u.height_cm = _as_int_or_none(ua_in.get("height_cm"), "身高(cm)", lo=120, hi=230)

    if "weight_kg" in ua_in:
        u.weight_kg = _as_int_or_none(ua_in.get("weight_kg"), "体重(kg)", lo=35, hi=150)

    if "has_children" in ua_in:
        u.has_children = _as_bool_or_none(ua_in.get("has_children"))

    if "accept_long_distance" in ua_in:
        u.accept_long_distance = _as_bool_or_none(ua_in.get("accept_long_distance"))

    u.updated_at = datetime.utcnow()

    # ---------- 更新公开资料 ----------
    prof = _get_or_create_profile(uid, db)
    if "tagline" in up_in or "tagline" in payload:
        prof.tagline = up_in.get("tagline", g("tagline"))
    if "bio" in up_in or "bio" in payload:
        prof.bio = up_in.get("bio", g("bio"))

    # ---------- 更新生活方式（支持嵌套/扁平） ----------
    LIFESTYLE_FIELDS = [
        "schedule", "drinking", "smoking", "workout_freq", "diet",
        "pet_view", "spending_view", "saving_view", "travel_pref",
        "interests", "personality",
    ]
    lifestyle = db.query(UserLifestyle).filter(UserLifestyle.user_id == uid).first()
    if lifestyle is None:
        lifestyle = UserLifestyle(user_id=uid, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        db.add(lifestyle)

    def _pick_lifestyle_value(field: str):
        # 先看嵌套 user_lifestyle，再看扁平
        return ul_in.get(field, g(field))

    def _jsonish(v):
        # 如果你的 DB 对应列是 TEXT，统一转 JSON 字符串
        if isinstance(v, (list, dict)):
            try:
                return json.dumps(v, ensure_ascii=False)
            except Exception:
                return str(v)
        return v

    life_touched = False
    for f in LIFESTYLE_FIELDS:
        if (f in ul_in) or (f in payload):
            val = _pick_lifestyle_value(f)
            # travel_pref / interests 可能是数组
            if f in ("travel_pref", "interests"):
                val = _jsonish(val)
            setattr(lifestyle, f, val)
            life_touched = True
    if life_touched:
        lifestyle.updated_at = datetime.utcnow()

    # ---------- Q&A：全量替换（仅当给到 user_qna） ----------
    qna_touched = False
    if "user_qna" in payload and isinstance(payload["user_qna"], list):
        db.query(UserQna).filter(UserQna.user_id == uid).delete()
        for q in payload["user_qna"]:
            if not q:
                continue
            db.add(UserQna(
                user_id=uid,
                question=(q.get("question") or "")[:200],
                answer=(q.get("answer") or "")[:500],
                visible=True,
                created_at=datetime.utcnow(),
            ))
        qna_touched = True

    # ---------- Intention：字段级 upsert（仍然使用嵌套 user_intention） ----------
    intent_touched = False
    if "user_intention" in payload and isinstance(payload["user_intention"], dict):
        data = payload["user_intention"]
        intention = db.query(UserIntention).filter(UserIntention.user_id == uid).first()
        if intention is None:
            intention = UserIntention(user_id=uid, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
            db.add(intention)

        # preferred_cities 可能是数组 -> 统一做 JSON 字符串（如列是 TEXT）
        def _coerce_cities(v):
            if isinstance(v, (list, dict)):
                try:
                    return json.dumps(v, ensure_ascii=False)
                except Exception:
                    return str(v)
            return v

        for f in [
            "relationship_goal",
            "preferred_age_min", "preferred_age_max",
            "preferred_height_min", "preferred_height_max",
            "preferred_cities",
            "accept_long_distance", "accept_divorce", "accept_children",
            "marriage_timeline", "child_plan", "family_view",
            "religion", "must_not_accept", "bonus_points",
        ]:
            if f in data:
                val = data.get(f)
                if f == "preferred_cities":
                    val = _coerce_cities(val)
                setattr(intention, f, val)
                intent_touched = True
        if intent_touched:
            intention.updated_at = datetime.utcnow()

    # ---------- 相册（可选，若你前端传入 user_media 列表就更新） ----------
    media_touched = False
    if "user_media" in payload and isinstance(payload["user_media"], list):
        db.query(UserMedia).filter(UserMedia.user_id == uid).delete()
        for i, m in enumerate(payload["user_media"]):
            if not m:
                continue
            db.add(UserMedia(
                user_id=uid,
                media_type=(m.get("media_type") or "photo"),
                url=m.get("url") or "",
                thumb_url=m.get("thumb_url"),
                audit_status=(m.get("audit_status") or "pending"),
                sort_order=int(m.get("sort_order") or i),
                created_at=datetime.utcnow(),
            ))
        media_touched = True

    # ---------- 认证（可选） ----------
    cert_touched = False
    if "user_certifications" in payload and isinstance(payload["user_certifications"], list):
        db.query(UserCertification).filter(UserCertification.user_id == uid).delete()
        for c in payload["user_certifications"]:
            if not c:
                continue
            db.add(UserCertification(
                user_id=uid,
                cert_type=c.get("cert_type") or "identity",
                status=c.get("status") or "pending",
                doc_meta=c.get("doc_meta"),
                reviewed_by=c.get("reviewed_by"),
                reviewed_at=c.get("reviewed_at"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ))
        cert_touched = True

    # ---------- 重算完善度 ----------
    payload_for_score = _build_payload(uid, db)
    score, detail = _compute_completion_score(payload_for_score)
    prof.completion_score = score
    prof.updated_at = datetime.utcnow()

    db.commit()           # 1) 先提交
    db.expunge_all()      # 2) 解除 ORM 对象与本 session 的绑定（防止后续惰性加载再用到这个 session）

    # ---------- 镜像到 Doris ----------
    MultiWriter.mirror_only(u)
    MultiWriter.mirror_only(prof)
    if life_touched:
        MultiWriter.mirror_only(lifestyle)
    if intent_touched:
        intention = db.query(UserIntention).filter(UserIntention.user_id == uid).first()
        if intention:
            MultiWriter.mirror_only(intention)
    if media_touched:
        for m in db.query(UserMedia).filter(UserMedia.user_id == uid).all():
            MultiWriter.mirror_only(m)
    if cert_touched:
        for c in db.query(UserCertification).filter(UserCertification.user_id == uid).all():
            MultiWriter.mirror_only(c)
    if qna_touched:
        for q in db.query(UserQna).filter(UserQna.user_id == uid, UserQna.visible == True).all():
            MultiWriter.mirror_only(q)

    return {"ok": True, "completion_score": score, "breakdown": detail}


@router.post("/completion/{uid}")
def recompute_completion(uid: int, db: Session = Depends(lambda: SessionLocal())):
    """手动触发重算完善度"""
    prof = _get_or_create_profile(uid, db)
    payload_for_score = _build_payload(uid, db)
    score, detail = _compute_completion_score(payload_for_score)
    prof.completion_score = score
    prof.updated_at = datetime.utcnow()
    db.commit()
    return {"completion_score": score, "breakdown": detail}

@router.get("/match/likes/{uid}")
def list_likes(uid: int, page: int = 1, page_size: int = 1, db: Session = Depends(get_db)):
    if page < 1: page = 1
    if page_size < 1 : page_size = 1

    me = db.query(UserAccount).filter(UserAccount.id == uid).first()
    if not me:
        raise HTTPException(404, "用户不存在")

    # 取出我点过“喜欢”的记录
    like_rows = db.query(UserLike).filter(UserLike.liker_id == uid).all()
    target_ids = [r.likee_id for r in like_rows if getattr(r, "likee_id", None)]
    #  去重 + 分页
    target_ids = list(dict.fromkeys(target_ids))
    total = len(target_ids)
    start, end = (page - 1) * page_size, (page - 1) * page_size + page_size
    page_ids = target_ids[start:end]

    if not page_ids:
        return {"items": [], "page": page, "page_size": page_size, "total": total}

    users = db.query(UserAccount).filter(UserAccount.id.in_(page_ids)).all()
    profs = db.query(UserProfilePublic).filter(UserProfilePublic.user_id.in_(page_ids)).all()
    prof_map = {p.user_id: p for p in profs}

    # 批量查询 Match 状态（判断是否双向匹配）
    match_rows = db.query(Match).filter(
        or_(
            and_(Match.user_a == uid, Match.user_b.in_(page_ids)),
            and_(Match.user_b == uid, Match.user_a.in_(page_ids))
        )
    ).all()
    matched_ids = {m.user_a if m.user_b == uid else m.user_b for m in match_rows}

    # 拼装数据
    items = []
    for u in users:
        match_status = "matched" if u.id in matched_ids else "pending"
        prof = prof_map.get(u.id)
        items.append({
            "id": u.id,
            "username": u.username,
            "nickname": u.nickname,
            "city": u.city,
            "gender": u.gender,
            "age": (datetime.utcnow().year - u.birth_date.year
                    - ((datetime.utcnow().month, datetime.utcnow().day)
                       < (u.birth_date.month, u.birth_date.day))) if u.birth_date else None,
            "avatar_url": u.avatar_url,
            "tagline": prof.tagline if prof else "",
            "bio": prof.bio if prof else "",
            "match_status": match_status,
        })

    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get("/match/liked_me/{uid}")
def list_liked_me(uid: int, page: int = 1, page_size: int = 1, waiting_only: int = 1, db: Session = Depends(get_db)):
    if page < 1: page = 1
    if page_size < 1: page_size = 1

    me = db.query(UserAccount).filter(UserAccount.id == uid).first()
    if not me:
        raise HTTPException(404, "用户不存在")

    # 找到“喜欢了我”的记录（给我点过赞的人）
    rows = db.query(UserLike).filter(UserLike.likee_id == uid).order_by(desc(UserLike.created_at)).all()

    # 提取点赞者 id，按时间顺序去重
    from_ids = []
    seen = set()
    for r in rows:
        lid = getattr(r, "liker_id", None)
        if lid and lid not in seen:
            seen.add(lid)
            from_ids.append(lid)

    if not from_ids:
        return {"items": [], "page": page, "page_size": page_size, "total": 0}

    # === 关键：在分页前计算全量状态，然后按 waiting_only 过滤 ===
    # 我是否已喜欢他们
    my_likes_all = db.query(UserLike).filter(
        UserLike.liker_id == uid,
        UserLike.likee_id.in_(from_ids)
    ).all()
    my_liked_set = {r.likee_id for r in my_likes_all}

    # 是否已匹配
    match_rows_all = db.query(Match).filter(
        or_(
            and_(Match.user_a == uid, Match.user_b.in_(from_ids)),
            and_(Match.user_b == uid, Match.user_a.in_(from_ids))
        )
    ).all()
    matched_set = {m.user_a if m.user_b == uid else m.user_b for m in match_rows_all}

    # 逐个判定状态
    def _status(other_id: int) -> str:
        if other_id in matched_set: return "matched"
        if other_id in my_liked_set: return "pending"
        return "waiting"

    # 如果 waiting_only=1，仅保留 waiting 的 id；否则保留全部
    if int(waiting_only) == 1:
        filtered_ids = [oid for oid in from_ids if _status(oid) == "waiting"]
    else:
        filtered_ids = from_ids

    total = len(filtered_ids)
    start, end = (page - 1) * page_size, (page - 1) * page_size + page_size
    page_ids = filtered_ids[start:end]

    if not page_ids:
        return {"items": [], "page": page, "page_size": page_size, "total": total}

    users = db.query(UserAccount).filter(UserAccount.id.in_(page_ids)).all()
    profs = db.query(UserProfilePublic).filter(UserProfilePublic.user_id.in_(page_ids)).all()
    prof_map = {p.user_id: p for p in profs}

    # 查我是否也喜欢了他们（用于判断是否 matched）
    my_likes = db.query(UserLike).filter(
        UserLike.liker_id == uid,
        UserLike.likee_id.in_(page_ids)
    ).all()
    my_liked_ids = {r.likee_id for r in my_likes}

    # 查 Match 表（双向匹配）
    match_rows = db.query(Match).filter(
        or_(
            and_(Match.user_a == uid, Match.user_b.in_(page_ids)),
            and_(Match.user_b == uid, Match.user_a.in_(page_ids))
        )
    ).all()
    matched_ids = {m.user_a if m.user_b == uid else m.user_b for m in match_rows}

    # 拼装输出
    order_index = {uid_: i for i, uid_ in enumerate(page_ids)}
    users_sorted = sorted(users, key=lambda u: order_index.get(u.id, 10**9))

    items = []
    for u in users_sorted:
        prof = prof_map.get(u.id)
        if u.id in matched_ids:
            status = "matched"
        elif u.id in my_liked_ids:
            status = "pending"  # 我已喜欢对方，等待匹配确认
        else:
            status = "waiting"  # 对方喜欢我，我未操作
        items.append({
            "id": u.id,
            "username": u.username,
            "nickname": u.nickname,
            "city": u.city,
            "gender": u.gender,
            "age": (datetime.utcnow().year - u.birth_date.year
                    - ((datetime.utcnow().month, datetime.utcnow().day)
                       < (u.birth_date.month, u.birth_date.day))) if u.birth_date else None,
            "avatar_url": u.avatar_url,
            "tagline": prof.tagline if prof else "",
            "bio": prof.bio if prof else "",
            "match_status": status
        })

    return {"items": items, "page": page, "page_size": page_size, "total": total}


# --------- 展示页：/display/{uid} ---------
@router.get("/display/{uid}")
def display_profile(uid: int, me_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    资料详情展示：
    - 基础：user_account / user_profile_public / user_intention / user_lifestyle / user_qna
    - 新增：user_medias / verification / risk / like_status / relation_stage
    - me_id：可选，用于返回“你↔TA”的社交状态（喜欢/阶段）
    """
    ua = db.query(UserAccount).filter(UserAccount.id == uid).first()
    if not ua:
        raise HTTPException(404, "用户不存在")

    up  = db.query(UserProfilePublic).filter(UserProfilePublic.user_id == uid).first()
    ui  = db.query(UserIntention).filter(UserIntention.user_id == uid).first()
    ul  = db.query(UserLifestyle).filter(UserLifestyle.user_id == uid).first()
    qna_rows = db.query(UserQna).filter(UserQna.user_id == uid, UserQna.visible == True).order_by(UserQna.id.asc()).all()

    # 相册（如果你只想看审核通过的，把下一行的注释打开）
    medias = (
        db.query(UserMedia)
          .filter(UserMedia.user_id == uid)  # .filter(UserMedia.audit_status == "approved")
          .order_by(UserMedia.sort_order.asc(), UserMedia.id.asc())
          .all()
    )

    # 认证（按最新一条）
    verification = (
        db.query(UserVerification)
          .filter(UserVerification.user_id == uid)
          .order_by(desc(UserVerification.updated_at))
          .first()
    )

    # 风控（target_type=0 表示用户；target_id 可能是字符串或整数）
    risk = (
        db.query(RiskAssessment)
          .filter(
              RiskAssessment.target_type == 0,
              or_(RiskAssessment.target_id == str(uid), RiskAssessment.target_id == uid)
          )
          .order_by(desc(RiskAssessment.created_at))
          .first()
    )

    # 可选：社交状态（需要 me_id）
    like_status = {}
    relation_stage = {}
    if me_id:
        me_to_other = (
            db.query(UserLike)
              .filter(UserLike.liker_id == me_id, UserLike.likee_id == uid)
              .order_by(desc(UserLike.updated_at))
              .first()
        )
        other_to_me = (
            db.query(UserLike)
              .filter(UserLike.liker_id == uid, UserLike.likee_id == me_id)
              .order_by(desc(UserLike.updated_at))
              .first()
        )
        like_status = {
            "me_to_other": me_to_other.status if me_to_other else None,
            "other_to_me": other_to_me.status if other_to_me else None,
        }

        rs = (
            db.query(Match)  # 你项目里“关系阶段”若是 UserRelationStage，就改成那个表
              .filter(
                  or_(
                      and_(Match.user_a == me_id, Match.user_b == uid),
                      and_(Match.user_a == uid,   Match.user_b == me_id),
                  )
              )
              .order_by(desc(Match.created_at))
              .first()
        )
        # 如果你有 UserRelationStage 模型，请把上面查询改成它，并返回 rs.stage/rs.updated_at
        if rs:
            relation_stage = {"stage": "matched" if getattr(rs, "active", True) else "off_the_shelf",
                              "updated_at": getattr(rs, "created_at", None)}

    return {
        "user_account": {
            "id": ua.id, "username": ua.username, "nickname": ua.nickname,
            "gender": ua.gender, "birth_date": ua.birth_date,
            "height_cm": ua.height_cm, "weight_kg": ua.weight_kg,
            "avatar_url": ua.avatar_url, "city": ua.city, "hometown": ua.hometown,
            "marital_status": ua.marital_status, "has_children": ua.has_children,
            "created_at": ua.created_at, "updated_at": ua.updated_at,
        },
        "user_profile_public": {
            "tagline": up.tagline if up else "",
            "bio": up.bio if up else "",
            "visibility_scope": (up.visibility_scope if up else "public"),
            "completion_score": (up.completion_score if up else 0),
            "created_at": up.created_at if up else None,
            "updated_at": up.updated_at if up else None,
        },
        "user_intention": {
            "relationship_goal": ui.relationship_goal if ui and ui.relationship_goal else "dating",
            "preferred_age_min": ui.preferred_age_min if ui else None,
            "preferred_age_max": ui.preferred_age_max if ui else None,
            "preferred_height_min": ui.preferred_height_min if ui else None,
            "preferred_height_max": ui.preferred_height_max if ui else None,
            "preferred_cities": ui.preferred_cities if ui else None,
            "accept_long_distance": ui.accept_long_distance if ui else None,
            "accept_divorce": ui.accept_divorce if ui else None,
            "accept_children": ui.accept_children if ui else None,
            "marriage_timeline": ui.marriage_timeline if ui else None,
            "child_plan": ui.child_plan if ui else None,
            "family_view": ui.family_view if ui else None,
            "religion": ui.religion if ui else None,
            "must_not_accept": ui.must_not_accept if ui else None,
            "bonus_points": ui.bonus_points if ui else None,
            "created_at": ui.created_at if ui else None,
            "updated_at": ui.updated_at if ui else None,
        },
        "user_lifestyle": {
            "schedule": ul.schedule if ul else None,
            "drinking": ul.drinking if ul else None,
            "smoking": ul.smoking if ul else None,
            "workout_freq": ul.workout_freq if ul else None,
            "diet": ul.diet if ul else None,
            "pet_view": ul.pet_view if ul else None,
            "spending_view": ul.spending_view if ul else None,
            "saving_view": ul.saving_view if ul else None,
            "travel_pref": ul.travel_pref if ul else None,
            "interests": ul.interests if ul else None,
            "personality": ul.personality if ul else None,
            "created_at": ul.created_at if ul else None,
            "updated_at": ul.updated_at if ul else None,
        },
        "user_qna": [
            { "question": r.question, "answer": r.answer, "created_at": r.created_at }
            for r in qna_rows
        ],

        # === 新增给前端的字段 ===
        "user_medias": [
            {
                "id": m.id, "media_type": m.media_type, "url": m.url, "thumb_url": m.thumb_url,
                "audit_status": m.audit_status, "sort_order": m.sort_order,
                "created_at": m.created_at, "updated_at": getattr(m, "updated_at", None),
            } for m in medias
        ],
        "verification": (
            {
                "status": verification.status,
                "reason": verification.reason,
                "created_at": verification.created_at,
                "updated_at": verification.updated_at,
            } if verification else {}
        ),
        "risk": (
            {
                "score": risk.score, "action": risk.action,
                "expire_at": risk.expire_at, "created_at": risk.created_at,
            } if risk else {}
        ),
        "like_status": like_status,
        "relation_stage": relation_stage,
    }


# ======== 已双向匹配（Match 表）=======
def _is_active(v) -> bool:
    return v in (True, 1, "1", "true", "TRUE", "True")

@router.get("/match/mutual/{uid}")
def list_mutual(uid: int, page: int = 1, page_size: int = 12, db: Session = Depends(get_db)):
    if page < 1: page = 1
    if page_size < 1 or page_size > 100: page_size = 12

    me = db.query(UserAccount).filter(UserAccount.id == uid).first()
    if not me:
        raise HTTPException(404, "用户不存在")

    # 取和我有关的匹配关系，按时间倒序
    rows = (
        db.query(Match)
        .filter(or_(Match.user_a == uid, Match.user_b == uid))
        .order_by(desc(Match.created_at))
        .all()
    )

    # 仅保留 active 的匹配，拿到“对端用户”ID，按时间顺序去重
    counterpart_ids: List[int] = []
    seen = set()
    for r in rows:
        if not _is_active(getattr(r, "active", True)):
            continue
        other_id = r.user_b if r.user_a == uid else r.user_a
        if other_id and other_id not in seen:
            seen.add(other_id)
            counterpart_ids.append(other_id)

    total = len(counterpart_ids)
    start, end = (page - 1) * page_size, (page - 1) * page_size + page_size
    page_ids = counterpart_ids[start:end]

    if not page_ids:
        return {"items": [], "page": page, "page_size": page_size, "total": total}

    # 批量查用户与公开资料，并按 page_ids 保持顺序
    users = db.query(UserAccount).filter(UserAccount.id.in_(page_ids)).all()
    profs = db.query(UserProfilePublic).filter(UserProfilePublic.user_id.in_(page_ids)).all()
    prof_map = {p.user_id: p for p in profs}
    order_index = {uid_: i for i, uid_ in enumerate(page_ids)}
    users_sorted = sorted(users, key=lambda u: order_index.get(u.id, 10**9))

    items = [_user_brief(u, prof_map.get(u.id)) for u in users_sorted]
    return {"items": items, "page": page, "page_size": page_size, "total": total}


# ======== 为您推荐 =======
@router.get("/recommend/{uid}")
def recommend_users(uid: int, limit: int = 20, page: int = 1, min_completion: int = 0, exclude_liked: int = 1,  exclude_matched: int = 1,  
                    db: Session = Depends(get_db)):
    """
    为您推荐：系统内聚算法（无外部引擎依赖）。
    - min_completion: 候选完善度门槛（0~100）
    """
    base = recommend_service.recommend_for_user(
        db, uid,
        limit=limit,
        page=page,                      # ★ 一定要传进 service
        min_completion=min_completion,
        exclude_liked=bool(exclude_liked),
        exclude_matched=bool(exclude_matched),
    )

    # 这里不再二次过滤，直接返回 service 的结果（它已是分页前过滤后的切片）
    return {
        "items": base.get("items", []),
        "page": page,
        "limit": limit,
        "total": base.get("total", 0),
        "min_completion": min_completion
    }


# ======== 新增一个喜欢的 =======
@router.post("/like")
def like_user(payload: dict, db: Session = Depends(get_db)):
    liker_id = int(payload.get("liker_id") or 0)
    likee_id = int(payload.get("likee_id") or 0)
    if not liker_id or not likee_id:
        raise HTTPException(400, "liker_id / likee_id 缺失")
    if liker_id == likee_id:
        raise HTTPException(400, "不能喜欢自己")

    # 基本存在性检查
    a = db.query(UserAccount).filter(UserAccount.id == liker_id).first()
    b = db.query(UserAccount).filter(UserAccount.id == likee_id).first()
    if not a or not b:
        raise HTTPException(404, "用户不存在")

    # 0) 已匹配早退：如果已经是有效 Match，则不再写 UserLike，直接返回
    existed_match = (
        db.query(Match)
        .filter(
            or_(
                and_(Match.user_a == liker_id, Match.user_b == likee_id),
                and_(Match.user_a == likee_id, Match.user_b == liker_id),
            )
        )
        .first()
    )
    if existed_match and (getattr(existed_match, "active", True) in (True, 1, "1", "true", "TRUE", "True")):
        return {
            "ok": True,
            "status": "already_matched",   # ★ 新增状态
            "refresh": ["mutual"]          # 前端仅需刷新已匹配列表
        }
    
    # 1) 幂等 upsert：我->对方 的喜欢记录
    like = (
        db.query(UserLike)
        .filter(UserLike.liker_id == liker_id, UserLike.likee_id == likee_id)
        .first()
    )
    now = datetime.utcnow()
    if like:
        # 已存在就不重复插，只更新时间
        like.updated_at = now
    else:
        like = UserLike(
            liker_id=liker_id,
            likee_id=likee_id,
            status="pending",
            created_at=now,
            updated_at=now,
        )
        db.add(like)

    # 2) 检查对方是否也喜欢我（对方->我）
    reverse = (
        db.query(UserLike)
        .filter(UserLike.liker_id == likee_id, UserLike.likee_id == liker_id)
        .first()
    )

    matched = False
    if reverse:
        # 有反向喜欢 => 形成互相喜欢
        like.status = "accepted"
        reverse.status = "accepted"
        like.updated_at = now
        reverse.updated_at = now

        # 3) Match 表去重插入
        exists = (
            db.query(Match)
            .filter(
                or_(
                    and_(Match.user_a == min(liker_id, likee_id), Match.user_b == max(liker_id, likee_id)),
                    and_(Match.user_a == max(liker_id, likee_id), Match.user_b == min(liker_id, likee_id))
                )
            )
            .first()
        )
        if not exists:
            db.add(Match(
                user_a=min(liker_id, likee_id),
                user_b=max(liker_id, likee_id),
                active=True,
                created_at=now
            ))
        matched = True

    db.commit()
    # --- Doris 镜像：UserLike（我->对方） ---
    MultiWriter.mirror_only(like)
    # --- Doris 镜像：UserLike（对方->我），若被更新 ---
    if reverse:
        MultiWriter.mirror_only(reverse)
    
    # --- Doris 镜像：Match（若本次形成了匹配）
    if matched:
        # 用唯一键把刚才的匹配行读出来（便于 mirror_only 使用对象拍平）
        mm = (
            db.query(Match)
              .filter(
                  or_(
                      and_(Match.user_a == min(liker_id, likee_id), Match.user_b == max(liker_id, likee_id)),
                      and_(Match.user_a == max(liker_id, likee_id), Match.user_b == min(liker_id, likee_id))
                  )
              )
              .order_by(desc(Match.created_at))
              .first()
        )
        if mm:
            MultiWriter.mirror_only(mm)

    # 给前端一个明确的动作提示，便于选择刷新哪些列表
    return {
        "ok": True,
        "status": "matched" if matched else "pending",
        "refresh": ["likes", "likedMe", "mutual"] if matched else ["likes", "likedMe"]
    }


# ========= 广告相关 =========
@router.get("/ads")
def list_ads(limit: int = 50, db: Session = Depends(get_db)):
    """
    广告列表，给前端弹窗随机抽
    """
    rows = (
        db.query(Advantage)
        .order_by(Advantage.time.desc())
        .limit(limit)
        .all()
    )
    # 直接返回 list，前端好处理
    return {
        "items": [
            {
                "id": r.id,
                "title": r.title,
                "desc": r.desc,
                "img": r.img,
                "destination": r.destination,
                "time": r.time,
            }
            for r in rows
        ]
    }


@router.get("/ads/{ad_id}")
def get_ad_detail(ad_id: int, db: Session = Depends(get_db)):
    """
    单条广告详情，给 /ad/:id 页面
    """
    ad = db.query(Advantage).filter(Advantage.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="广告不存在")
    return {
        "id": ad.id,
        "title": ad.title,
        "desc": ad.desc,
        "img": ad.img,
        "destination": ad.destination,
        "time": ad.time,
    }


# ========= 自定义匹配 =========
@router.get("/match/custom/{uid}")
def custom_match(
    uid: int,
    page: int = 1,
    page_size: int = 12,
    gender: Optional[str] = None,
    city: Optional[str] = None,
    hometown: Optional[str] = None,
    age_min: Optional[int] = None,
    age_max: Optional[int] = None,
    height_min: Optional[int] = None,
    height_max: Optional[int] = None,
    weight_min: Optional[int] = None,
    weight_max: Optional[int] = None,
    db: Session = Depends(get_db),
):
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 12

    # 读取用户自身的一些默认值
    me = db.query(UserAccount).filter(UserAccount.id == uid).first()
    if not me:
        raise HTTPException(404, "用户不存在")

    my_intent = (
        db.query(UserIntention)
        .filter(UserIntention.user_id == uid)
        .one_or_none()
    )

    # 如果前端没传任何筛选条件，则给一个“比较合理的默认值”
    if age_min is None and age_max is None:
        # 例如：取我意向里的一部分；如果没有，则 ±3 岁
        if my_intent and my_intent.preferred_age_min is not None:
            age_min = my_intent.preferred_age_min
        if my_intent and my_intent.preferred_age_max is not None:
            age_max = my_intent.preferred_age_max
        if age_min is None or age_max is None:
            # 退化到“以我实际年龄为中心 ±3 岁”
            my_age = _age_from_birth(me.birth_date)
            if my_age is not None:
                age_min = my_age - 3
                age_max = my_age + 3

    if height_min is None and height_max is None:
        if my_intent and my_intent.preferred_height_min is not None:
            height_min = my_intent.preferred_height_min
        if my_intent and my_intent.preferred_height_max is not None:
            height_max = my_intent.preferred_height_max


    # 候选基础集：只选活跃用户，排除自己，按更新时间排序
    q = (
        db.query(UserAccount)
        .filter(UserAccount.is_active == True)
        .filter(UserAccount.id != uid)
    )

    # 性别：默认按“异性”来
    if gender is None:
        if me.gender:
            g = str(me.gender).lower()
            if g in ("male", "m", "男"):
                gender = "female"
            elif g in ("female", "f", "女"):
                gender = "male"
    if gender:
        q = q.filter(func.lower(UserAccount.gender) == func.lower(gender))

    # 身高/体重区间
    if height_min is not None:
        q = (
            q.filter(UserAccount.height_cm != None)
            .filter(UserAccount.height_cm >= height_min)
        )
    if height_max is not None:
        q = (
            q.filter(UserAccount.height_cm != None)
            .filter(UserAccount.height_cm <= height_max)
        )
    if weight_min is not None:
        q = (
            q.filter(UserAccount.weight_kg != None)
            .filter(UserAccount.weight_kg >= weight_min)
        )
    if weight_max is not None:
        q = (
            q.filter(UserAccount.weight_kg != None)
            .filter(UserAccount.weight_kg <= weight_max)
        )

    # 城市/籍贯
    if city and str(city).strip():
        q = q.filter(UserAccount.city == city)
    if hometown and str(hometown).strip():
        q = q.filter(UserAccount.hometown == hometown)

    # 先抓一批候选，再在 Python 里按“年龄区间”兜底过滤
    # 这里取前 500 个候选做二次过滤，足够小页使用；数据量特别大时可以改成 AGE SQL 表达式
    candidates = q.order_by(desc(UserAccount.updated_at)).limit(500).all()

    def _ok_age(u: UserAccount) -> bool:
        if (age_min is None) and (age_max is None):  # 未限制
            return True
        a = _age_from_birth(u.birth_date)
        if a is None:
            return False
        if (age_min is not None) and (a < age_min):
            return False
        if (age_max is not None) and (a > age_max):
            return False
        return True

    # 一次性按年龄过滤后的全体候选
    filtered: List[UserAccount] = [u for u in candidates if _ok_age(u)]
    total_all = len(filtered)

    if not filtered:
        # 没人命中时，直接返回空结构，方便前端渲染
        return {
            "items": [],
            "liked_items": [],
            "page": page,
            "page_size": page_size,
            "total": 0,
            "total_all": 0,
            "liked_count": 0,
            "defaults": {
                "age_min": age_min,
                "age_max": age_max,
                "height_min": height_min,
                "height_max": height_max,
                "weight_min": weight_min,
                "weight_max": weight_max,
            },
        }

    # ====== 新增：按“我是否已经喜欢过 TA”拆分 ======
    cand_ids = [u.id for u in filtered]

    like_rows = (
        db.query(UserLike.likee_id, UserLike.status)
        .filter(
            UserLike.liker_id == uid,
            UserLike.likee_id.in_(cand_ids),
        )
        .all()
    )

    # 和训练脚本保持一致的“正向 like 状态”
    LIKE_POS_STATUSES = {
        "pending",
        "accepted",
        "agree",
        "ok",
        "mutual",
        "success",
        "liked",
        "like",
        "y",
        "yes",
        "1",
        "true",
    }
    LIKE_NEG_STATUSES = {"rejected", "blocked", "cancelled", "2", "no", "false"}

    def _like_status_ok(st) -> bool:
        s = str(st or "").strip().lower()
        if s in LIKE_NEG_STATUSES:
            return False
        return (s in LIKE_POS_STATUSES) or (
            s.isdigit() and (s == "1" or s == "2")
        )

    liked_id_set = {
        rid
        for (rid, st) in like_rows
        if _like_status_ok(st)
    }

    liked_users = [u for u in filtered if u.id in liked_id_set]
    unliked_users = [u for u in filtered if u.id not in liked_id_set]

    liked_count = len(liked_users)
    total_unliked = len(unliked_users)

    # 分页只针对“未喜欢”的人
    start = (page - 1) * page_size
    end = start + page_size
    page_users = unliked_users[start:end]

    # 补公开资料（显示 tagline/bio），一次性查 liked + 当前页未喜欢
    uids = [u.id for u in liked_users + page_users]
    profs = (
        db.query(UserProfilePublic)
        .filter(UserProfilePublic.user_id.in_(uids))
        .all()
        if uids
        else []
    )
    prof_map = {p.user_id: p for p in profs}

    def _pack_user_brief(u: UserAccount):
        prof = prof_map.get(u.id)
        age = _age_from_birth(u.birth_date)
        return {
            "id": u.id,
            "username": u.username,
            "nickname": u.nickname,
            "gender": u.gender,
            "city": u.city,
            "hometown": u.hometown,
            "age": age,  # 与现有接口一致的年龄口径
            "height_cm": u.height_cm,
            "weight_kg": u.weight_kg,
            "avatar_url": u.avatar_url,
            "tagline": prof.tagline if prof else "",
            "bio": prof.bio if prof else "",
        }

    liked_items = [_pack_user_brief(u) for u in liked_users]
    items = [_pack_user_brief(u) for u in page_users]

    return {
        # 下面这个 items 就是“未喜欢 + 分页”的列表，
        # 保持字段名不变，方便你原来的表格继续用
        "items": items,
        # 新增：已喜欢的完整列表（不分页）
        "liked_items": liked_items,
        # 分页仍然针对“未喜欢”的部分
        "page": page,
        "page_size": page_size,
        "total": total_unliked,  # 未喜欢的总数，给分页组件用
        # 统计用
        "total_all": total_all,  # 本次筛选命中总人数（已喜欢 + 未喜欢）
        "liked_count": liked_count,
        "defaults": {
            "age_min": age_min,
            "age_max": age_max,
            "height_min": height_min,
            "height_max": height_max,
            "weight_min": weight_min,
            "weight_max": weight_max,
        },
    }


# @router.post("/behavior/{uid}")
# async def log_behavior(uid: int, payload: dict):
#     record = UserBehaviorLog(
#         user_id=uid,
#         event_name=payload.get("event_name"),
#         event_time=datetime.utcnow(),
#         event_props=payload.get("event_props"),
#     )
#     await DorisQueue.add(record)
#     return {"ok": True}
