#!/usr/bin/env python
# coding: utf-8

# In[32]:


import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import random
import os
from tqdm import tqdm

# 初始化Faker生成器（中文）
fake = Faker('zh_CN')
random.seed(42)
np.random.seed(42)

# 学历级别映射
EDUCATION_LEVELS = {
    0: "高中及以下",
    1: "大专",
    2: "本科",
    3: "硕士",
    4: "博士"
}

# 专业技能库
SKILLS_LIBRARY = [
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
    "Notion", "低代码平台"
]

# 职位名称库
JOB_TITLES = [
    # 信息技术 (IT) / 互联网 / 软件 / 硬件
    "软件工程师", "前端开发工程师", "后端开发工程师", "全栈开发工程师", 
    "移动应用开发工程师", "DevOps工程师", "系统架构师", "数据库管理员", 
    "网络工程师", "信息安全工程师", "云计算工程师", "大数据工程师", 
    "人工智能工程师", "机器学习工程师", "算法工程师", "测试工程师", 
    "自动化测试工程师", "技术支持工程师", "IT运维工程师", "硬件工程师", 
    "嵌入式系统工程师", "固件工程师", "游戏开发工程师", "UI设计师", 
    "UX设计师", "技术文档工程师", "产品经理", "产品助理", "产品总监", 
    "交互设计师", "视觉设计师", "用户研究员", "数据分析师", "数据科学家", 
    "数据工程师", "数据仓库工程师", "商业智能分析师", "网站运营", 
    "产品运营", "用户运营", "内容运营", "活动运营", "新媒体运营", 
    "社区运营", "电商运营", "IT项目经理", "市场经理", "数字营销专员", 
    "SEO/SEM专员", "技术总监", "研发总监", "IT经理", "IT咨询顾问", 
    "IT采购专员",
    
    # 金融
    "柜员", "客户经理", "理财经理", "信贷专员", "信贷经理", 
    "风险管理经理", "合规经理", "反洗钱专员", "资金交易员", 
    "外汇交易员", "投资银行分析师", "投资银行经理", "运营专员", 
    "运营经理", "产品经理", "技术开发", "证券经纪人", "投资顾问", 
    "基金经理", "基金销售", "行业研究员", "量化分析师", "交易员", 
    "风控经理", "私募股权投资经理", "风险投资经理", "保险代理人", 
    "保险经纪人", "核保师", "理赔专员", "理赔经理", "精算师", 
    "保险产品经理", "会计师", "审计师", "税务专员", "税务经理", 
    "财务分析师", "财务经理", "财务总监", "区块链工程师", 
    "支付产品经理", "风控模型开发", "合规科技专员",
    
    # 医疗保健 / 生物医药
    "医生", "护士", "药剂师", "医学检验师", "医学影像技师", 
    "康复治疗师", "营养师", "麻醉师", "助产士", "心理咨询师", 
    "心理治疗师", "生物信息学家", "生物统计师", "临床研究员", 
    "药物研发科学家", "医学写作专员", "实验室技术员", "实验室研究员", 
    "生产经理", "生产主管", "质量保证专员", "质量保证经理", 
    "质量控制专员", "质量控制经理", "注册专员", "药物安全专员", 
    "医疗器械研发工程师", "临床评价专员", "质量工程师", "销售工程师", 
    "医院管理人员", "科室主任", "医务科专员", "病案管理员", 
    "健康管理师", "医疗顾问", "医药代表", "医疗器械销售代表", 
    "医疗信息管理专员", "医保专员", "医疗设备维护工程师", 
    "医疗采购专员",
    
    # 教育
    "教师", "大学教授", "大学讲师", "助理教授", "助教", "培训师", 
    "家教", "教练", "校长", "园长", "教务主任", "教务处长", "教研员", 
    "课程顾问", "招生顾问", "学籍管理员", "教学支持专员", "教育咨询师", 
    "教育产品经理", "教育技术专员", "教育研究员", "图书管理员", 
    "实验室管理员",
    
    # 制造业
    "机械工程师", "电气工程师", "电子工程师", "自动化工程师", 
    "工艺工程师", "质量工程师", "研发工程师", "测试工程师", 
    "工业工程师", "结构工程师", "材料工程师", "包装工程师", 
    "项目工程师", "生产经理", "生产主管", "车间主任", "班组长", 
    "操作工", "技术员", "设备维护工程师", "维修技师", "计划员", 
    "生产计划专员", "物流专员", "物流经理", "仓储管理员", "采购专员", 
    "采购经理", "供应链专员", "供应链经理", "质量检验员", 
    "质量管理工程师", "质量管理经理", "体系工程师", "安全工程师", 
    "安全专员", "销售工程师", "技术销售代表", "客户服务工程师", 
    "技术文档专员",
    
    # 消费品 / 零售
    "品牌经理", "产品经理", "市场经理", "数字营销专员", 
    "社交媒体专员", "内容营销专员", "公关专员", "促销活动专员", 
    "销售代表", "销售经理", "零售店长", "店员", "采购专员", 
    "采购经理", "买手", "电商运营专员", "视觉陈列师", "供应链经理", 
    "物流经理", "仓储经理", "配送中心主管", "计划专员", 
    "产品开发经理", "包装设计师", "食品科学家", "研发工程师", 
    "服装设计师", "商品企划", "客户服务代表", "售后支持专员",
    
    # 专业服务
    "咨询顾问", "分析师", "项目经理", "咨询总监", "合伙人", 
    "律师", "律师助理", "法务专员", "法务经理", "合规专员", 
    "合规经理", "专利代理人", "商标代理人", "法律秘书", "法律助理", 
    "会计师", "审计师", "税务顾问", "财务顾问", "簿记员", 
    "招聘顾问", "猎头", "人力资源外包专员", "薪酬福利顾问", 
    "培训师", "客户经理", "客户总监", "文案", "美术指导", 
    "创意总监", "媒介策划", "媒介购买", "公关专员", "公关经理", 
    "活动策划",
    
    # 媒体与娱乐
    "记者", "编辑", "编剧", "导演", "制片人", "摄影师", "摄像师", 
    "剪辑师", "动画师", "游戏设计师", "音效师", "作曲家", "作词人", 
    "主持人", "主播", "演员", "模特", "艺术家", "插画师", 
    "内容运营专员", "社交媒体编辑", "平台运营专员", "版权专员", 
    "发行经理", "节目编排", "灯光师", "音响师", "舞台监督", 
    "化妆师", "造型师", "技术工程师", "游戏开发工程师", 
    "广告销售代表", "品牌合作经理", "艺人经纪", "票务经理", 
    "活动策划", "活动执行",
    
    # 房地产与建筑
    "开发经理", "投资分析师", "策划经理", "报建专员", 
    "房地产经纪人", "置业顾问", "估价师", "物业经理", "设施经理", 
    "招商专员", "招商经理", "租赁专员", "建筑师", "景观设计师", 
    "室内设计师", "规划师", "建筑设计师助理", "BIM工程师", 
    "结构工程师", "给排水工程师", "暖通工程师", "电气工程师", 
    "土木工程师", "施工员", "项目经理", "监理工程师", "造价工程师", 
    "预算员", "安全员", "材料员", "测量员",
    
    # 酒店与旅游
    "酒店经理", "前厅经理", "前厅主管", "客房经理", "客房主管", 
    "礼宾", "前台接待", "客房服务员", "餐饮经理", "餐饮主管", 
    "厨师", "服务员", "调酒师", "会议活动经理", "旅游顾问", 
    "导游", "领队", "景区管理员", "销售经理", "销售代表", "市场专员", 
    "预订专员", "人力资源专员", "采购专员", "工程维修",
    
    # 能源与环保
    "石油工程师", "地质工程师", "钻井工程师", "采油工程师", 
    "矿业工程师", "电厂运行工程师", "检修工程师", "光伏系统工程师", 
    "风电工程师", "储能工程师", "电池研发工程师", "环境工程师", 
    "水处理工程师", "固废处理工程师", "环保咨询顾问", 
    "EHS工程师", "EHS经理", "碳管理咨询师", "项目工程师", 
    "安全工程师", "工艺工程师", "设备工程师", "销售工程师",
    
    # 交通运输与物流
    "飞行员", "空乘", "船长", "轮机长", "船员", "列车长", "列车员", 
    "公交司机", "出租车司机", "货运司机", "调度员", "物流经理", 
    "仓储经理", "配送经理", "运输经理", "供应链经理", "采购经理", 
    "计划专员", "关务专员", "货代操作员", "海运操作员", "空运操作员", 
    "物流销售", "仓库管理员", "叉车司机", "交通规划师", "路桥工程师", 
    "港口工程师", "机场运营专员", "维修技师", "客户服务代表",
    
    # 政府与非营利组织
    "公务员", "政策分析师", "研究员", "项目经理", "项目官员", 
    "筹款专员", "传播专员", "政策倡导专员", "志愿者协调员", 
    "行政经理", "财务专员",
    
    # 农业
    "农艺师", "畜牧师", "水产养殖师", "农业技术员", "种植场经理", 
    "养殖场经理", "农产品加工工程师", "农业机械工程师", "农场主", 
    "农场经理", "采购专员", "销售代表", "农产品质量检验员", 
    "农业合作社经理", "农业研究员", "农业推广员", "兽医",
    
    # 艺术与文化
    "艺术家", "策展人", "博物馆管理员", "美术馆管理员", 
    "文物修复师", "档案管理员", "图书馆员", "音乐家", "舞蹈家", 
    "戏剧工作者", "非遗传承人", "艺术机构总监", "艺术机构经理", 
    "画廊经理", "文化项目专员"
]

