# -*- coding: utf-8 -*-
import os
import csv
import json
import datetime as dt
from decimal import Decimal

from backend.app.database import engine, Base, SessionLocal
from backend.app.models.user import (
    UserAccount, UserIntention, UserLifestyle, UserCertification,
    UserProfilePublic, UserMedia, UserQna, UserLike, Match,
    UserEvent, UserRelationStage, UserActivityEnroll, UserSubscription,
    UserOrder, UserCoupon, UserPrivacy, UserBlacklist, UserBehaviorLog,
)
from backend.app.models.platform import (
    UserVerification, MediaReview, QcSampling, DeviceFingerprint,
    BehaviorEvent, RiskAssessment, Event, TicketType, TicketOrder,
    Checkin, VoteHeartbeat,
)

# --------------------基础--------------------------
Base.metadata.create_all(bind=engine)
db = SessionLocal()

DATA_ROOTS = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "user_file")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "platform"))
]

def to_find(path, name):
    p = os.path.join(path, name)
    return p if os.path.exists(p) else None

def to_read_csv(fn):
    if not fn or not os.path.exists(fn):
        return []
    with open(fn, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def to_int(v, default=None):
    if v is None or v == "": return default
    try:
        return int(v)
    except Exception:
        return default

def to_bool(v, default=False):
    if isinstance(v, bool): return v
    if v is None: return default
    s = str(v).strip().lower()
    if s in ("1", "true", "t", "yes", "y"): return True
    if s in ("0", "false", "f", "no", "n"): return False
    return default

def to_json(v):
    if v is None or v == "": return None
    try:
        return json.loads(v)
    except Exception:
        return None

def to_dt(v):
    if v is None or v == "": return None
    # 常见格式兜底
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(v, fmt)
        except Exception:
            pass
    # ISO 尝试
    try:
        return dt.datetime.fromisoformat(v.replace("Z","").replace("T"," "))
    except Exception:
        return None

def to_dec(v, default=Decimal("0.00")):
    if v is None or v == "": return default
    try:
        return Decimal(str(v))
    except Exception:
        return default


# --------------------user的导入--------------------------
def import_user_account(root):
    rows = to_read_csv(to_find(root, "user_account.csv"))
    cnt = 0
    for r in rows:
        if db.get(UserAccount, int(r["id"])): continue
        db.add(UserAccount(
            id=to_int(r["id"]),
            username=r.get("username"),
            nickname=r.get("nickname"),
            phone=r.get("phone"),
            email=r.get("email"),
            password_hash=r.get("password_hash") or "hash",
            gender=(r.get("gender") or None),
            birth_date=to_dt(r.get("birth_date")).date() if to_dt(r.get("birth_date")) else None,
            height_cm=to_int(r.get("height_cm")),
            weight_kg=to_dec(r.get("weight_kg")),
            avatar_url=r.get("avatar_url"),
            city=r.get("city"),
            hometown=r.get("hometown"),
            marital_status=(r.get("marital_status") or "single"),
            has_children=to_bool(r.get("has_children")),
            accept_long_distance=to_bool(r.get("accept_long_distance"), True),
            is_active=to_bool(r.get("is_active"), True),
            is_verified=to_bool(r.get("is_verified"), False),
            created_at=to_dt(r.get("created_at")) or dt.datetime.utcnow(),
            updated_at=to_dt(r.get("updated_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    db.commit()
    return cnt

def import_userto_intention(root):
    rows = to_read_csv(to_find(root, "userto_intention.csv"))
    cnt = 0
    for r in rows:
        if db.get(UserIntention, to_int(r["id"])): continue
        db.add(UserIntention(
            id=to_int(r["id"]),
            user_id=to_int(r["user_id"]),
            relationship_goal=(r.get("relationship_goal") or "dating"),
            preferred_age_min=to_int(r.get("preferred_age_min")),
            preferred_age_max=to_int(r.get("preferred_age_max")),
            preferred_height_min=to_int(r.get("preferred_height_min")),
            preferred_height_max=to_int(r.get("preferred_height_max")),
            preferred_cities=to_json(r.get("preferred_cities")),
            accept_long_distance=to_bool(r.get("accept_long_distance"), True),
            accept_divorce=to_bool(r.get("accept_divorce"), True),
            accept_children=to_bool(r.get("accept_children"), True),
            marriage_timeline=r.get("marriage_timeline"),
            child_plan=r.get("child_plan"),
            family_view=r.get("family_view"),
            religion=r.get("religion"),
            must_not_accept=to_json(r.get("must_not_accept")),
            bonus_points=to_json(r.get("bonus_points")),
            created_at=to_dt(r.get("created_at")) or dt.datetime.utcnow(),
            updated_at=to_dt(r.get("updated_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    db.commit()
    return cnt

def import_user_lifestyle(root):
    rows = to_read_csv(to_find(root, "user_lifestyle.csv"))
    cnt = 0
    for r in rows:
        if db.get(UserLifestyle, to_int(r["id"])): continue
        db.add(UserLifestyle(
            id=to_int(r["id"]), 
            user_id=to_int(r["user_id"]),
            schedule=r.get("schedule"),
            drinking=r.get("drinking"),
            smoking=r.get("smoking"),
            workout_freq=r.get("workout_freq"),
            diet=r.get("diet"),
            pet_view=r.get("pet_view"),
            spending_view=r.get("spending_view"),
            saving_view=r.get("saving_view"),
            travel_pref=to_json(r.get("travel_pref")),
            interests=to_json(r.get("interests")),
            personality=r.get("personality"),
            created_at=to_dt(r.get("created_at")) or dt.datetime.utcnow(),
            updated_at=to_dt(r.get("updated_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    db.commit()
    return cnt


def import_user_certification(root):
    rows = to_read_csv(to_find(root, "user_certification.csv"))
    cnt = 0
    for r in rows:
        if db.get(UserCertification, to_int(r["id"])): continue
        db.add(UserCertification(
            id=to_int(r["id"]), 
            user_id=to_int(r["user_id"]),
            cert_type=r.get("cert_type"),
            status=r.get("status") or "pending",
            doc_meta=to_json(r.get("doc_meta")),
            reviewed_by=to_int(r.get("reviewed_by")),
            reviewed_at=to_dt(r.get("reviewed_at")),
            created_at=to_dt(r.get("created_at")) or dt.datetime.utcnow(),
            updated_at=to_dt(r.get("updated_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    db.commit()
    return cnt


def import_user_profile_public(root):
    rows = to_read_csv(to_find(root, "user_profile_public.csv"))
    cnt = 0
    for r in rows:
        if db.get(UserProfilePublic, to_int(r["id"])): continue
        db.add(UserProfilePublic(
            id=to_int(r["id"]), 
            user_id=to_int(r["user_id"]),
            tagline=r.get("tagline"), bio=r.get("bio"),
            visibility_scope=r.get("visibility_scope") or "public",
            completion_score=to_int(r.get("completion_score"), 0) or 0,
            created_at=to_dt(r.get("created_at")) or dt.datetime.utcnow(),
            updated_at=to_dt(r.get("updated_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    db.commit()
    return cnt

def import_user_media(root):
    rows = to_read_csv(to_find(root, "user_media.csv"))
    cnt = 0
    for r in rows:
        if db.get(UserMedia, to_int(r["id"])): continue
        db.add(UserMedia(
            id=to_int(r["id"]), 
            user_id=to_int(r["user_id"]),
            media_type=r.get("media_type"),
            url=r.get("url"), 
            thumb_url=r.get("thumb_url"),
            audit_status=r.get("audit_status") or "pending",
            sort_order=to_int(r.get("sort_order"), 0) or 0,
            created_at=to_dt(r.get("created_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    db.commit()
    return cnt

def import_user_qna(root):
    rows = to_read_csv(to_find(root, "user_qna.csv"))
    cnt = 0
    for r in rows:
        if db.get(UserQna, to_int(r["id"])): continue
        db.add(UserQna(
            id=to_int(r["id"]), 
            user_id=to_int(r["user_id"]),
            question=r.get("question"), answer=r.get("answer"),
            visible=to_bool(r.get("visible"), True),
            created_at=to_dt(r.get("created_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    db.commit()
    return cnt

def import_user_like_and_match(root):
    cnt = 0
    # likes
    rows = to_read_csv(to_find(root, "user_like.csv"))
    for r in rows:
        if db.get(UserLike, to_int(r["id"])): continue
        db.add(UserLike(
            id=to_int(r["id"]),
            liker_id=to_int(r["liker_id"]),
            likee_id=to_int(r["likee_id"]),
            status=r.get("status") or "pending",
            created_at=to_dt(r.get("created_at")) or dt.datetime.utcnow(),
            updated_at=to_dt(r.get("updated_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    # matches
    rows = to_read_csv(to_find(root, "user_match.csv"))
    for r in rows:
        if db.get(Match, to_int(r["id"])): continue
        db.add(Match(
            id=to_int(r["id"]),
            user_a=to_int(r["user_a"]),
            user_b=to_int(r["user_b"]),
            active=to_bool(r.get("active"), True),
            created_at=to_dt(r.get("created_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    db.commit()
    return cnt

def import_user_event_and_stage(root):
    cnt = 0
    rows = to_read_csv(to_find(root, "user_event.csv"))
    for r in rows:
        if db.get(UserEvent, to_int(r["id"])): continue
        db.add(UserEvent(
            id=to_int(r["id"]), 
            user_id=to_int(r["user_id"]),
            counterpart_id=to_int(r["counterpart_id"]),
            type=r.get("type"),
            start_at=to_dt(r.get("start_at")),
            place=r.get("place"), note=r.get("note"),
            created_at=to_dt(r.get("created_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    rows = to_read_csv(to_find(root, "user_relation_stage.csv"))
    for r in rows:
        if db.get(UserRelationStage, to_int(r["id"])): continue
        db.add(UserRelationStage(
            id=to_int(r["id"]), 
            user_a_id=to_int(r["user_a_id"]),
            user_b_id=to_int(r["user_b_id"]),
            stage=r.get("stage") or "met",
            updated_by=to_int(r.get("updated_by")),
            updated_at=to_dt(r.get("updated_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    db.commit()
    return cnt

def import_user_activity(root):
    rows = to_read_csv(to_find(root, "user_activity_enroll.csv"))
    cnt = 0
    for r in rows:
        if db.get(UserActivityEnroll, to_int(r["id"])): continue
        db.add(UserActivityEnroll(
            id=to_int(r["id"]), 
            user_id=to_int(r["user_id"]),
            activity_id=to_int(r["activity_id"]),
            status=r.get("status") or "applied",
            group_no=r.get("group_no"),
            liked_user_ids=to_json(r.get("liked_user_ids")),
            review=r.get("review"),
            created_at=to_dt(r.get("created_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    db.commit()
    return cnt

def import_user_subscription_order_coupon(root):
    cnt = 0
    # subscription
    rows = to_read_csv(to_find(root, "user_subscription.csv"))
    for r in rows:
        if db.get(UserSubscription, to_int(r["id"])): continue
        db.add(UserSubscription(
            id=to_int(r["id"]), 
            user_id=to_int(r["user_id"]),
            plan_code=r.get("plan_code"),
            status=r.get("status") or "active",
            start_at=to_dt(r.get("start_at")) or dt.datetime.utcnow(),
            end_at=to_dt(r.get("end_at")),
            created_at=to_dt(r.get("created_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    # order
    rows = to_read_csv(to_find(root, "user_order.csv"))
    for r in rows:
        if db.get(UserOrder, to_int(r["id"])): continue
        db.add(UserOrder(
            id=to_int(r["id"]), 
            user_id=to_int(r["user_id"]),
            order_no=r.get("order_no"), 
            item_code=r.get("item_code"),
            amount=to_dec(r.get("amount")),
            pay_status=r.get("pay_status") or "unpaid",
            created_at=to_dt(r.get("created_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    # coupon
    rows = to_read_csv(to_find(root, "user_coupon.csv"))
    for r in rows:
        if db.get(UserCoupon, to_int(r["id"])): continue
        db.add(UserCoupon(
            id=to_int(r["id"]), 
            user_id=to_int(r["user_id"]),
            coupon_code=r.get("coupon_code"),
            status=r.get("status") or "unused",
            expire_at=to_dt(r.get("expire_at")),
            created_at=to_dt(r.get("created_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    db.commit()
    return cnt

def import_user_privacy_blacklist(root):
    cnt = 0
    # privacy
    rows = to_read_csv(to_find(root, "user_privacy.csv"))
    for r in rows:
        if db.get(UserPrivacy, to_int(r["id"])): continue
        db.add(UserPrivacy(
            id=to_int(r["id"]), 
            user_id=to_int(r["user_id"]),
            visibility_scope=r.get("visibility_scope") or "public",
            contact_sharing=r.get("contact_sharing") or "double_confirm",
            org_block_enabled=to_bool(r.get("org_block_enabled"), True),
            phonebook_block_enabled=to_bool(r.get("phonebook_block_enabled"), True),
            location_precision=r.get("location_precision") or "city",
            data_export_requested=to_bool(r.get("data_export_requested"), False),
            deletion_requested=to_bool(r.get("deletion_requested"), False),
            created_at=to_dt(r.get("created_at")) or dt.datetime.utcnow(),
            updated_at=to_dt(r.get("updated_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    # blacklist
    rows = to_read_csv(to_find(root, "user_blacklist.csv"))
    for r in rows:
        if db.get(UserBlacklist, to_int(r["id"])): continue
        db.add(UserBlacklist(
            id=to_int(r["id"]), user_id=to_int(r["user_id"]),
            blocked_user_id=to_int(r["blocked_user_id"]),
            reason=r.get("reason"),
            created_at=to_dt(r.get("created_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    db.commit()
    return cnt


def import_user_behavior(root):
    cnt = 0
    rows = to_read_csv(to_find(root, "user_behavior_log.csv"))
    for r in rows:
        if db.get(UserBehaviorLog, to_int(r["id"])): continue
        db.add(UserBehaviorLog(
            id=to_int(r["id"]), 
            user_id=to_int(r["user_id"]),
            event_name=r.get("event_name"),
            event_time=to_dt(r.get("event_time")) or dt.datetime.utcnow(),
            event_props=to_json(r.get("event_props")),
            client_ip=r.get("client_ip"),
            device_id=r.get("device_id"),
            ua=r.get("ua"),
        ))
        cnt += 1
    db.commit()
    return cnt


# --------------------plotform的导入--------------------------
def import_platform_user_verification(root):
    cnt = 0
    rows = to_read_csv(to_find(root, "user_verification.csv"))
    for r in rows:
        if db.get(UserVerification, to_int(r["id"])): continue
        db.add(UserVerification(
            id=to_int(r["id"]), 
            user_id=to_int(r["user_id"]),
            status=to_int(r.get("status"), 0) or 0,
            reason=r.get("reason"),
            reviewer_id=to_int(r.get("reviewer_id")),
            recheck_reviewer_id=to_int(r.get("recheck_reviewer_id")),
            ocr_result=to_json(r.get("ocr_result")),
            meta=to_json(r.get("meta")),
            created_at=to_dt(r.get("created_at")) or dt.datetime.utcnow(),
            updated_at=to_dt(r.get("updated_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    db.commit()
    return cnt

def import_platform_media_review(root):
    cnt = 0
    rows = to_read_csv(to_find(root, "media_review.csv"))
    for r in rows:
        if db.get(MediaReview, to_int(r["id"])): continue
        db.add(MediaReview(
            id=to_int(r["id"]), 
            user_id=to_int(r["user_id"]),
            media_id=to_int(r["media_id"]),
            media_type=to_int(r.get("media_type"), 1) or 1,
            status=to_int(r.get("status"), 0) or 0,
            labels=to_json(r.get("labels")),
            reviewer_id=to_int(r.get("reviewer_id")),
            evidence=to_json(r.get("evidence")),
            created_at=to_dt(r.get("created_at")) or dt.datetime.utcnow(),
            updated_at=to_dt(r.get("updated_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    db.commit()
    return cnt

def import_platform_qc(root):
    rows = to_read_csv(to_find(root, "qc_sampling.csv"))
    cnt = 0
    for r in rows:
        if db.get(QcSampling, to_int(r["id"])): continue
        db.add(QcSampling(
            id=to_int(r["id"]), review_id=to_int(r["review_id"]),
            checker_id=to_int(r["checker_id"]),
            result=to_int(r.get("result"), 1) or 1,
            remark=r.get("remark"),
            created_at=to_dt(r.get("created_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    db.commit()
    return cnt

def import_platform_risk(root):
    cnt = 0
    # device_fingerprint
    rows = to_read_csv(to_find(root, "device_fingerprint.csv"))
    for r in rows:
        if db.get(DeviceFingerprint, r.get("device_id")): continue
        db.add(DeviceFingerprint(
            device_id=r.get("device_id"),
            user_id=to_int(r.get("user_id")),
            attrs=to_json(r.get("attrs")),
            risk_score=to_dec(r.get("risk_score"), Decimal("0.00")),
            created_at=to_dt(r.get("created_at")) or dt.datetime.utcnow(),
            updated_at=to_dt(r.get("updated_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    # behavior_event
    rows = to_read_csv(to_find(root, "behavior_event.csv"))
    for r in rows:
        if db.get(BehaviorEvent, to_int(r["id"])): continue
        db.add(BehaviorEvent(
            id=to_int(r["id"]), user_id=to_int(r["user_id"]),
            device_id=r.get("device_id"),
            ip=r.get("ip"),
            event_type=to_int(r.get("event_type"), 0) or 0,
            details=to_json(r.get("details")),
            occurred_at=to_dt(r.get("occurred_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    # risk_assessment
    rows = to_read_csv(to_find(root, "risk_assessment.csv"))
    for r in rows:
        if db.get(RiskAssessment, to_int(r["id"])): continue
        db.add(RiskAssessment(
            id=to_int(r["id"]),
            target_type=to_int(r.get("target_type"), 0) or 0,
            target_id=r.get("target_id"),
            score=to_dec(r.get("score"), Decimal("0.00")),
            action=to_int(r.get("action"), 0) or 0,
            expire_at=to_dt(r.get("expire_at")),
            reason=r.get("reason"),
            created_at=to_dt(r.get("created_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    db.commit()
    return cnt

def import_platform_events_and_tickets(root):
    cnt = 0
    # event
    rows = to_read_csv(to_find(root, "event.csv"))
    for r in rows:
        if db.get(Event, to_int(r["event_id"])): continue
        db.add(Event(
            event_id=to_int(r["event_id"]),
            title=r.get("title"),
            budget_cents=to_int(r.get("budget_cents"), 0) or 0,
            venue=r.get("venue"),
            start_time=to_dt(r.get("start_time")),
            end_time=to_dt(r.get("end_time")),
            gender_ratio_target=to_json(r.get("gender_ratio_target")),
            status=to_int(r.get("status"), 0) or 0,
            created_at=to_dt(r.get("created_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    db.commit()

    # ticket_type
    rows = to_read_csv(to_find(root, "ticket_type.csv"))
    for r in rows:
        if db.get(TicketType, to_int(r["ticket_type_id"])): continue
        db.add(TicketType(
            ticket_type_id=to_int(r["ticket_type_id"]),
            event_id=to_int(r["event_id"]),
            name=r.get("name"),
            price_cents=to_int(r.get("price_cents"), 0) or 0,
            quota=to_int(r.get("quota"), 0) or 0,
            gender_limit=to_int(r.get("gender_limit")),
            created_at=to_dt(r.get("created_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    db.commit()

    # ticket_order
    rows = to_read_csv(to_find(root, "ticket_order.csv"))
    for r in rows:
        if db.get(TicketOrder, to_int(r["order_id"])): continue
        db.add(TicketOrder(
            order_id=to_int(r["order_id"]),
            user_id=to_int(r["user_id"]),
            event_id=to_int(r["event_id"]),
            ticket_type_id=to_int(r["ticket_type_id"]),
            amount_cents=to_int(r.get("amount_cents"), 0) or 0,
            status=to_int(r.get("status"), 0) or 0,
            paid_at=to_dt(r.get("paid_at")),
            created_at=to_dt(r.get("created_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    db.commit()

    # checkin
    rows = to_read_csv(to_find(root, "checkin.csv"))
    for r in rows:
        if db.get(Checkin, to_int(r["checkin_id"])): continue
        db.add(Checkin(
            checkin_id=to_int(r["checkin_id"]),
            order_id=to_int(r["order_id"]),
            verified_by=to_int(r.get("verified_by")),
            checkin_time=to_dt(r.get("checkin_time")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    db.commit()

    # vote_heartbeat
    rows = to_read_csv(to_find(root, "vote_heartbeat.csv"))
    for r in rows:
        if db.get(VoteHeartbeat, to_int(r["vote_id"])): continue
        db.add(VoteHeartbeat(
            vote_id=to_int(r["vote_id"]),
            event_id=to_int(r["event_id"]),
            from_user_id=to_int(r["from_user_id"]),
            to_user_id=to_int(r["to_user_id"]),
            created_at=to_dt(r.get("created_at")) or dt.datetime.utcnow(),
        ))
        cnt += 1
    db.commit()
    return cnt


def main():
    total = 0
    for root in DATA_ROOTS:
        if os.path.isdir(root):
            total += import_user_account(root)
            total += import_userto_intention(root)
            total += import_user_lifestyle(root)
            total += import_user_certification(root)
            total += import_user_profile_public(root)
            total += import_user_media(root)
            total += import_user_qna(root)
            total += import_user_like_and_match(root)
            total += import_user_event_and_stage(root)
            total += import_user_activity(root)
            total += import_user_subscription_order_coupon(root)
            total += import_user_privacy_blacklist(root)
            total += import_user_behavior(root)


            total += import_platform_user_verification(root)
            total += import_platform_media_review(root)
            total += import_platform_qc(root)
            total += import_platform_risk(root)
            total += import_platform_events_and_tickets(root)
    print(f"Imported rows: {total}")

if __name__ == "__main__":
    main()

