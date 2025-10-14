import os, csv, random, string, json, datetime, hashlib

# ----------------- 基础参数 -----------------
root = "/home/qssss/haozong/hunlian/master/data/user_file"
os.makedirs(root, exist_ok=True)
random.seed(42)

N_USERS = 2000
LIKES_PER_USER = 12
MEDIA_PER_USER = (1, 4)
QNA_PER_USER = (1, 3)
EVENTS_PER_MATCH = (0, 2)     # 每个匹配生成的事件数量范围
CHAT_MSGS_RANGE = (0, 5)      # 每个匹配生成的聊天条数范围

# ----------------- 工具函数 -----------------
def rand_choice(arr): return random.choice(arr)
def rand_bool(p=0.5): return 1 if random.random() < p else 0
def rand_int(a, b): return random.randint(a, b)
def rand_float(a, b): return random.uniform(a, b)
def slug(n=8): return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))
def now(): return datetime.datetime.utcnow()

def birthdate_for_age(age):
    year = now().year - age
    month = rand_int(1, 12)
    day = rand_int(1, 28)
    return datetime.date(year, month, day).isoformat()

# ----------------- 数据池 -----------------
cities = ["Beijing","Shanghai","Guangzhou","Shenzhen","Chengdu","Hangzhou","Wuhan","Nanjing","Xi'an","Suzhou","Tianjin"]
religions = [None,"none","buddhism","christian","islam","taoism"]
diets = ["normal","vegan","vegetarian","keto","low_carb","halal"]
interests_pool = ["movie","music","reading","basketball","football","yoga","hiking","boardgame","travel","photography","coding","cooking","gaming","running"]
travel_pool = ["mountain","sea","citywalk","museum","roadtrip","island","desert"]
q_pool = [
    ("最喜欢的周末安排？","和朋友聚会/运动/看电影"),
    ("你理想的旅行？","海岛躺平/徒步登山/城市漫游"),
    ("三年内的计划？","稳定发展/学习提升/结婚组建家庭"),
    ("你最拿手的菜？","番茄牛腩/咖喱鸡/意大利面"),
]
taglines = ["认真找对象","享受生活，热爱运动","爱阅读、爱旅行","慢热但真诚","有趣的灵魂在路上"]
bios = [
    "热爱运动与电影，期待遇见志同道合的你。",
    "程序员一枚，喜欢做饭和摄影，认真对待感情。",
    "外向开朗，周末citywalk，向往稳定的亲密关系。",
    "猫派，咖啡控，喜欢书店和博物馆。",
]

# ----------------- CSV Writer -----------------
def make_writer(name, headers):
    f = open(os.path.join(root, f"{name}.csv"), "w", newline="", encoding="utf-8")
    w = csv.writer(f)
    w.writerow(headers)
    return f, w

files, w = {}, {}
def open_table(name, headers):
    f, writer = make_writer(name, headers)
    files[name] = f
    w[name] = writer

# 打开表
open_table("user_account", ["id","username","nickname","phone","email","password_hash","gender","birth_date","height_cm","weight_kg","avatar_url","city","hometown","marital_status","has_children","accept_long_distance","is_active","is_verified","created_at","updated_at"])
open_table("user_intention", ["id","user_id","relationship_goal","preferred_age_min","preferred_age_max","preferred_height_min","preferred_height_max","preferred_cities","accept_long_distance","accept_divorce","accept_children","marriage_timeline","child_plan","family_view","religion","must_not_accept","bonus_points","created_at","updated_at"])
open_table("user_lifestyle", ["id","user_id","schedule","drinking","smoking","workout_freq","diet","pet_view","spending_view","saving_view","travel_pref","interests","personality","created_at","updated_at"])
open_table("user_certification", ["id","user_id","cert_type","status","doc_meta","reviewed_by","reviewed_at","created_at","updated_at"])
open_table("user_profile_public", ["id","user_id","tagline","bio","visibility_scope","completion_score","created_at","updated_at"])
open_table("user_media", ["id","user_id","media_type","url","thumb_url","audit_status","sort_order","created_at"])
open_table("user_qna", ["id","user_id","question","answer","visible","created_at"])
open_table("user_like", ["id","liker_id","likee_id","status","created_at","updated_at"])
open_table("user_match", ["id","user_a","user_b","active","created_at"])
open_table("user_event", ["id","user_id","counterpart_id","type","start_at","place","note","created_at"])
open_table("user_relation_stage", ["id","user_a_id","user_b_id","stage","updated_by","updated_at"])
open_table("user_activity_enroll", ["id","user_id","activity_id","status","group_no","liked_user_ids","review","created_at"])
open_table("user_subscription", ["id","user_id","plan_code","status","start_at","end_at","created_at"])
open_table("user_order", ["id","user_id","order_no","item_code","amount","pay_status","created_at"])
open_table("user_coupon", ["id","user_id","coupon_code","status","expire_at","created_at"])
open_table("user_privacy", ["id","user_id","visibility_scope","contact_sharing","org_block_enabled","phonebook_block_enabled","location_precision","data_export_requested","deletion_requested","created_at","updated_at"])
open_table("user_blacklist", ["id","user_id","blocked_user_id","reason","created_at"])
open_table("user_behavior_log", ["id","user_id","event_name","event_time","event_props","client_ip","device_id","ua"])

