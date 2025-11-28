# -*- coding: utf-8 -*-
"""
平台中台 - 基于 user_* 数据衍生生成（审核直接针对 user 数据）
- 输入：/home/qssss/haozong/hunlian/data/user_file 下现有 CSV（你之前的脚本生成的那些 user_* 表）
- 输出：/home/qssss/haozong/hunlian/data/platform_mid 下的各平台中台 CSV（字段顺序与之前 CREATE TABLE 对齐）
- 风格：与 user 脚本类似，固定入参路径、无命令行
"""

import os, csv, json, random, string, datetime

# ----------------- 基础参数 -----------------
INPUT_ROOT  = "/home/qssss/haozong/hunlian/data/user_file"
OUTPUT_ROOT = "/home/qssss/haozong/hunlian/data/platform"
os.makedirs(OUTPUT_ROOT, exist_ok=True)
random.seed(42)

# 可调规模（不改变 user 行数，只影响平台“派生/补全”部分的密度）
N_EVENTS = 120            # 新建活动数量（与 user 活动报名无强耦合）
N_TICKETS = None          # 留空=按活动/票种推导
N_POSTS = 2000            # 平台内容贴数量
N_TICKETS_SAMPLE = 60     # 每个活动平均订单数
N_EXPERIMENTS = 20

def rand_choice(arr): return random.choice(arr)
def rand_bool(p=0.5): return 1 if random.random() < p else 0
def rand_int(a, b): return random.randint(a, b)
def rand_float(a, b): return random.uniform(a, b)
def slug(n=8): return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))
def now(): return datetime.datetime.utcnow()
def ts(dt): return dt.strftime("%Y-%m-%d %H:%M:%S")
def now_minus(days=365):
    dt = now() - datetime.timedelta(days=rand_int(0, days), seconds=rand_int(0, 86400))
    return dt.replace(microsecond=0)

def open_writer(name, headers):
    f = open(os.path.join(OUTPUT_ROOT, f"{name}.csv"), "w", newline="", encoding="utf-8")
    w = csv.writer(f)
    w.writerow(headers)
    return f, w

files, W = {}, {}
def open_table(name, headers):
    f, w = open_writer(name, headers); files[name]=f; W[name]=w

# ----------------- 打开平台中台各表 -----------------
# 用户审核中心（严格基于 user_*）
open_table("user_verification", ["id","user_id","status","reason","reviewer_id","recheck_reviewer_id","ocr_result","meta","created_at","updated_at"])
open_table("media_review", ["id","user_id","media_id","media_type","status","labels","reviewer_id","evidence","created_at","updated_at"])
open_table("qc_sampling", ["id","review_id","checker_id","result","remark","created_at"])

# 风控中心（部分参考 user 行为日志）
open_table("device_fingerprint", ["device_id","user_id","attrs","risk_score","created_at","updated_at"])
open_table("behavior_event", ["id","user_id","device_id","ip","event_type","details","occurred_at"])
open_table("risk_assessment", ["id","target_type","target_id","score","action","expire_at","reason","created_at"])

# 活动与票务（用户参与者来自 user_account）
open_table("event", ["event_id","title","budget_cents","venue","start_time","end_time","gender_ratio_target","status","created_at"])
open_table("ticket_type", ["ticket_type_id","event_id","name","price_cents","quota","gender_limit","created_at"])
open_table("ticket_order", ["order_id","user_id","event_id","ticket_type_id","amount_cents","status","paid_at","created_at"])
open_table("checkin", ["checkin_id","order_id","verified_by","checkin_time"])
open_table("vote_heartbeat", ["vote_id","event_id","from_user_id","to_user_id","created_at"])

