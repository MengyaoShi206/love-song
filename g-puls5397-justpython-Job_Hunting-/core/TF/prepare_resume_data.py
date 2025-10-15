#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# 准备简历特征数据
def prepare_resume_data(df):
    # 合并简历文本特征
    text_fields = ['summary', 'skills', 'work_1_description', 
                  'work_2_description', 'work_3_description',
                  'project_1_description', 'project_2_description', 
                  'project_3_description']
    df['combined_text'] = ''
    for field in text_fields:
        df[field] = df[field].fillna('')
        df['combined_text'] += ' ' + df[field].apply(preprocess_text)
    
    # 添加其他特征
    df['experience_years'] = df['experience_years'].clip(lower=0)
    df['education_level'] = df['education_level'].fillna(0)
    
    # 添加技能匹配度特征
    skills_list = [
    # 信息技术(IT/互联网)
    "Python", "Java", "C++", "Go", "Rust", "前端框架(React/Vue)", "后端架构(Spring/Django)", 
    "数据库(MySQL/Redis)", "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Serverless架构",
    "机器学习(Scikit-learn/TensorFlow)", "大数据(Hadoop/Spark)", "数据可视化(PowerBI/Tableau)",
    "渗透测试", "漏洞挖掘", "防火墙策略", "密码学基础",
    
    # 金融经济
    "财务建模(DCF/LBO)", "估值分析", "并购重组", "尽职调查", "量化交易(Python/R)", "风险管理(VaR模型)",
    "衍生品定价", "会计准则(IFRS/GAAP)", "税务筹划", "内部控制", "审计软件(ACL/IDEA)", "区块链开发",
    "支付系统架构", "信贷评分模型",
    
    # 医疗健康
    "疾病诊断", "手术操作", "影像判读(X光/CT)", "急救技术", "药物合成", "临床试验设计", "基因组学分析",
    "病理检测", "流行病统计学", "健康政策评估", "疫苗管理", "设备操作(MRI/ECG)", "生物传感器开发",
    "医用机器人维护",
    
    # 工程制造
    "CAD/CAE(SolidWorks/ANSYS)", "热力学仿真", "精密加工(CNC)", "PCB设计(Altium)", "嵌入式开发(ARM)",
    "FPGA编程", "半导体工艺", "BIM建模(Revit)", "结构计算(ETABS)", "工程造价", "绿色建筑认证(LEED)",
    "自动化控制(PLC/SCADA)", "数字孪生", "柔性生产线优化",
    
    # 教育科研
    "课程设计", "教育心理学应用", "STEAM教学法", "实验设计(双盲试验)", "文献计量分析", "科研写作(SCI规范)",
    "LMS系统管理(Moodle)", "MOOC开发", "AR/VR教学工具",
    
    # 创意设计
    "Adobe全家桶(PS/AI/AE)", "3D建模(Blender/Maya)", "影视剪辑(DaVinci)", "人机工程学", "材料工艺",
    "原型制作(3D打印)", "SketchUp", "GIS空间分析", "景观生态规划",
    
    # 法律法务
    "合同审查", "IPO合规", "反垄断法", "GDPR数据保护", "诉讼策略", "仲裁程序", "证据链构建", "专利撰写",
    "商标维权", "技术秘密保护",
    
    # 市场运营
    "SEO/SEM", "社交媒体运营", "增长黑客", "用户画像分析", "VI系统设计", "危机公关", "消费者行为研究",
    "物流优化", "库存控制(ABC分析法)", "采购谈判",
    
    # 新兴领域
    "光伏系统设计", "储能技术", "碳足迹核算", "Unity/Unreal引擎", "虚拟人开发", "NFT智能合约",
    "可持续发展报告(GRI标准)", "绿色金融", "企业碳中和路径",
    
    # 通用核心技能
    "Excel", "SQL", "Python", "敏捷开发", "甘特图", "Risk管理", "商务英语", "跨文化谈判", "Office套件",
    "Notion", "低代码平台"]
    
    for skill in skills_list:
            df[f'skill_{skill}'] = df['skills'].apply(lambda x: 1 if skill in x else 0)
    return df