# ----------------- 生成数据 -----------------
user_ids = list(range(1, N_USERS + 1))
created0 = now() - datetime.timedelta(days=120)

# 1) user_account
genders = ["male","female"]
maritals = ["single","divorced","widowed"]
for uid in user_ids:
    username = f"user{uid:05d}"
    nickname = f"小{random.choice(['林','王','张','李','周','赵','钱','孙','吴'])}{rand_choice(['同学','同事','朋友','伙伴'])}"
    phone = f"1{rand_int(3000000000, 3999999999)}"
    email = f"{username}@example.com"
    pwd_hash = "$2b$12$examplehash"
    gender = rand_choice(genders)
    age = rand_int(22, 40)
    birth_date = birthdate_for_age(age)
    height = rand_int(150, 190)
    weight = round(rand_float(45, 95), 1)
    avatar = f"https://img.example.com/avatars/{uid}.jpg"
    city = rand_choice(cities)
    hometown = rand_choice(cities)
    marital_status = "single" if age < 30 else rand_choice(maritals)
    has_children = rand_bool(0.15 if marital_status != "single" else 0.05)
    accept_ld = rand_bool(0.6)
    is_active = 1
    is_verified = rand_bool(0.8)
    created_at = (created0 + datetime.timedelta(days=rand_int(0, 90))).strftime("%Y-%m-%d %H:%M:%S")
    updated_at = created_at
    w["user_account"].writerow([uid, username, nickname, phone, email, pwd_hash, gender, birth_date, height, weight, avatar, city, hometown, marital_status, has_children, accept_ld, is_active, is_verified, created_at, updated_at])