# 奖项级别
AWARD_LEVELS = ["公司级", "区县级", "市级", "省级", "国家级", "国际级"]

def generate_photo_url():
    """生成虚拟照片URL"""
    return f"https://resume-photos.example.com/{fake.uuid4()}.jpg"

def generate_education():
    """生成教育经历（1-3段）"""
    num_educations = random.randint(1, 3)
    educations = []
    
    # 确保时间顺序合理
    end_dates = []
    for _ in range(num_educations):
        end_date = None  # 先初始化默认值
        # 随机选择学历级别（0-4）
        level = random.randint(0, 4)
        
        # 如果是第一段教育经历，从18岁开始
        if not educations:
            start_date = fake.date_of_birth(minimum_age=18, maximum_age=22)
        else:
            # 下一段教育应在上一段结束后开始
            prev_end = max(end_dates) if end_dates else datetime.now().date()
            start_date = fake.date_between_dates(
                date_start=prev_end + timedelta(days=30),
                date_end=prev_end + timedelta(days=365*2))
            duration = random.randint(2,5)  # 学习年限
            end_date = fake.date_between_dates(
                date_start=start_date + timedelta(days=365*duration),  
                date_end=start_date + timedelta(days=365*duration))
            end_dates.append(end_date)
        
        educations.append({
            "school": fake.company() + "大学",
            "start_date": start_date.strftime("%Y-%m"),
            "end_date": end_date.strftime("%Y-%m-%d") if end_date else "无结束日期",
            "major": random.choice(["计算机科学", "软件工程", "人工智能", "数据科学", 
                                 "电子信息工程", "网络安全", "数学与应用数学"]),
            "degree": EDUCATION_LEVELS[level]
        })
    
    return educations

