import datetime
from sqlalchemy import Column, Integer, String,text, Text, Date, SmallInteger, DECIMAL, Enum, Boolean, DateTime, ForeignKey, JSON # type: ignore
from ..database import Base
import enum
import datetime

class UserVerification(Base):
    __tablename__ = "user_verification"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_account.id"), nullable=False, index=True)
    status = Column(SmallInteger, nullable=False, server_default=text("0"))  # 0待审/1通过/2拒绝/3复审中
    reason = Column(String(255))
    reviewer_id = Column(Integer)
    recheck_reviewer_id = Column(Integer)
    ocr_result = Column(JSON)
    meta = Column(JSON)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, nullable=False,
                        server_default=text("CURRENT_TIMESTAMP"),
                        onupdate=text("CURRENT_TIMESTAMP"))


class MediaReview(Base):
    __tablename__ = "media_review"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_account.id"), nullable=False, index=True)
    media_id = Column(Integer, nullable=False)
    media_type = Column(SmallInteger, nullable=False)  # 0头像/1图片/2视频
    status = Column(SmallInteger, nullable=False, server_default=text("0"))  # 0待审/1过/2拒
    labels = Column(JSON)
    reviewer_id = Column(Integer)
    evidence = Column(JSON)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, nullable=False,
                        server_default=text("CURRENT_TIMESTAMP"),
                        onupdate=text("CURRENT_TIMESTAMP"))


class QcSampling(Base):
    __tablename__ = "qc_sampling"
    id = Column(Integer, primary_key=True, autoincrement=True)
    review_id = Column(Integer, ForeignKey("media_review.id"), nullable=False, index=True)
    checker_id = Column(Integer, nullable=False)
    result = Column(SmallInteger, nullable=False)  # 1合规/0不合规
    remark = Column(String(255))
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class DeviceFingerprint(Base):
    __tablename__ = "device_fingerprint"
    device_id = Column(String(64), primary_key=True)
    user_id = Column(Integer, index=True)
    attrs = Column(JSON)
    risk_score = Column(DECIMAL(5, 2), nullable=False, server_default=text("0.00"))
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, nullable=False,
                        server_default=text("CURRENT_TIMESTAMP"),
                        onupdate=text("CURRENT_TIMESTAMP"))


class BehaviorEvent(Base):
    __tablename__ = "behavior_event"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_account.id"), nullable=False, index=True)
    device_id = Column(String(64))
    ip = Column(String(64))  # SQL原为 VARBINARY(16)，存储时转字符串或INET格式
    event_type = Column(SmallInteger, nullable=False)  # 0复制/1外链/2涉黄/3诈骗
    details = Column(JSON)
    occurred_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class RiskAssessment(Base):
    __tablename__ = "risk_assessment"
    id = Column(Integer, primary_key=True, autoincrement=True)
    target_type = Column(SmallInteger, nullable=False)  # 0用户/1设备/2IP
    target_id = Column(String(64), nullable=False)
    score = Column(DECIMAL(5, 2), nullable=False, server_default=text("0.00"))
    action = Column(SmallInteger, nullable=False, server_default=text("0"))  # 0无/1限流/2限聊/3封禁
    expire_at = Column(DateTime)
    reason = Column(String(255))
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class Event(Base):
    __tablename__ = "event"
    event_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(128), nullable=False)
    budget_cents = Column(Integer, nullable=False, server_default=text("0"))
    venue = Column(String(256))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    gender_ratio_target = Column(JSON)
    status = Column(SmallInteger, nullable=False, server_default=text("0"))
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class TicketType(Base):
    __tablename__ = "ticket_type"
    ticket_type_id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("event.event_id"), nullable=False, index=True)
    name = Column(String(64), nullable=False)
    price_cents = Column(Integer, nullable=False, server_default=text("0"))
    quota = Column(Integer, nullable=False, server_default=text("0"))
    gender_limit = Column(SmallInteger)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class TicketOrder(Base):
    __tablename__ = "ticket_order"
    order_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_account.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("event.event_id"), nullable=False)
    ticket_type_id = Column(Integer, ForeignKey("ticket_type.ticket_type_id"),
                            nullable=False)
    amount_cents = Column(Integer, nullable=False, server_default=text("0"))
    status = Column(SmallInteger, nullable=False, server_default=text("0")) # 0待支付/1已支付/2退款中/3已退款/4已核销
    paid_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class Checkin(Base):
    __tablename__ = "checkin"
    checkin_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("ticket_order.order_id"),
                      nullable=False, unique=True)
    verified_by = Column(Integer)
    checkin_time = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class VoteHeartbeat(Base):
    __tablename__ = "vote_heartbeat"
    vote_id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("event.event_id"), nullable=False)
    from_user_id = Column(Integer, nullable=False)
    to_user_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