# 2) intention & 3) lifestyle & 5) profile_public & privacy
iid = lid = pid = prvid = 1
for uid in user_ids:
    # intention
    relationship_goal = rand_choice(["dating", "marriage"])
    p_age_min = rand_int(22, 28)
    p_age_max = p_age_min + rand_int(3, 10)
    p_h_min = rand_int(150, 165)
    p_h_max = p_h_min + rand_int(5, 20)
    pcities = random.sample(cities, k=rand_int(1, 3))
    accept_ld = rand_bool(0.6)
    accept_divorce = rand_bool(0.7)
    accept_children = rand_bool(0.6)
    mt = rand_choice([None, "1y", "2y", "flexible", "unknown"])
    cp = rand_choice([None, "want", "dont_want", "flexible", "unknown"])
    fv = rand_choice([None, "independent", "with_parents", "flexible"])
    rel = rand_choice(religions)
    must_not = random.sample(["smoking","heavy_drinking","no_children","different_religion","pet_reject"], k=rand_int(0, 2))
    bonus = random.sample(["sporty","reader","traveler","chef","financially_prudent","family_oriented"], k=rand_int(0, 3))
    ts = (created0 + datetime.timedelta(days=rand_int(0, 90))).strftime("%Y-%m-%d %H:%M:%S")
    w["user_intention"].writerow([iid, uid, relationship_goal, p_age_min, p_age_max, p_h_min, p_h_max, json.dumps(pcities, ensure_ascii=False), accept_ld, accept_divorce, accept_children, mt, cp, fv, rel, json.dumps(must_not, ensure_ascii=False), json.dumps(bonus, ensure_ascii=False), ts, ts])
    iid += 1

    # lifestyle
    schedule = rand_choice(["early","normal","late"])
    drinking = rand_choice(["never","occasionally","often"])
    smoking = rand_choice(["never","occasionally","often"])
    workout = rand_choice(["none","weekly","3+weekly","daily"])
    diet = rand_choice(diets)
    pet_view = rand_choice(["love","ok","allergic","reject"])
    spending = rand_choice(["frugal","balanced","luxury"])
    saving = rand_choice(["aggressive","balanced","conservative"])
    travel_pref = random.sample(travel_pool, k=rand_int(1, 3))
    interests = random.sample(interests_pool, k=rand_int(2, 6))
    mbti = rand_choice(["INTJ","ENTP","ISFJ","ENFP","ISTP","ESFJ", None])
    w["user_lifestyle"].writerow([lid, uid, schedule, drinking, smoking, workout, diet, pet_view, spending, saving, json.dumps(travel_pref), json.dumps(interests), mbti, ts, ts])
    lid += 1

    # profile public
    tagline = rand_choice(taglines)
    bio = rand_choice(bios)
    scope = rand_choice(["public","matched","matchmaker_only"])
    completion_score = 0
    w["user_profile_public"].writerow([pid, uid, tagline, bio, scope, completion_score, ts, ts])
    pid += 1

    # privacy
    w["user_privacy"].writerow([prvid, uid, scope, "double_confirm", 1, 1, "city", 0, 0, ts, ts])
    prvid += 1

# 4) certifications
cid = 1
for uid in user_ids:
    for ctype in ["identity","photo_liveness"]:
        status = rand_choice(["approved","approved","approved","pending"])
        doc = {"file":"redacted.png"}
        ts = (created0 + datetime.timedelta(days=rand_int(0, 90))).strftime("%Y-%m-%d %H:%M:%S")
        w["user_certification"].writerow([cid, uid, ctype, status, json.dumps(doc), None, None, None, ts, ts])
        cid += 1
    if rand_bool(0.5):
        ctype = rand_choice(["education","employment","income"])
        status = rand_choice(["approved","pending","rejected"])
        ts = (created0 + datetime.timedelta(days=rand_int(0, 90))).strftime("%Y-%m-%d %H:%M:%S")
        w["user_certification"].writerow([cid, uid, ctype, status, json.dumps({"meta":"ocr"}), None, None, None, ts, ts])
        cid += 1

# 5b) media
mid = 1
for uid in user_ids:
    k = rand_int(*MEDIA_PER_USER)
    for i in range(k):
        url = f"https://img.example.com/avatars/{uid}/{i+1}.jpg"
        thumb = url.replace(".jpg","_thumb.jpg")
        audit = rand_choice(["approved","pending","approved","approved"])
        sort = i
        ts = (created0 + datetime.timedelta(days=rand_int(0, 90))).strftime("%Y-%m-%d %H:%M:%S")
        w["user_media"].writerow([mid, uid, "photo", url, thumb, audit, sort, ts])
        mid += 1

# 5c) qna
qnid = 1
for uid in user_ids:
    k = rand_int(*QNA_PER_USER)
    choices = random.sample(q_pool, k=k)
    for q, a in choices:
        visible = rand_bool(0.9)
        ts = (created0 + datetime.timedelta(days=rand_int(0, 90))).strftime("%Y-%m-%d %H:%M:%S")
        w["user_qna"].writerow([qnid, uid, q, a, visible, ts])
        qnid += 1

# ----------------- 6) Likes & Matches（两趟，保证时序） -----------------
# 第 1 趟：采样所有 likes 与时间（不写表）
like_edges = set()                    # (u->v)
like_time = {}                        # (u,v) -> ts
for uid in user_ids:
    targets = set()
    while len(targets) < LIKES_PER_USER:
        t = rand_int(1, N_USERS)
        if t != uid:
            targets.add(t)
    for t in targets:
        edge = (uid, t)
        like_edges.add(edge)
        ts = (created0 + datetime.timedelta(days=rand_int(0, 90), minutes=rand_int(0, 60*24))).replace(microsecond=0)
        like_time[edge] = ts

