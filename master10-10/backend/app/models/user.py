from sqlalchemy import Column, Integer, String,text, Text, Date, SmallInteger, DECIMAL, Enum, Boolean, DateTime, ForeignKey, JSON # type: ignore
from sqlalchemy.orm import relationship # type: ignore
from ..database import Base
import enum
import datetime

class Gender(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"

class Marital(str, enum.Enum):
    single = "single"
    divorced = "divorced"
    widowed = "widowed"

class UserAccount(Base):
    __tablename__ = "user_account"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(32), unique=True, nullable=False, index=True)
    nickname = Column(String(64))
    phone = Column(String(20), unique=True)
    email = Column(String(128), unique=True)
    password_hash = Column(String(255), nullable=False)
    gender = Column(Enum(Gender), nullable=True)
    birth_date = Column(Date, nullable=True)
    height_cm = Column(SmallInteger, nullable=True)
    weight_kg = Column(DECIMAL(5,1), nullable=True)
    avatar_url = Column(String(512), nullable=True)
    city = Column(String(64), index=True)
    hometown = Column(String(64))
    marital_status = Column(Enum(Marital), nullable=False, default=Marital.single)
    has_children = Column(Boolean, default=False, nullable=False)
    accept_long_distance = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

class UserIntention(Base):
    __tablename__ = "user_intention"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_account.id"), nullable=False, index=True)
    relationship_goal = Column(Enum("dating", "marriage", name="relationship_goal_enum"),
                               nullable=False, default="dating")
    preferred_age_min = Column(SmallInteger)
    preferred_age_max = Column(SmallInteger)
    preferred_height_min = Column(SmallInteger)
    preferred_height_max = Column(SmallInteger)
    preferred_cities = Column(JSON)
    accept_long_distance = Column(Boolean, nullable=False, default=True)
    accept_divorce = Column(Boolean, nullable=False, default=True)
    accept_children = Column(Boolean, nullable=False, default=True)
    marriage_timeline = Column(Enum("1y", "2y", "flexible", "unknown", name="marriage_timeline_enum"))
    child_plan = Column(Enum("want", "dont_want", "flexible", "unknown", name="child_plan_enum"))
    family_view = Column(Enum("independent", "with_parents", "flexible", name="family_view_enum"))
    religion = Column(String(32))
    must_not_accept = Column(JSON)
    bonus_points = Column(JSON)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

class UserLifestyle(Base):
    __tablename__ = "user_lifestyle"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_account.id"),nullable=False, index=True)
    schedule = Column(Enum("early", "normal", "late", name="schedule_enum"))
    drinking = Column(Enum("never", "occasionally", "often", name="drinking_enum"))
    smoking = Column(Enum("never", "occasionally", "often", name="smoking_enum"))
    workout_freq = Column(Enum("none", "weekly", "3+weekly", "daily", name="workout_freq_enum"))
    diet = Column(String(64))
    pet_view = Column(Enum("love", "ok", "allergic", "reject", name="pet_view_enum"))
    spending_view = Column(Enum("frugal", "balanced", "luxury", name="spending_view_enum"))
    saving_view = Column(Enum("aggressive", "balanced", "conservative", name="saving_view_enum"))
    travel_pref = Column(JSON)
    interests = Column(JSON)
    personality = Column(String(16))
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

class UserCertification(Base):
    __tablename__ = "user_certification"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer,ForeignKey("user_account.id"),nullable=False, index=True)
    cert_type = Column(
        Enum(
            "identity", "education", "employment", "income", "asset",
            "photo_liveness", "video_liveness",
            name="cert_type_enum"
        ),
        nullable=False
    )
    status = Column(
        Enum("pending", "approved", "rejected", "expired", name="cert_status_enum"),
        nullable=False,
        server_default="pending"
    )
    doc_meta = Column(JSON)
    reviewed_by = Column(Integer)
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

class UserProfilePublic(Base):
    __tablename__ = "user_profile_public"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer,ForeignKey("user_account.id"),nullable=False,index=True)
    tagline = Column(String(120))
    bio = Column(Text)
    visibility_scope = Column(
        Enum("public", "matched", "matchmaker_only", name="visibility_scope_enum"),
        nullable=False,server_default="public"
    )
    completion_score = Column(SmallInteger, nullable=False, server_default=text("0"))
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

class UserMedia(Base):
    __tablename__ = "user_media"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_account.id"), nullable=False,index=True)
    media_type = Column(Enum("photo", "video", name="media_type_enum"), nullable=False)
    url = Column(String(512), nullable=False)
    thumb_url = Column(String(512))
    audit_status = Column(Enum("pending", "approved", "rejected", name="audit_status_enum"), nullable=False,server_default="pending")
    sort_order = Column(Integer, nullable=False, server_default=text("0"))
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

