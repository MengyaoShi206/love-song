# backend/app/api/user.py
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
                              UserSubscription, UserLike, Match
                            )
from datetime import date, datetime
from app.services.recommend_service import RecommendService


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
        "avatar_url": 6, "phone": 4, "email": 4, "city": 3, "hometown": 2,
        "gender": 3, "birth_date": 3, "height_cm": 3, "weight_kg": 2,
        "nickname": 2, "marital_status": 2, "has_children": 1, "accept_long_distance": 1,
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
    if bio_len >= 120:
        B += 14
    elif bio_len >= 60:
        B += 11
    elif bio_len >= 20:
        B += 7
    B = min(B, 20)
    detail["B"] = B
    score += B

    # ===== C. 择偶意向 20 =====
    # 注意：此处不再对 accept_long_distance 二次计分（避免和 A 重复）
    C_weights = {
        "relationship_goal": 3,
        "preferred_age_min": 2, "preferred_age_max": 2,
        "preferred_height_min": 2, "preferred_height_max": 2,
        "preferred_cities": 2,
        "accept_divorce": 1, "accept_children": 1,
        "marriage_timeline": 1, "child_plan": 1,
        "family_view": 1, "religion": 1,
        "must_not_accept": 1, "bonus_points": 1,
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
        "schedule": 2, "workout_freq": 2, "diet": 2, "personality": 2,
        "drinking": 1, "smoking": 1, "pet_view": 1, "spending_view": 1,
        "saving_view": 1, "travel_pref": 1, "interests": 1,
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
def update_profile(uid: int, payload: Dict[str, Any], db: Session = Depends(lambda: SessionLocal())):
    """
    更新用户资料 + 重新计算完善度
    """
    u = db.query(UserAccount).filter(UserAccount.id == uid).first()
    if not u:
        raise HTTPException(404, "用户不存在")

    # --- 唯一性检查 ---
    if payload.get("email") and payload["email"] != u.email:
        if db.query(UserAccount).filter(UserAccount.email == payload["email"]).first():
            raise HTTPException(400, "Email 已被占用")
    if payload.get("phone") and payload["phone"] != u.phone:
        if db.query(UserAccount).filter(UserAccount.phone == payload["phone"]).first():
            raise HTTPException(400, "手机号已被占用")
    
    # --- 更新账户基础字段 ---
    for f in ("nickname", "city", "phone", "email", "avatar_url"):
        val = payload.get(f)
        if val is not None:
            setattr(u, f, val)
    u.updated_at = datetime.utcnow()

    # --- 更新公开资料 ---
    prof = _get_or_create_profile(uid, db)
    if "tagline" in payload: prof.tagline = payload["tagline"]
    if "bio" in payload: prof.bio = payload["bio"]

    if "user_qna" in payload:
        qnas = payload["user_qna"]
        db.query(UserQna).filter(UserQna.user_id == uid).delete()
        for q in qnas:
            db.add(UserQna(
                user_id=uid,
                question=q.get("question"),
                answer=q.get("answer"),
                visible=True,
                created_at=datetime.utcnow(),
            ))
    # --- 重新计算完善度 ---
    payload_for_score = _build_payload(uid, db)
    score, detail = _compute_completion_score(payload_for_score)
    prof.completion_score = score
    prof.updated_at = datetime.utcnow()

    db.commit()
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
def list_liked_me(uid: int, page: int = 1, page_size: int = 1, db: Session = Depends(get_db)):
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

    total = len(from_ids)
    start, end = (page - 1) * page_size, (page - 1) * page_size + page_size
    page_ids = from_ids[start:end]

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
def recommend_users(uid: int, limit: int = 20, page: int = 1, min_completion: int = 0, db: Session = Depends(get_db)):
    """
    为您推荐：系统内聚算法（无外部引擎依赖）。
    - min_completion: 候选完善度门槛（0~100）
    """
    res = recommend_service.recommend_for_user(db, uid, limit=limit, min_completion=min_completion)
    return res


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

    # 给前端一个明确的动作提示，便于选择刷新哪些列表
    return {
        "ok": True,
        "status": "matched" if matched else "pending",
        "refresh": ["likes", "likedMe", "mutual"] if matched else ["likes", "likedMe"]
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
