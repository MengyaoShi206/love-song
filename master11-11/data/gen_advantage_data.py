# /master/data/gen_advantage_data.py
import os, csv, random, datetime

# 直接放在 data/advantage 下
root = os.path.join(os.path.dirname(__file__), "advantage")
os.makedirs(root, exist_ok=True)

headers = ["id", "title", "desc", "img", "time", "destination"]

titles = [
    "解锁更多推荐位", "开通高级筛选", "限时VIP优惠", "发布高质量照片赢曝光",
    "寻找同城缘分", "智能匹配升级", "心动来电", "发现有趣灵魂", "情感测试限时开放", "今日缘分榜TOP"
]
descs = [
    "上传清晰头像，即刻提升曝光", "按学历、城市、是否离异筛选心仪对象",
    "首月仅9.9元，解锁高级匹配功能", "三张真实照片助你获得更多点赞",
    "开启同城缘分推送，遇见更近的人", "AI推荐算法升级，更精准更懂你",
    "参与心动来电活动，速配对象立刻见面", "让AI带你找到志同道合的人",
    "一分钟测测你的恋爱类型", "看看今日谁与你最匹配"
]
destinations = [
    "/ad/boost", "/ad/vip", "/ad/filter", "/ad/photo", "/ad/local",
    "/ad/ai", "/ad/call", "/ad/fun", "/ad/test", "/ad/top"
]

path_csv = os.path.join(root, "advantage.csv")

with open(path_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(headers)
    for i in range(1, 101):  # 生成100条
        title = random.choice(titles)
        desc = random.choice(descs)
        img = f"https://placehold.co/600x240?text=Ad+{i}"
        destination = random.choice(destinations)
        time = (datetime.datetime.utcnow() - datetime.timedelta(days=random.randint(0, 60))).strftime("%Y-%m-%d %H:%M:%S")
        w.writerow([i, title, desc, img, time, destination])

print(f"✅ 已生成 100 条广告数据到 {path_csv}")
