#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# 相似度计算
def calculate_similarity_results(resume_vectors, position_vectors):
    #计算简历与岗位的相似度矩阵
    similarity_matrix = cosine_similarity(resume_vectors, position_vectors)
    return similarity_matrix

# 可视化与结果处理
def visualize_results(similarity_matrix, positions):
    #可视化相似度分布
    plt.figure(figsize=(12, 8))
    sns.heatmap(similarity_matrix, 
                xticklabels=positions.keys(),
                cmap='YlGnBu')
    plt.title('简历岗位 Matching Matrix')
    plt.ylabel('Resume Index')
    plt.xlabel('Position')
    plt.tight_layout()
    plt.savefig('matching_heatmap.png', dpi=300)
    plt.show()

#获取岗位的前N个匹配简历
def get_top_matches(similarity_matrix, positions, resumes, top_n=10):
    position_names = list(positions.keys())
    results = {}
    
    for i, position in enumerate(position_names):
        # 获取当前岗位的相似度分数
        scores = similarity_matrix[:, i]
        # 获取前N个简历的索引
        top_indices = np.argsort(scores)[-top_n:][::-1]
        
        # 收集结果
        position_results = []
        for idx in top_indices:
            resume_data = {
                'index':idx,
                'name': resumes.iloc[idx]['name'],
                'email': resumes.iloc[idx]['email'],
                'phone': resumes.iloc[idx]['phone'],
                'similarity': scores[idx],
                'experience': resumes.iloc[idx]['experience_years'],
                'education': resumes.iloc[idx]['highest_education']
            }
            position_results.append(resume_data)
        
        results[position] = position_results
    
    return results

