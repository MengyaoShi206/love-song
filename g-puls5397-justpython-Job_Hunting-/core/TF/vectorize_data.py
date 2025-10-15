#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# 特征工程
def vectorize_data(resumes, positions):
    #向量化文本数据
    all_texts = list(resumes['combined_text']) + list(positions.values())
    
    # 使用TF-IDF向量化
    vectorizer = TfidfVectorizer(max_features=500)
    tfidf_matrix = vectorizer.fit_transform(all_texts)
    
    # 分割回简历和岗位
    resume_vectors = tfidf_matrix[:len(resumes)]
    position_vectors = tfidf_matrix[len(resumes):]
    
    return resume_vectors, position_vectors, vectorizer

