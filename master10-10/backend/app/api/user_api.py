# backend/app/api/user.py
from fastapi import APIRouter, HTTPException, Depends # type: ignore
from sqlalchemy.orm import Session # type: ignore
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
import re
from sqlalchemy import func # type: ignore

from app.database import SessionLocal
from app.models.user import UserAccount, UserProfilePublic, UserMedia, UserQna, UserLifestyle, UserIntention


router = APIRouter()

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
    ua = UserAccount(
        username=payload.username,
        password_hash=payload.password_hash,  # 演示：直接入库；生产请存加盐哈希
        nickname=payload.nickname,
        phone=payload.phone,
        email=payload.email,
        gender=payload.gender,
        city=payload.city,
        avatar_url=payload.avatar_url,
    )
    db.add(ua)
    db.commit()
    db.refresh(ua)

    # 创建公开资料占位
    upp = UserProfilePublic(
        user_id=ua.id,
        tagline="",
        bio="",
        visibility_scope="public",
        completion_score=0,
    )
    db.add(upp)
    db.commit()

    return ua


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


@router.get("/display/{uid}")
def display(uid: int, db: Session = Depends(get_db)):
    u = db.query(UserAccount).filter(UserAccount.id == uid).first()
    if not u:
        raise HTTPException(404, "用户不存在")
    media_count = db.query(func.count(UserMedia.id)).filter(
        UserMedia.user_id == uid, UserMedia.audit_status == "approved"
    ).scalar() or 0
    qna_count = db.query(func.count(UserQna.id)).filter(
        UserQna.user_id == uid, UserQna.visible == True
    ).scalar() or 0
    life = db.query(UserLifestyle).filter(UserLifestyle.user_id == uid).first()
    intent = db.query(UserIntention).filter(UserIntention.user_id == uid).first()
    prof = db.query(UserProfilePublic).filter(UserProfilePublic.user_id == uid).first()
    return {
        "user": {
            "id": u.id, "username": u.username, "nickname": u.nickname,
            "email": u.email, "phone": u.phone, "city": u.city, "avatar_url": u.avatar_url
        },
        "profile": {"tagline": prof.tagline if prof else "", "bio": prof.bio if prof else ""},
        "media_count": media_count,
        "qna_count": qna_count,
        "lifestyle": life.__dict__ if life else None,
        "intention": intent.__dict__ if intent else None
    }