def generate_work_experience(birthdate):
    """生成工作经历（1-3段）"""
    num_jobs = random.randint(1, 3)
    experiences = []
    
    # 计算最小工作年龄（18岁）
    min_work_age = 18
    current_age = datetime.now().year - birthdate.year
    
    # 确保有合理的工作年限
    if current_age < min_work_age + 2:
        return experiences
    
    # 确保时间顺序合理
    end_dates = []
    for _ in range(num_jobs):
        job_title = random.choice(JOB_TITLES)
        
        if not experiences:
            # 第一份工作从22岁左右开始
            min_start_age = max(22, min_work_age)
            start_date = fake.date_between_dates(
                date_start=birthdate + timedelta(days=min_start_age*365),
                date_end=birthdate + timedelta(days=(min_start_age+3)*365))
        else:
            # 下一份工作应在上一份结束后开始
            prev_end = max(end_dates) if end_dates else datetime.now().date()
            start_date = fake.date_between_dates(
                date_start=prev_end + timedelta(days=30),
                date_end=prev_end + timedelta(days=180))
            
        # 工作持续时间（3个月-5年）
        duration_months = random.randint(3, 60)
        end_date = fake.date_between_dates(
            date_start=start_date + timedelta(days=duration_months*30),
            date_end=start_date + timedelta(days=duration_months*30))
        
        # 确保结束日期不超过当前日期
        if end_date > datetime.now().date():
            end_date = None  # 当前工作
            
        end_dates.append(end_date or datetime.now().date())
        
        experiences.append({
            "company": fake.company(),
            "start_date": start_date.strftime("%Y-%m"),
            "end_date": end_date.strftime("%Y-%m") if end_date else "至今",
            "position": job_title,
            "description": f"负责{random.choice(['开发', '设计', '维护', '优化'])}{random.choice(['核心系统', '关键模块', '数据平台', '用户界面'])}，"
                         f"使用{random.choice(SKILLS_LIBRARY[:15])}等技术解决{random.choice(['性能', '安全', '用户体验'])}问题。"
        })
    
    return experiences

