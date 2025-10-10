import os, csv, datetime
from backend.app.database import engine, Base, SessionLocal
from backend.app.models.user import (
    UserAccount, UserLike, Match, UserProfilePublic, 
    UserLifestyle, UserIntention, UserMedia, UserQna
)
# from app.models.platform import 

Base.metadata.create_all(bind=engine)
db = SessionLocal()

DATA_ROOTS = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "user_file")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "platform"))
]

def find(path, name):
    p = os.path.join(path, name)
    return p if os.path.exists(p) else None

def import_user_account(root):
    fn = find(root, "user_account.csv")
    if not fn: return 0
    with open(fn, encoding="utf-8") as f:
        r = csv.DictReader(f)
        cnt = 0
        for row in r:
            if db.query(UserAccount).filter(UserAccount.id==int(row["id"])).first():
                continue
            obj = UserAccount(
                id=int(row["id"]),
                username=row["username"],
                nickname=row.get("nickname"),
                phone=row.get("phone"),
                email=row.get("email"),
                password_hash=row.get("password_hash") or "hash",
                gender=row.get("gender") or None,
                city=row.get("city") or None
            )
            db.add(obj); cnt += 1
        db.commit()
    return cnt

def main():
    total = 0
    for root in DATA_ROOTS:
        if os.path.isdir(root):
            total += import_user_account(root)
            total += import_profile(root)
            total += import_lifestyle(root)
            total += import_intention(root)
            total += import_media(root)
            total += import_qna(root)
    print(f"Imported rows: {total}")

if __name__ == "__main__":
    main()

def _read_csv(fn):
    import csv
    with open(fn, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def import_profile(root):
    fn = find(root, "user_profile_public.csv")
    if not fn: return 0
    rows = _read_csv(fn); cnt=0
    for r in rows:
        if db.query(UserProfilePublic).filter(UserProfilePublic.id==int(r["id"])).first(): continue
        obj = UserProfilePublic(
            id=int(r["id"]), user_id=int(r["user_id"]), tagline=r.get("tagline"),
            bio=r.get("bio"), visibility_scope=r.get("visibility_scope") or "public",
            completion_score=int(r.get("completion_score") or 0)
        )
        db.add(obj); cnt+=1
    db.commit(); return cnt

def import_lifestyle(root):
    fn = find(root, "user_lifestyle.csv")
    if not fn: return 0
    rows = _read_csv(fn); cnt=0
    for r in rows:
        if db.query(UserLifestyle).filter(UserLifestyle.id==int(r["id"])).first(): continue
        obj = UserLifestyle(
            id=int(r["id"]), user_id=int(r["user_id"]), schedule=r.get("schedule"),
            drinking=r.get("drinking"), smoking=r.get("smoking"), workout_freq=r.get("workout_freq"),
            diet=r.get("diet"), pet_view=r.get("pet_view"), spending_view=r.get("spending_view"),
            saving_view=r.get("saving_view"), travel_pref=None, interests=None, personality=r.get("personality")
        )
        db.add(obj); cnt+=1
    db.commit(); return cnt

def import_intention(root):
    fn = find(root, "user_intention.csv")
    if not fn: return 0
    rows = _read_csv(fn); cnt=0
    for r in rows:
        if db.query(UserIntention).filter(UserIntention.id==int(r["id"])).first(): continue
        obj = UserIntention(
            id=int(r["id"]), user_id=int(r["user_id"]), relationship_goal=r.get("relationship_goal") or "dating",
            preferred_age_min=int(r.get("preferred_age_min") or 0) or None, preferred_age_max=int(r.get("preferred_age_max") or 0) or None,
            preferred_height_min=int(r.get("preferred_height_min") or 0) or None, preferred_height_max=int(r.get("preferred_height_max") or 0) or None,
            preferred_cities=None, accept_long_distance=(r.get("accept_long_distance")=='1'),
            accept_divorce=(r.get("accept_divorce")=='1'), accept_children=(r.get("accept_children")=='1'),
            marriage_timeline=r.get("marriage_timeline"), child_plan=r.get("child_plan"), family_view=r.get("family_view"),
            religion=r.get("religion"), must_not_accept=None, bonus_points=None
        )
        db.add(obj); cnt+=1
    db.commit(); return cnt

def import_media(root):
    fn = find(root, "user_media.csv")
    if not fn: return 0
    rows = _read_csv(fn); cnt=0
    for r in rows:
        if db.query(UserMedia).filter(UserMedia.id==int(r["id"])).first(): continue
        obj = UserMedia(
            id=int(r["id"]), user_id=int(r["user_id"]), media_type=r.get("media_type"),
            url=r.get("url"), thumb_url=r.get("thumb_url"), audit_status=r.get("audit_status"),
            sort_order=int(r.get("sort_order") or 0)
        )
        db.add(obj); cnt+=1
    db.commit(); return cnt

def import_qna(root):
    fn = find(root, "user_qna.csv")
    if not fn: return 0
    rows = _read_csv(fn); cnt=0
    for r in rows:
        if db.query(UserQna).filter(UserQna.id==int(r["id"])).first(): continue
        obj = UserQna(
            id=int(r["id"]), user_id=int(r["user_id"]), question=r.get("question"),
            answer=r.get("answer"), visible=(r.get("visible") in ['1','true','True'])
        )
        db.add(obj); cnt+=1
    db.commit(); return cnt
