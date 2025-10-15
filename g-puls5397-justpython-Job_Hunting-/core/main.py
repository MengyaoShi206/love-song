#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# 主程序
def main():
    # 加载数据
    df = pd.read_csv('resumes_dataset.csv')
    df = preprocess_data(df)
    
    # 筛选简历
    filtered = df[
        (df['education_level'] >= JOB_REQUIREMENTS['min_education']) &
        (df['experience_years'] >= JOB_REQUIREMENTS['min_experience'])
    ]
    def has_required_skills(skills_dict):
        return all(skill in skills_dict for skill in JOB_REQUIREMENTS['required_skills'])
    filtered = filtered[filtered['skills_parsed'].apply(has_required_skills)]
    
    
    # 综合评分
    filtered['score'] = filtered.apply(
        lambda row: evaluate_candidate(row, JOB_REQUIREMENTS), axis=1)
    result = filtered.sort_values('score', ascending=False)
    
    # 准备评分系统筛选数据
    resume_df = prepare_resume_data(result)
    
    # 创建岗位描述
    positions = create_position_descriptions()
    
    # 向量化
    resume_vectors, position_vectors, vectorizer = vectorize_data(resume_df, positions)
    
    # 计算相似度
    similarity_matrix = calculate_similarity(resume_vectors, position_vectors)
    
    # 可视化
    visualize_results(similarity_matrix, positions)
    
    # 获取匹配结果
    matches = get_top_matches(similarity_matrix, positions, resume_df)
    
    # 打印结果
    for position, candidates in matches.items():
        print(f"\nTop candidates for {position}:")
        for cand in candidates:
            print(f" - {cand['index']} {cand['name']} ({cand['email']}): "
                  f"Similarity: {cand['similarity']:.2f}, "
                  f"Exp: {cand['experience']} yrs, "
                  f"Education: {cand['education']}")
    


if __name__ == "__main__":
    main()

