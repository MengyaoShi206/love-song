#!/usr/bin/env python
# coding: utf-8

# In[6]:


import pandas as pd
import numpy as np
import re
import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime

# 读取岗位 
jobs = pd.read_csv('jobs_dataset.csv')



def configure_resume():
    print("\n【1. 基本信息】")
    basic = {
        "city":        input("所在城市：").strip(),
        "self_intro":  input("自我介绍（一句话）：").strip()
    }

    # ---------- 2. 教育经历 ----------
    education = []
    while True:
        print("\n【2. 教育经历】新增一条？（y/n）", end=' ')
        if input().strip().lower() != 'y':
            break
        edu = {
            "school":  input("学校名称：").strip(),
            "start":   input("开始时间（yyyy-mm）：").strip(),
            "end":     input("结束时间（yyyy-mm）：").strip(),
            "major":   input("专业：").strip(),
            "degree":  input("学历（高中/大专/本科/硕士/博士）：").strip()
        }
        education.append(edu)

    # ---------- 3. 工作经历 ----------
    work = []
    while True:
        print("\n【3. 工作经历】新增一条？（y/n）", end=' ')
        if input().strip().lower() != 'y':
            break
        w = {
            "company":     input("公司名称：").strip(),
            "start":       input("开始时间（yyyy-mm）：").strip(),
            "end":         input("结束时间（yyyy-mm，填“至今”或日期）：").strip(),
            "position":    input("职位：").strip(),
            "description": input("工作描述：").strip()
        }
        work.append(w)

    # ---------- 4. 项目经历 ----------
    project = []
    while True:
        print("\n【4. 项目经历】新增一条？（y/n）", end=' ')
        if input().strip().lower() != 'y':
            break
        p = {
            "name":   input("项目名称：").strip(),
            "start":  input("开始时间（yyyy-mm）：").strip(),
            "end":    input("结束时间（yyyy-mm）：").strip(),
            "role":   input("你的角色：").strip(),
            "desc":   input("项目描述：").strip()
        }
        project.append(p)

    # ---------- 5. 专业技能 ----------
    skills = input("\n【5. 专业技能】用逗号分隔：").strip().split(',')
    skills = [s.strip() for s in skills if s.strip()]

    # ---------- 组装简历字典 ----------
    resume = {
        "basic":      basic,
        "education":  education,
        "work":       work,
        "project":    project,
        "skills":     skills
    }
    
    return resume

resume=configure_resume()


# 构造文本 
def build_resume_text(r):
    txt = [r["basic"]["self_intro"]]
    for edu in r["education"]:
        txt.append(f"{edu['degree']} {edu['major']} 专业")
    for w in r["work"]:
        txt.append(w["description"])
    for p in r["project"]:
        txt.append(p["desc"])
    txt += r["skills"]
    return " ".join(txt)

def build_job_text(row):
    return " ".join([
        str(row["岗位标题"]), str(row["岗位详情"]), str(row["岗位分类"]),
        str(row["薪资范围"]), str(row["工作性质"]), str(row["工作经验"]),
        str(row["教育要求"]), str(row["公司类型"]), str(row["岗位福利"])
    ])

resume_text = build_resume_text(resume)
jobs["job_text"] = jobs.apply(build_job_text, axis=1)


# 推荐模型 中文分词 + TF-IDF
stop_words = list('的 了 和 是 在 我 有 与 及 或 等 可 并 能 为 上 下'.split())

def cut(text):
    return " ".join([w for w in jieba.lcut(text) if w.strip() and w not in stop_words])

corpus = [cut(resume_text)] + jobs["job_text"].apply(cut).tolist()

vectorizer = TfidfVectorizer(
    max_df=0.8,
    min_df=2,
    ngram_range=(1, 2),
    stop_words=stop_words
)
tfidf_matrix = vectorizer.fit_transform(corpus)


resume_vec = tfidf_matrix[0]# 第 0 行是简历向量
job_vecs   = tfidf_matrix[1:]

# 余弦相似度  
sim_scores = cosine_similarity(resume_vec, job_vecs).flatten()

# 规则加权 
def rule_score(row, r):
    score = 0.0
    if r["basic"]["city"] in str(row["地域要求"]):
        score += 0.1
    # 学历匹配
    req_deg = str(row["教育要求"]).lower()
    max_deg = max([e["degree"] for e in r["education"]],
                  key=lambda d: {"高中":0,"大专":1,"本科":2,"硕士":3,"博士":4}[d])
    if max_deg in req_deg or req_deg in max_deg:
        score += 0.05
    # 经验年限
    req_exp = str(row["工作经验"])
    years = 5
    if "不限" in req_exp or "应届" in req_exp:
        score += 0.05
    else:
        nums = list(map(int, re.findall(r"\d+", req_exp)))
        if nums and years >= nums[0]:
            score += 0.05
    return score

rule_scores = jobs.apply(lambda row: rule_score(row, resume), axis=1).values

# 最终得分 
alpha = 0.7   # TF-IDF 权重(可学习)
final_scores = alpha * sim_scores + (1 - alpha) * rule_scores

# 输出 Top-N 结果
N = 10
top_idx = np.argsort(final_scores)[::-1][:N]
recommend = jobs.iloc[top_idx][["岗位ID", "岗位标题", "公司类型", "薪资范围", "地域要求", "岗位福利"]]
recommend["score"] = final_scores[top_idx].round(4)

print("为您推荐的岗位：")
print(recommend.to_string(index=False))


# In[ ]:


# 简历配置
resume = {
    "basic": {
        "city": "上海",
        "self_intro": "5 年 Java 后端开发经验，熟悉 SpringCloud、MySQL、Redis，主导过日均千万级请求的微服务系统。",
    },
    "education": [
        {"school": "复旦大学", "start": "2014-09", "end": "2018-06",
         "major": "计算机科学与技术", "degree": "本科"}
    ],
    "work": [
        {"company": "XX 科技有限公司", "start": "2018-07", "end": "至今",
         "position": "高级 Java 工程师",
         "description": "负责订单中心微服务架构升级，引入异步消息队列，将接口 99 线耗时从 120ms 降到 45ms。"}
    ],
    "project": [
        {"name": "高并发秒杀系统", "start": "2021-03", "end": "2021-12",
         "role": "技术负责人",
         "desc": "基于 Redis + Lua 脚本实现库存扣减，QPS 提升 10 倍。"}
    ],
    "skills": ["Java", "Spring Boot", "Spring Cloud", "MySQL", "Redis", "Kafka", "Docker", "K8s"]
}