# 计算互相喜欢的 pair（ua<ub）与两侧 like 的时间
mutual_pairs = set()
pair_to_likes_ts = {}
for (u, v) in like_edges:
    if (v, u) in like_edges:
        ua, ub = sorted([u, v])
        if (ua, ub) not in mutual_pairs:
            mutual_pairs.add((ua, ub))
            pair_to_likes_ts[(ua, ub)] = (like_time[(ua, ub)], like_time[(ub, ua)])

# 第 2 趟：写 user_like（状态正确）+ user_match（稳定 match_id）
like_id = 1
match_id = 1
pair_to_match_id = {}
match_participants = {}  # match_id -> (ua, ub)

for (u, v) in sorted(like_edges):
    accepted = (min(u, v), max(u, v)) in mutual_pairs and ((u, v) in like_edges and (v, u) in like_edges)
    status = "accepted" if accepted else "pending"
    ts = like_time[(u, v)].strftime("%Y-%m-%d %H:%M:%S")
    w["user_like"].writerow([like_id, u, v, status, ts, ts])
    like_id += 1

for (ua, ub) in sorted(mutual_pairs):
    ts_a, ts_b = pair_to_likes_ts[(ua, ub)]
    match_ts = max(ts_a, ts_b) + datetime.timedelta(minutes=rand_int(1, 60))
    match_ts_str = match_ts.strftime("%Y-%m-%d %H:%M:%S")
    pair_to_match_id[(ua, ub)] = match_id
    match_participants[match_id] = (ua, ub, match_ts)  # 带上 match_ts
    w["user_match"].writerow([match_id, ua, ub, 1, match_ts_str])
    match_id += 1


# ----------------- 6) Events & Relation Stage（必须有线下见面才可进入阶段） -----------------
evt_id = 1
stage_id = 1
STAGE_AFTER_DATE_PROB = 0.6  # 出现过线下 date 后，有 60% 概率写入关系阶段；你可改成 1.0=必写/0.0=不写

for mid in sorted(match_participants.keys()):
    ua, ub, match_ts = match_participants[mid]  # ua < ub
    base_ts = match_ts + datetime.timedelta(minutes=5)

    # 事件（视频/线下），时间顺序递增
    ev_cnt = rand_int(*EVENTS_PER_MATCH)
    prev_ts = base_ts
    last_event_ts = None
    last_date_ts = None   # 仅记录线下见面的最后事件时间

    for _ in range(ev_cnt):
        initiator = rand_choice([ua, ub])
        counterpart = ub if initiator == ua else ua
        tp = rand_choice(["video", "date"])
        evt_ts = prev_ts + datetime.timedelta(minutes=rand_int(10, 24*60))
        place = None if tp == "video" else rand_choice(["星巴克","Manner Coffee","万达广场","博物馆","商场中庭"])
        note = "初次见面" if tp == "date" else "视频速配"
        created_at = evt_ts - datetime.timedelta(minutes=rand_int(1, 60))

        w["user_event"].writerow([
            evt_id, initiator, counterpart, tp,
            evt_ts.strftime("%Y-%m-%d %H:%M:%S"),
            place, note,
            created_at.strftime("%Y-%m-%d %H:%M:%S")
        ])
        evt_id += 1

        prev_ts = evt_ts
        last_event_ts = evt_ts
        if tp == "date":
            last_date_ts = evt_ts

    # === 只有出现“线下见面（date）”后，才可能写入关系阶段 ===
    if last_date_ts is not None and rand_bool(STAGE_AFTER_DATE_PROB):
        stage = rand_choice(["met", "dating", "exclusive", "off_the_shelf"])
        who = rand_choice([ua, ub])  # 操作人
        stage_ts = last_date_ts + datetime.timedelta(minutes=rand_int(5, 180))
        w["user_relation_stage"].writerow([
            stage_id,
            ua,  # user_a_id（保证 ua < ub）
            ub,  # user_b_id
            stage,
            who,  # updated_by
            stage_ts.strftime("%Y-%m-%d %H:%M:%S")
        ])
        stage_id += 1



