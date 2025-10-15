#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# 交互式配置岗位要求
def configure_job_requirements():

    print("===== 岗位要求 =====")
    print("请根据提示输入岗位要求信息（输入后按回车确认）\n")
    
    # 学历映射表
    education_map = {
        "0": "高中及以下",
        "1": "大专",
        "2": "本科",
        "3": "硕士",
        "4": "博士"
    }
    
    # 最低学历要求
    while True:
        print("最低学历要求选项：")
        for code, level in education_map.items():
            print(f"  {code}: {level}")
        
        min_education = input("\n请输入最低学历代码 (0-4): ").strip()
        if min_education in education_map:
            min_education = int(min_education)
            break
        print("⚠️ 错误：请输入有效的学历代码 (0-4)")
    
    # 最低工作经验
    while True:
        min_experience = input("\n请输入最低工作经验年限 (0-50): ").strip()
        if min_experience.isdigit() and 0 <= int(min_experience) <= 50:
            min_experience = int(min_experience)
            break
        print("⚠️ 错误：请输入0-50之间的整数")
    
    # 必须技能
    required_skills = input("\n请输入必须技能（多个技能用逗号分隔）: ").strip()
    required_skills = [s.strip() for s in required_skills.split(",") if s.strip()]
    
    # 优先技能
    preferred_skills = input("\n请输入优先技能（多个技能用逗号分隔）: ").strip()
    preferred_skills = [s.strip() for s in preferred_skills.split(",") if s.strip()]
    
    # 行业关键词
    industry_keywords = input("\n请输入行业关键词（多个关键词用逗号分隔）: ").strip()
    industry_keywords = [k.strip() for k in industry_keywords.split(",") if k.strip()]
    
    # 地点偏好
    location_preference = input("\n请输入工作地点偏好（多个地点用逗号分隔）: ").strip()
    location_preference = [loc.strip() for loc in location_preference.split(",") if loc.strip()]
    
    # 职位标题
    position_titles = input("\n请输入相关职位标题（多个标题用逗号分隔）: ").strip()
    position_titles = [t.strip() for t in position_titles.split(",") if t.strip()]
    
    # 技术关键词
    technical_keywords = input("\n请输入技术关键词（多个关键词用逗号分隔）: ").strip()
    technical_keywords = [k.strip() for k in technical_keywords.split(",") if k.strip()]
    
    # 构建配置字典
    job_requirements = {
        'min_education': min_education,
        'min_experience': min_experience,
        'required_skills': required_skills,
        'preferred_skills': preferred_skills,
        'industry_keywords': industry_keywords,
        'location_preference': location_preference,
        'position_titles': position_titles,
        'technical_keywords': technical_keywords
    }
    
    
    return job_requirements

