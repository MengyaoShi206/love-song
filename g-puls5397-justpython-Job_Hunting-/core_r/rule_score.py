#!/usr/bin/env python
# coding: utf-8

# In[ ]:


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