# ----------------- 7) 活动报名 -----------------
enroll_id = 1
for uid in random.sample(user_ids, k=int(N_USERS * 0.3)):
    activity_id = rand_int(1, 10)
    status = rand_choice(["applied","approved","rejected","checked_in","absent"])
    group_no = rand_choice([None, "A", "B", "C"])
    liked = json.dumps(random.sample(user_ids, k=rand_int(0, 3)))
    review = rand_choice([None, "活动很棒", "组织有序", "氛围不错"])
    ts = (created0 + datetime.timedelta(days=rand_int(0, 90))).strftime("%Y-%m-%d %H:%M:%S")
    w["user_activity_enroll"].writerow([enroll_id, uid, activity_id, status, group_no, liked, review, ts])
    enroll_id += 1

# ----------------- 8) 订阅 / 订单 / 优惠券 -----------------
sub_id = 1; ord_id = 1; cpn_id = 1
for uid in user_ids:
    if rand_bool(0.35):
        plan = rand_choice(["vip","vip_plus"])
        start = (created0 + datetime.timedelta(days=rand_int(0, 90)))
        end = start + datetime.timedelta(days=rand_int(15, 90))
        ts = start.strftime("%Y-%m-%d %H:%M:%S")
        w["user_subscription"].writerow([sub_id, uid, plan, "active", ts, end.strftime("%Y-%m-%d %H:%M:%S"), ts])
        sub_id += 1
    if rand_bool(0.4):
        item = rand_choice(["exposure_boost","priority_match","matchmaker_1v1"])
        amt = {"exposure_boost":19.9, "priority_match":49.0, "matchmaker_1v1":199.0}[item]
        order_no = f"ORD{uid:05d}{slug(6)}"
        pay_status = rand_choice(["paid","paid","unpaid","refunding","refunded"])
        ts = (created0 + datetime.timedelta(days=rand_int(0, 90))).strftime("%Y-%m-%d %H:%M:%S")
        w["user_order"].writerow([ord_id, uid, order_no, item, amt, pay_status, ts])
        ord_id += 1
    if rand_bool(0.2):
        code = f"CPN{slug(6).upper()}"
        status = rand_choice(["unused","used","expired"])
        exp = (now() + datetime.timedelta(days=rand_int(7, 90))).strftime("%Y-%m-%d %H:%M:%S")
        ts = (created0 + datetime.timedelta(days=rand_int(0, 90))).strftime("%Y-%m-%d %H:%M:%S")
        w["user_coupon"].writerow([cpn_id, uid, code, status, exp, ts])
        cpn_id += 1

# ----------------- 9) 黑名单 -----------------
bl_id = 1
for uid in random.sample(user_ids, k=int(N_USERS * 0.05)):
    blocked = rand_int(1, N_USERS)
    if blocked == uid: 
        continue
    ts = (created0 + datetime.timedelta(days=rand_int(0, 90))).strftime("%Y-%m-%d %H:%M:%S")
    w["user_blacklist"].writerow([bl_id, uid, blocked, rand_choice(["骚扰信息","价值观不合","虚假资料"]), ts])
    bl_id += 1

# ----------------- 10) 行为日志 -----------------
beh_id = 1
events = ["view_card","open_profile","like","reject","open_chat","send_msg","video_book","date_create","report"]
for uid in user_ids:
    k = rand_int(5, 12)
    for _ in range(k):
        ev = rand_choice(events)
        ts = (created0 + datetime.timedelta(days=rand_int(0, 90), minutes=rand_int(0, 60*24))).strftime("%Y-%m-%d %H:%M:%S")
        props = {"card_id": rand_int(1, N_USERS), "stay_ms": rand_int(1000, 20000)}
        w["user_behavior_log"].writerow([beh_id, uid, ev, ts, json.dumps(props, ensure_ascii=False), "127.0.0.1", slug(12), "Mozilla/5.0"])
        beh_id += 1

# ----------------- 收尾 -----------------
for f in files.values():
    f.close()
