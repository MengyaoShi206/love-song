#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# 评分系统
def evaluate_candidate(row, requirements):
    # 候选人综合评分
    total_score = 0
    
    # 基础资格评分 
    base_score = evaluate_base_qualification(row, requirements)
    
    # 技能匹配度评分 
    skill_score = evaluate_skills(row, requirements)
    
    # 工作经验评分 
    experience_score = evaluate_experience(row, requirements)
    
    # 教育背景评分 
    education_score = evaluate_education(row)
    
    # 额外加分项 
    bonus_score = evaluate_bonus(row)
    
    total_score = base_score + skill_score + experience_score + education_score + bonus_score
    return min(total_score, 100)  # 确保不超过100分



def evaluate_base_qualification(row, req):
    # 基础资格评分
    score = 0
    
    # 学历要求
    if row['education_level'] >= req['min_education']:
        score += 8
    else:
        return 0  # 学历不达标直接淘汰
    
    # 工作经验
    if row['experience_years'] >= req['min_experience']:
        score += 8
    else:
        return 0  # 经验不达标直接淘汰
    
    # 地点偏好
    if any(loc in row['city'] for loc in req['location_preference']):
        score += 4
    
    return score

def evaluate_skills(row, req):
    # 技能匹配度评分
    score = 0
    skills = row['skills_parsed']
    
    # 必须技能检查
    must_have_count = 0
    for skill in req['required_skills']:
        if skill in skills:
            must_have_count += 1
            # 根据熟练度加分
            proficiency = skills[skill]
            if proficiency == '精通':
                score += 3
            elif proficiency == '熟练':
                score += 2
            else:
                score += 1
    
    # 必须技能不全则淘汰
    if must_have_count < len(req['required_skills']):
        return 0
    
    # 基础分 (满足必须技能)
    score += 15
    
    # 优先技能加分
    for skill in req['preferred_skills']:
        if skill in row['all_work_desc'] or skill in row['all_project_desc']:
            score += 2
    
    # 技能相关性上限
    return min(score, 40)

def evaluate_experience(row, req):
    # 工作经验评分
    score = 0
    work_desc = row['all_work_desc'].lower()
    project_desc = row['all_project_desc'].lower()
    
    # 职位相关性
    for title in req['position_titles']:
        if title in work_desc:
            score += 5
    
    # 行业经验
    industry_match = False
    for industry in req['industry_keywords']:
        if industry in work_desc or industry in project_desc:
            score += 4
            industry_match = True
    
    # 技术关键词匹配
    tech_keywords_count = 0
    for keyword in req['technical_keywords']:
        if keyword in work_desc or keyword in project_desc:
            tech_keywords_count += 1
            score += 2
    
    # 重大项目经验
    if '架构设计' in work_desc or '核心开发' in work_desc:
        score += 5
    
    # 稳定性加分
    score += min(row['job_stability'], 5)
    
    return min(score, 25)

def evaluate_education(row):
    # 教育背景评分
    score = 0
    degree = row['highest_degree']
    
    # 学校等级
    if any(school in degree['school'] for school in elite_schools):
        score += 4
    
    # 专业相关性
    if any(major in degree['major'] for major in tech_majors):
        score += 3
    
    # 学历加分
    if row['education_level'] >= 3:  # 硕士及以上
        score += 2
    
    # 学位类型
    if '硕士' in degree['degree'] or '博士' in degree['degree']:
        score += 1
    
    return min(score, 10)

def evaluate_bonus(row):
    # 额外加分项 (5分) 
    score = 0
    
    # 证书认证
    if 'AWS' in row['skills'] or 'Azure' in row['skills'] or 'GCP' in row['skills']:
        score += 2
    
    # 奖项荣誉
    for i in range(1, 4):
        award = row[f'award_{i}_description']
        if pd.notna(award):
            if '国家级' in award or '国际级' in award:
                score += 3
            elif '省级' in award:
                score += 2
            elif '市级' in award:
                score += 1
    
    # 项目成果
    if '用户增长' in row['all_project_desc'] or '成本降低' in row['all_project_desc']:
        score += 1
    
    return min(score, 5)