def generate_projects():
    """生成项目经历（0-3个）"""
    num_projects = random.randint(0, 3)
    projects = []
    
    for _ in range(num_projects):
        start_date = fake.date_between_dates(date_start='-5y', date_end='-1y')
        duration_months = random.randint(2, 18)
        end_date = start_date + timedelta(days=duration_months*30)
        
        projects.append({
            "name": random.choice(["智能", "大数据", "云", "AI", "移动"]) + random.choice(["平台", "系统", "应用", "解决方案"]),
            "start_date": start_date.strftime("%Y-%m"),
            "end_date": end_date.strftime("%Y-%m"),
            "role": random.choice(["项目负责人", "核心开发", "架构设计", "测试主管"]),
            "description": f"开发了一个基于{random.choice(['微服务', '分布式', '响应式'])}架构的{random.choice(['电商', '金融', '教育', '医疗'])}"
                         f"领域应用，实现了{random.choice(['用户增长', '效率提升', '成本降低'])}目标。"
        })
    
    return projects

def generate_skills():
    """生成专业技能（3-8项）"""
    num_skills = random.randint(3, 8)
    skills = random.sample(SKILLS_LIBRARY, num_skills)
    
    # 添加熟练程度
    return [f"{skill} ({random.choice(['熟练', '精通', '掌握'])})" for skill in skills]

def generate_awards():
    """生成奖项荣誉（0-3个）"""
    num_awards = random.randint(0, 3)
    awards = []
    
    for _ in range(num_awards):
        award_date = fake.date_between_dates(date_start='-5y', date_end='now')
        awards.append({
            "name": random.choice(["优秀员工", "技术创新", "设计大赛", "编程竞赛"]) + random.choice(["奖", "称号", "证书"]),
            "date": award_date.strftime("%Y-%m"),
            "level": random.choice(AWARD_LEVELS),
            "description": f"因{random.choice(['卓越表现', '突出贡献', '创新成果'])}"
                         f"获得{random.choice(['公司', '行业', '政府'])}颁发的奖项"
        })
    
    return awards

def generate_resume():
    """生成一份完整的简历数据"""
    # 基本信息
    birthdate = fake.date_of_birth(minimum_age=22, maximum_age=50)
    city = fake.city()
    
    resume = {
        "basic_info": {
            "photo": generate_photo_url(),
            "name": fake.name(),
            "gender": random.choice(["男", "女"]),
            "birthdate": birthdate.strftime("%Y-%m-%d"),
            "phone": fake.phone_number(),
            "email": fake.email(),
            "city": city,
            "summary": f"拥有{random.randint(1, 15)}年{random.choice(['软件开发', '数据分析', '系统架构'])}经验，"
                      f"擅长{random.choice(SKILLS_LIBRARY[:10])}等技术，"
                      f"期待在{random.choice(['互联网', '金融科技', '人工智能'])}领域发展。"
        },
        "education": generate_education(),
        "work_experience": generate_work_experience(birthdate),
        "projects": generate_projects(),
        "skills": generate_skills(),
        "awards": generate_awards()
    }
    
    # 添加最高学历字段
    if resume["education"]:
        highest_edu = max([list(EDUCATION_LEVELS.keys())[list(EDUCATION_LEVELS.values()).index(edu["degree"])] 
                          for edu in resume["education"]])
        resume["basic_info"]["highest_education"] = EDUCATION_LEVELS[highest_edu]
        resume["basic_info"]["education_level"] = highest_edu
    else:
        resume["basic_info"]["highest_education"] = "高中及以下"
        resume["basic_info"]["education_level"] = 0
    
    # 添加工作经验年限
    if resume["work_experience"]:
        total_experience = 0
        for job in resume["work_experience"]:
            start = datetime.strptime(job["start_date"], "%Y-%m")
            end = datetime.now() if job["end_date"] == "至今" else datetime.strptime(job["end_date"], "%Y-%m")
            total_experience += (end.year - start.year) + (end.month - start.month)/12
        resume["basic_info"]["experience_years"] = round(total_experience, 1)
    else:
        resume["basic_info"]["experience_years"] = 0.0
    
    return resume