# ----------------- 读取 user_* 数据 -----------------
def read_csv(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows

UA = read_csv(os.path.join(INPUT_ROOT, "user_account.csv"))
UM = read_csv(os.path.join(INPUT_ROOT, "user_media.csv"))
UC = read_csv(os.path.join(INPUT_ROOT, "user_certification.csv"))
UQ = read_csv(os.path.join(INPUT_ROOT, "user_qna.csv"))
UL = read_csv(os.path.join(INPUT_ROOT, "user_like.csv"))
UMatch = read_csv(os.path.join(INPUT_ROOT, "user_match.csv"))
UE = read_csv(os.path.join(INPUT_ROOT, "user_event.csv"))
UBL = read_csv(os.path.join(INPUT_ROOT, "user_blacklist.csv"))
USB = read_csv(os.path.join(INPUT_ROOT, "user_subscription.csv"))
UO = read_csv(os.path.join(INPUT_ROOT, "user_order.csv"))
UBLLOG = read_csv(os.path.join(INPUT_ROOT, "user_behavior_log.csv"))

user_ids = [int(x["id"]) for x in UA] if UA else []
created0 = now() - datetime.timedelta(days=120)

# 索引辅助
media_by_user = {}
for row in UM:
    uid = int(row["user_id"]); media_by_user.setdefault(uid, []).append(row)

cert_by_user = {}
for row in UC:
    uid = int(row["user_id"]); cert_by_user.setdefault(uid, []).append(row)

likes_out = {}      # liker_id -> set(likee_id)
likes_in  = {}      # likee_id -> set(liker_id)
for row in UL:
    a = int(row["liker_id"]); b = int(row["likee_id"])
    likes_out.setdefault(a,set()).add(b)
    likes_in.setdefault(b,set()).add(a)

mutual_pairs = set()
for a, outs in likes_out.items():
    for b in outs:
        if a!=b and b in likes_out and a in likes_out[b]:
            ua,ub = sorted([a,b])
            mutual_pairs.add((ua,ub))

# ----------------- 1) 审核中心：严格来源于 user_* -----------------
# user_verification 来自 user_certification（identity/…）聚合
def map_cert_status(st):
    if st is None: return 0
    st = str(st).lower()
    if "approved" in st: return 1
    if "rejected" in st: return 2
    if "pending" in st: return 0
    return 0

uv_id = 1
for uid in user_ids:
    certs = cert_by_user.get(uid, [])
    if not certs:
        # 无证件：记为待审
        status = 0; reason = ""
        ocr = {}
    else:
        # 聚合该用户多个认证：优先级 rejected > pending > approved（体现风控谨慎）
        mapped = [map_cert_status(c.get("status")) for c in certs]
        if 2 in mapped: status = 2; reason="证件不通过"
        elif 0 in mapped: status=0; reason="审核中"
        else: status=1; reason=""
        # 尝试抽 identity 的 doc_meta 作为 ocr_result
        ocr = {}
        for c in certs:
            if c.get("cert_type")=="identity":
                try:
                    ocr = json.loads(c.get("doc_meta") or "{}")
                except Exception:
                    ocr = {}
                break
    t1 = now_minus()
    W["user_verification"].writerow([
        uv_id, uid, status, reason,
        rand_int(100000,100500),
        rand_int(100000,100500) if status in (2,) else "",
        json.dumps(ocr, ensure_ascii=False),
        json.dumps({"src":"user_certification"}, ensure_ascii=False),
        ts(t1), ts(t1 + datetime.timedelta(minutes=rand_int(1,600)))
    ])
    uv_id += 1

# media_review 来自 user_media.audit_status
mr_id = 1; qc_id = 1
audit_map = {"approved":1, "pending":0, "rejected":2}
for uid, medias in media_by_user.items():
    for m in medias:
        st = audit_map.get((m.get("audit_status") or "").lower(), 0)
        W["media_review"].writerow([
            mr_id, uid, int(m["id"]), 1, st,
            json.dumps({"labels":["face","portrait"],"score":round(random.uniform(0.8,0.99),3)}, ensure_ascii=False),
            rand_int(100000,100500) if rand_bool(0.7) else "",
            json.dumps({"src":"user_media","url": m["url"]}, ensure_ascii=False),
            m.get("created_at") or ts(now_minus()),
            ts(now_minus())
        ])
        # 20% 抽检
        if rand_bool(0.2):
            W["qc_sampling"].writerow([
                qc_id, mr_id, rand_int(200000,200500),
                1 if rand_bool(0.95) else 0,
                "" if rand_bool(0.8) else "边界样本复核",
                ts(now_minus())
            ])
            qc_id += 1
        mr_id += 1

# ----------------- 2) 风控中心（参考 user_behavior_log 派生） -----------------
# 行为日志 -> 抽样转 behavior_event；生成部分设备/IP 画像
device_ids = []
df_count = max(500, int(0.3*len(user_ids)))
for uid in random.sample(user_ids, k=df_count):
    for _ in range(rand_int(1,2)):
        did = f"dev_{uid}_{slug(6)}"; device_ids.append(did)
        W["device_fingerprint"].writerow([
            did, uid,
            json.dumps({"os": rand_choice(["iOS","Android"]), "ver": f"{rand_int(10,17)}.{rand_int(0,9)}"}, ensure_ascii=False),
            round(rand_float(0,100),2),
            ts(now_minus()), ts(now_minus())
        ])

def rand_ip():
    return ".".join(str(rand_int(1,254)) for _ in range(4))

# behavior_event 映射：简单把行为名分桶
be_id = 1
event_map = {
    "send_msg":0,      # 复制类
    "open_chat":0,
    "report":3,        # 欺诈/举报作为高风险
    "video_book":1,    # 外链/视频预约归到1
    "date_create":1,
}
for row in UBLLOG[: max(20000, len(UBLLOG)) ]:
    uid = int(row["user_id"])
    etype = event_map.get(row["event_name"], rand_choice([0,1,2,3]))
    ip = row.get("client_ip") or rand_ip()
    W["behavior_event"].writerow([
        be_id, uid,
        rand_choice(device_ids) if device_ids and rand_bool(0.6) else "",
        ip, etype,
        json.dumps({"props": row.get("event_props")}, ensure_ascii=False),
        row.get("event_time") or ts(now_minus())
    ]); be_id += 1

# 风险评估/证据（与互相黑名单/举报倾向随机）
ra_id = 1; rev_id = 1
for _ in range(int(0.1*len(user_ids))):
    ttype = rand_choice([0,1,2])
    target = str(rand_choice(user_ids)) if ttype==0 else (rand_choice(device_ids) if ttype==1 else rand_ip())
    W["risk_assessment"].writerow([
        ra_id, ttype, target,
        round(rand_float(0,100),2),
        rand_choice([0,1,2,3,0]),
        ts(now_minus()) if rand_bool(0.5) else "",
        rand_choice(["批量复制","导流外链","色情嫌疑","欺诈嫌疑","设备异常"]),
        ts(now_minus())
    ])
    ra_id += 1

# ----------------- 3) 活动与票务（参与者来自 user） -----------------
venues = ["国贸中心A座","高新万达广场","滨江咖啡厅","环球影城","天府广场","科技园路演厅"]
event_id = 1; tt_id = 1; order_id = 1; checkin_id = 1; vote_id = 1
for _ in range(N_EVENTS):
    st = now_minus(); et = st + datetime.timedelta(hours=rand_int(2,6))
    W["event"].writerow([event_id, f"线下活动{event_id}", rand_int(10000,200000), rand_choice(venues), ts(st), ts(et), json.dumps({"F":0.5,"M":0.5}, ensure_ascii=False), rand_choice([0,1,2,3,4]), ts(now_minus())])
    for name in ["早鸟","普通","双人"]:
        W["ticket_type"].writerow([tt_id, event_id, name, rand_int(1000,9900), rand_int(20,200), rand_choice([None,0,1,2]), ts(now_minus())]); tt_id += 1
    event_id += 1

all_tt = list(range(1, tt_id))
for _ in range(N_EVENTS * N_TICKETS_SAMPLE):
    tt = rand_choice(all_tt); eid = (tt-1)//3 + 1; uid = rand_choice(user_ids)
    status = rand_choice([0,1,2,3,4,1,1,4])
    paid_at = ts(now_minus()) if status in (1,2,3,4) else ""
    W["ticket_order"].writerow([order_id, uid, eid, tt, rand_int(1000,9900), status, paid_at, ts(now_minus())])
    if status==4 and rand_bool(0.9):
        W["checkin"].writerow([checkin_id, order_id, rand_int(700000,700500), ts(now_minus())]); checkin_id+=1
    if rand_bool(0.15):
        to_user = rand_choice(user_ids)
        if to_user != uid:
            W["vote_heartbeat"].writerow([vote_id, eid, uid, to_user, ts(now_minus())]); vote_id+=1
    order_id += 1

# ----------------- 收尾与装载脚本 -----------------
for f in files.values():
    f.close()

with open(os.path.join(OUTPUT_ROOT, "load_data.sql"), "w", encoding="utf-8") as f:
    for name in W.keys():
        f.write(
            f"LOAD DATA LOCAL INFILE '{name}.csv' INTO TABLE {name} "
            "FIELDS TERMINATED BY ',' ENCLOSED BY '\"' "
            "LINES TERMINATED BY '\\n' IGNORE 1 LINES;\n"
        )

print("OK - 平台 CSV 已生成到：", OUTPUT_ROOT)