class UserQna(Base):
    __tablename__ = "user_qna"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer,ForeignKey("user_account.id"),nullable=False,index=True)
    question = Column(String(200), nullable=False)
    answer = Column(String(500), nullable=False)
    visible = Column(Boolean,nullable=False,server_default=text("1") )
    created_at = Column(DateTime,nullable=False,server_default=text("CURRENT_TIMESTAMP"))

class UserLike(Base):
    __tablename__ = "user_like"
    id = Column(Integer, primary_key=True, autoincrement=True)
    liker_id = Column(Integer,ForeignKey("user_account.id"),nullable=False)
    likee_id = Column(Integer,ForeignKey("user_account.id"),nullable=False)
    status = Column(
        Enum("pending", "accepted", "rejected", "expired", name="like_status_enum"),
        nullable=False,server_default="pending"
    )
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"),
                        onupdate=text("CURRENT_TIMESTAMP"))

class Match(Base):
    __tablename__ = "user_match"
    id = Column(Integer, primary_key=True)
    user_a = Column(Integer, ForeignKey("user_account.id"), nullable=False)
    user_b = Column(Integer, ForeignKey("user_account.id"), nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

class UserEvent(Base):
    __tablename__ = "user_event"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_account.id"), nullable=False)
    counterpart_id = Column(Integer, ForeignKey("user_account.id"), nullable=False)
    type = Column(Enum("video", "date", name="event_type_enum"), nullable=False)
    start_at = Column(DateTime, nullable=False)
    place = Column(String(200))
    note = Column(String(500))
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

class UserRelationStage(Base):
    __tablename__ = "user_relation_stage"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_a_id = Column(Integer, ForeignKey("user_account.id"), nullable=False)
    user_b_id = Column(Integer, ForeignKey("user_account.id"), nullable=False)
    stage = Column(
        Enum("met", "dating", "exclusive", "off_the_shelf", name="relation_stage_enum"),
        nullable=False, server_default="met"
    )
    updated_by = Column(Integer, ForeignKey("user_account.id"), nullable=False)
    updated_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class UserActivityEnroll(Base):
    __tablename__ = "user_activity_enroll"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_account.id"), nullable=False)
    activity_id = Column(Integer, nullable=False)
    status = Column(
        Enum("applied", "approved", "rejected", "checked_in", "absent",
             name="activity_enroll_status_enum"),
        nullable=False,
        server_default="applied"
    )
    group_no = Column(String(16))
    liked_user_ids = Column(JSON)
    review = Column(String(500))
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class UserSubscription(Base):
    __tablename__ = "user_subscription"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_account.id"), nullable=False)
    plan_code = Column(String(32), nullable=False)
    status = Column(
        Enum("active", "expired", "paused", name="subscription_status_enum"),
        nullable=False,
        server_default="active"
    )
    start_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP")
    )
    end_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class UserOrder(Base):
    __tablename__ = "user_order"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_account.id"), nullable=False)
    order_no = Column(String(64), nullable=False) 
    item_code = Column(String(32), nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False, server_default=text("0.00"))
    pay_status = Column(
        Enum("unpaid", "paid", "refunding", "refunded", name="order_pay_status_enum"),
        nullable=False,
        server_default="unpaid"
    )
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class UserCoupon(Base):
    __tablename__ = "user_coupon"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_account.id"), nullable=False)
    coupon_code = Column(String(32), nullable=False)
    status = Column(
        Enum("unused", "used", "expired", name="coupon_status_enum"),
        nullable=False,
        server_default="unused"
    )
    expire_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class UserPrivacy(Base):
    __tablename__ = "user_privacy"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_account.id"), nullable=False)
    visibility_scope = Column(
        Enum("public", "matched", "matchmaker_only", name="privacy_visibility_enum"),
        nullable=False,
        server_default="public"
    )
    contact_sharing = Column(
        Enum("double_confirm", "never", "always", name="privacy_contact_enum"),
        nullable=False,
        server_default="double_confirm"
    )
    org_block_enabled = Column(Boolean, nullable=False, server_default=text("1"))
    phonebook_block_enabled = Column(Boolean, nullable=False, server_default=text("1") )
    location_precision = Column(
        Enum("city", "district", "off", name="privacy_location_precision_enum"),
        nullable=False,
        server_default="city"
    )
    data_export_requested = Column(Boolean, nullable=False, server_default=text("0"))
    deletion_requested = Column(Boolean, nullable=False, server_default=text("0"))
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP")
    )


class UserBlacklist(Base):
    __tablename__ = "user_blacklist"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_account.id"), nullable=False)
    blocked_user_id = Column(Integer, ForeignKey("user_account.id"), nullable=False)
    reason = Column(String(200))
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class UserBehaviorLog(Base):
    __tablename__ = "user_behavior_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_account.id"), nullable=False)
    event_name = Column(String(64), nullable=False)
    event_time = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    event_props = Column(JSON)
    client_ip = Column(String(64))
    device_id = Column(String(64))
    ua = Column(String(255))