def generate_resumes(num=1000):
    """生成多份简历"""
    resumes = []
    print(f"正在生成 {num} 份简历数据...")
    for _ in tqdm(range(num)):
        resumes.append(generate_resume())
    return resumes

def save_to_csv(resumes, filename="resumes_dataset.csv"):
    """将简历数据保存为CSV文件"""
    # 创建扁平化的数据结构
    data = []
    for resume in resumes:
        # 基本信息
        row = {
            "photo": resume["basic_info"]["photo"],
            "name": resume["basic_info"]["name"],
            "gender": resume["basic_info"]["gender"],
            "birthdate": resume["basic_info"]["birthdate"],
            "phone": resume["basic_info"]["phone"],
            "email": resume["basic_info"]["email"],
            "city": resume["basic_info"]["city"],
            "summary": resume["basic_info"]["summary"],
            "highest_education": resume["basic_info"]["highest_education"],
            "education_level": resume["basic_info"]["education_level"],
            "experience_years": resume["basic_info"]["experience_years"],
        }
        
        # 教育经历（最多3段）
        for i in range(3):
            prefix = f"edu_{i+1}_"
            if i < len(resume["education"]):
                edu = resume["education"][i]
                row.update({
                    prefix + "school": edu["school"],
                    prefix + "start": edu["start_date"],
                    prefix + "end": edu["end_date"],
                    prefix + "major": edu["major"],
                    prefix + "degree": edu["degree"]
                })
            else:
                row.update({
                    prefix + "school": "",
                    prefix + "start": "",
                    prefix + "end": "",
                    prefix + "major": "",
                    prefix + "degree": ""
                })
        
        # 工作经历（最多3段）
        for i in range(3):
            prefix = f"work_{i+1}_"
            if i < len(resume["work_experience"]):
                work = resume["work_experience"][i]
                row.update({
                    prefix + "company": work["company"],
                    prefix + "start": work["start_date"],
                    prefix + "end": work["end_date"],
                    prefix + "position": work["position"],
                    prefix + "description": work["description"]
                })
            else:
                row.update({
                    prefix + "company": "",
                    prefix + "start": "",
                    prefix + "end": "",
                    prefix + "position": "",
                    prefix + "description": ""
                })
        
        # 项目经历（最多3个）
        for i in range(3):
            prefix = f"project_{i+1}_"
            if i < len(resume["projects"]):
                project = resume["projects"][i]
                row.update({
                    prefix + "name": project["name"],
                    prefix + "start": project["start_date"],
                    prefix + "end": project["end_date"],
                    prefix + "role": project["role"],
                    prefix + "description": project["description"]
                })
            else:
                row.update({
                    prefix + "name": "",
                    prefix + "start": "",
                    prefix + "end": "",
                    prefix + "role": "",
                    prefix + "description": ""
                })
        
        # 专业技能（合并为字符串）
        row["skills"] = "，".join(resume["skills"])
        
        # 奖项荣誉（最多3个）
        for i in range(3):
            prefix = f"award_{i+1}_"
            if i < len(resume["awards"]):
                award = resume["awards"][i]
                row.update({
                    prefix + "name": award["name"],
                    prefix + "date": award["date"],
                    prefix + "level": award["level"],
                    prefix + "description": award["description"]
                })
            else:
                row.update({
                    prefix + "name": "",
                    prefix + "date": "",
                    prefix + "level": "",
                    prefix + "description": ""
                })
        
        data.append(row)
    
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False, encoding="utf_8_sig")
    print(f"简历数据已保存至 {filename}，共 {len(df)} 条记录")
    return df

# 生成1000份简历
if __name__ == "__main__":
    resumes = generate_resumes(10000)
    
    # 保存到CSV文件
    save_to_csv(resumes)
    


# In[ ]:




