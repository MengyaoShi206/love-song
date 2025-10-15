#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# 构造简历文本 
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

# 构造岗位文本
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

