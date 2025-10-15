#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# 数据预处理
def preprocess_data(df):
    
    # 清洗异常工作经验
    df['experience_years'] = df['experience_years'].apply(
        lambda x: max(0, x) if isinstance(x, (int, float)) else 0)
    
    # 解析技能字符串
    df['skills_parsed'] = df['skills'].apply(parse_skills)
    
    # 合并所有工作经历描述
    df['all_work_desc'] = df.apply(
        lambda row: ' '.join([str(row[f'work_{i}_description']) 
                             for i in range(1,4) 
                             if pd.notna(row[f'work_{i}_description'])]), axis=1)
    
    # 合并所有项目经历描述
    df['all_project_desc'] = df.apply(
        lambda row: ' '.join([str(row[f'project_{i}_description']) 
                             for i in range(1,4) 
                             if pd.notna(row[f'project_{i}_description'])]), axis=1)
    
    # 提取最高学历信息
    df['highest_degree'] = df.apply(extract_highest_degree, axis=1)
    
    # 计算工作稳定性
    df['job_stability'] = df.apply(calculate_job_stability, axis=1)
    
    return df
def parse_skills(skill_str):
    # 解析技能字符串为字典{技能: 熟练度}
    skills = {}
    for item in skill_str.split('，'):
        match = re.search(r'(.+?) \((精通|熟练|掌握)\)', item)
        if match:
            skill, level = match.groups()
            skills[skill.strip()] = level
    return skills

def extract_highest_degree(row):
    # 提取最高学历信息
    for i in range(3, 0, -1):
        if pd.notna(row[f'edu_{i}_school']):
            return {
                'school': row[f'edu_{i}_school'],
                'major': row[f'edu_{i}_major'],
                'degree': row[f'edu_{i}_degree']
            }
    return {'school': '', 'major': '', 'degree': ''}


def calculate_job_stability(row):
    # 计算工作稳定性得分
    stability_score = 0
    positions = 0
    
    for i in range(1, 4):
        company = row[f'work_{i}_company']
        start = row[f'work_{i}_start']
        end = row[f'work_{i}_end']
        
        if pd.notna(company):
            positions += 1
            try:
                # 计算工作持续时间
                start_date = datetime.strptime(start, '%Y-%m')
                end_date = datetime.strptime(end, '%Y-%m') if end != '至今' and end != '无结束日期' else datetime.now()
                duration = (end_date - start_date).days / 365
                
                # 超过2年加分
                if duration >= 2:
                    stability_score += 2
            except:
                continue
                
    # 平均每段工作时长得分
    return stability_score

