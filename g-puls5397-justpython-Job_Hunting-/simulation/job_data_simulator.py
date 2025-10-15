#!/usr/bin/env python
# coding: utf-8

# In[1]:


import csv
import random
from datetime import datetime, timedelta
import numpy as np

# 扩展行业分类（30个行业）
industries = [
    '互联网/科技', '金融/银行', '教育/培训', '医疗/健康', '制造业', '零售/电商', 
    '房地产/建筑', '物流/供应链', '媒体/娱乐', '餐饮/酒店', '能源/环保', '政府/非营利', 
    '法律/咨询', '艺术/设计', '农业/林业', '汽车/交通', '生物/制药', '电信/通讯', 
    '体育/健身', '旅游/航空', '人力资源', '市场营销', '科学研究', '游戏开发', 
    '网络安全', '人工智能', '区块链', '大数据', '物联网', '航空航天'
]

# 扩展岗位标题（每个行业8-10个岗位）
job_titles = {
    '互联网/科技': ['前端开发工程师', '后端开发工程师', '数据科学家', '产品经理', 'UI/UX设计师', 
                'DevOps工程师', '测试工程师', '技术总监', '算法工程师', '云计算架构师'],
    '金融/银行': ['财务分析师', '投资顾问', '风险控制经理', '审计专员', '银行客户经理', 
               '信贷分析师', '精算师', '证券交易员', '财务总监', '金融产品经理'],
    '教育/培训': ['学科教师', '课程顾问', '教务主管', '教育研究员', '培训讲师', 
               '教育产品经理', '国际教育顾问', '在线教育运营', '教育技术专家', '留学顾问'],
    '医疗/健康': ['护士长', '临床药师', '医学检验师', '主治医师', '医疗顾问', 
               '康复治疗师', '医疗设备工程师', '公共卫生专员', '医疗数据分析师', '健康管理师'],
    '制造业': ['机械设计工程师', '生产主管', '质量经理', '工艺工程师', '设备维护工程师', 
             '供应链经理', '工业设计师', '制造总监', '自动化工程师', '精益生产专家'],
    '零售/电商': ['店长', '电商运营', '采购经理', '仓储主管', '商品策划', 
               '视觉营销设计师', '客户体验经理', '直播运营', '跨境电商专员', '新零售经理'],
    '房地产/建筑': ['房产经纪人', '估价师', '项目开发经理', '物业总监', '招商经理', 
                '建筑设计师', '室内设计师', '工程造价师', '城市规划师', '房地产分析师'],
    '物流/供应链': ['物流规划师', '仓储经理', '供应链分析师', '关务专员', '运输调度', 
                '采购专员', '物流解决方案专家', '国际货运代理', '供应链总监', '物流自动化工程师'],
    '媒体/娱乐': ['内容主编', '视频制作人', '广告策划', '新媒体运营', '记者', 
               '影视编导', '艺人经纪', '音效设计师', '游戏策划', '社交媒体经理'],
    '餐饮/酒店': ['行政总厨', '餐厅经理', '酒店前台主管', '食品研发', '营养顾问', 
               '宴会策划', '调酒师', '客房部经理', '品控专员', '餐饮品牌经理'],
    '能源/环保': ['能源工程师', '环境评估师', '光伏技术专家', '碳交易专员', '节能顾问', 
               '环保项目经理', '地质勘探师', '新能源产品经理', '水务工程师', '可持续发展专员'],
    '政府/非营利': ['政策研究员', '项目官员', '公共事务专员', '社区工作者', '基金会项目经理', 
                '社会工作者', '公共政策分析师', '慈善募捐专员', '政府关系经理', 'NGO传播主管'],
    # 其他行业的岗位类似配置...
}

# 对于未明确列出的行业，使用通用岗位
for industry in industries:
    if industry not in job_titles:
        job_titles[industry] = [
            f"{industry}专员", f"{industry}经理", f"{industry}分析师", 
            f"{industry}工程师", f"{industry}顾问", f"{industry}主管",
            f"{industry}助理", f"{industry}总监", f"{industry}专家", f"{industry}策划"
        ]

# 岗位经验要求
experience_levels = ['应届生', '1-3年', '3-5年', '5-8年', '8年以上']

# 教育要求
education_levels = ['不限', '大专', '本科', '硕士', '博士']

# 薪资类型
salary_types = ['月薪', '日薪', '年薪']

# 工作性质
employment_types = ['全职', '兼职', '实习']

# 城市列表（国内一二线城市+海外）
cities = [
    '北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '南京', '西安', '重庆',
    '苏州', '天津', '青岛', '郑州', '长沙', '宁波', '厦门', '大连', '济南', '沈阳',
    '香港', '澳门', '台北', '纽约', '伦敦', '东京', '新加坡', '悉尼', '洛杉矶', '柏林'
]

# 公司类型
company_types = [
    '上市公司', '国企', '外企', '创业公司', '独角兽企业', '合资企业', 
    '民营企业', '非营利组织', '政府机构', '事业单位'
]

# 岗位福利
benefits = [
    '五险一金', '带薪年假', '弹性工作', '年终奖金', '股票期权', '补充医疗保险',
    '免费三餐', '住房补贴', '交通补助', '年度旅游', '培训学习', '健身房',
    '定期体检', '节日福利', '员工宿舍', '加班补贴', '育儿补贴', '股权激励'
]

# 生成岗位详情描述
def generate_description(job_title, industry):
    # 根据行业和岗位生成专业描述
    descriptions = {
        '技术类': f"负责{job_title}相关工作，具备扎实的专业知识和解决问题的能力。",
        '管理类': f"负责团队管理和项目协调，制定工作计划并推动执行，达成业务目标。",
        '销售类': f"开拓市场资源，维护客户关系，完成销售指标，提供专业解决方案。",
        '服务类': f"提供优质客户服务，解决客户问题，提升客户满意度和品牌忠诚度。",
        '创意类': f"负责创意内容策划与执行，具备创新思维和艺术审美能力。",
        '研究类': f"开展专业领域研究，分析数据趋势，提供研究报告和解决方案。",
        '操作类': f"负责日常操作执行，确保工作流程顺畅，提高工作效率和质量。"
    }
    
    # 根据岗位名称判断类型
    job_type = '技术类'
    if '经理' in job_title or '总监' in job_title or '主管' in job_title:
        job_type = '管理类'
    elif '销售' in job_title or '顾问' in job_title or '经纪' in job_title:
        job_type = '销售类'
    elif '服务' in job_title or '客服' in job_title or '护理' in job_title:
        job_type = '服务类'
    elif '设计' in job_title or '创意' in job_title or '策划' in job_title:
        job_type = '创意类'
    elif '研究' in job_title or '分析' in job_title or '科学家' in job_title:
        job_type = '研究类'
    elif '操作' in job_title or '维护' in job_title or '生产' in job_title:
        job_type = '操作类'
    
    base_desc = descriptions[job_type]
    
    # 添加行业特定要求
    industry_specific = {
        '互联网/科技': "熟悉敏捷开发流程，掌握主流技术栈。",
        '金融/银行': "具备风险意识，熟悉金融法规和市场动态。",
        '教育/培训': "热爱教育事业，具备良好的表达和沟通能力。",
        '医疗/健康': "遵守医疗规范，具备专业资质和临床经验。",
        '制造业': "熟悉生产流程，掌握精益生产管理方法。"
    }
    
    specific = industry_specific.get(industry, "具备相关行业知识和经验。")
    
    # 随机添加额外要求
    extras = [
        "优秀的团队合作精神和沟通能力。",
        "能够承受工作压力，适应快节奏工作环境。",
        "具备创新思维和解决问题的能力。",
        "良好的英语读写能力。",
        "熟练使用相关专业软件和工具。",
        "具备项目管理经验者优先。"
    ]
    
    return f"{base_desc} {specific} {random.choice(extras)}"

# 生成薪资范围（基于行业、岗位类型和经验）
def generate_salary(salary_type, industry, job_title, employment_type):
    # 行业薪资系数
    industry_factors = {
        '互联网/科技': 1.4,
        '金融/银行': 1.5,
        '人工智能': 1.6,
        '区块链': 1.7,
        '大数据': 1.5,
        '游戏开发': 1.3,
        '生物/制药': 1.2,
        '能源/环保': 1.1,
        '政府/非营利': 0.9,
        '教育/培训': 1.0
    }
    factor = industry_factors.get(industry, 1.0)
    
    # 岗位级别系数（管理层更高）
    level_factor = 1.0
    if '总监' in job_title or '首席' in job_title:
        level_factor = 2.0
    elif '经理' in job_title or '主管' in job_title:
        level_factor = 1.5
    elif '助理' in job_title or '专员' in job_title:
        level_factor = 0.8
    elif '实习' in employment_type:
        level_factor = 0.4
    
    # 工作性质系数
    employment_factor = 1.0
    if employment_type == '兼职':
        employment_factor = 0.6
    elif employment_type == '实习':
        employment_factor = 0.4
    
    # 基本薪资计算
    if salary_type == '月薪':
        base = int(5000 * factor * level_factor * employment_factor)
        min_salary = max(3000, base + random.randint(-1000, 2000))
        max_salary = min_salary + int(min_salary * random.uniform(0.3, 0.8))
        return f"{min_salary}-{max_salary}"
    
    elif salary_type == '日薪':
        base = int(200 * factor * level_factor * employment_factor)
        min_salary = max(100, base + random.randint(-50, 100))
        max_salary = min_salary + int(min_salary * random.uniform(0.3, 0.6))
        return f"{min_salary}-{max_salary}"
    
    else:  # 年薪
        base = int(100000 * factor * level_factor * employment_factor)
        min_salary = max(50000, base + random.randint(-20000, 30000))
        max_salary = min_salary + int(min_salary * random.uniform(0.3, 0.7))
        return f"{min_salary}-{max_salary}"

# 生成随机截止日期（1-90天内）
def generate_deadline():
    return (datetime.now() + timedelta(days=random.randint(1, 90))).strftime('%Y-%m-%d')

# 生成公司规模
def generate_company_size():
    sizes = ['少于50人', '50-150人', '150-500人', '500-2000人', '2000人以上']
    weights = [0.2, 0.3, 0.25, 0.15, 0.1]
    return random.choices(sizes, weights=weights, k=1)[0]

# 生成岗位福利（随机3-5项）
def generate_benefits():
    num_benefits = random.randint(3, 5)
    return '，'.join(random.sample(benefits, num_benefits))

# 生成1000条岗位数据
def generate_job_data(num):
    jobs = []
    for _ in range(num):
        # 随机选择行业
        industry = random.choice(industries)
        
        # 从该行业中选择岗位标题
        title = random.choice(job_titles[industry])
        
        # 薪资类型
        salary_type = random.choice(salary_types)
        
        # 工作性质
        employment_type = random.choice(employment_types)
        
        # 地域要求
        if random.random() > 0.2:  # 80%岗位有地域要求
            if random.random() > 0.7:  # 30%为远程工作
                location = '远程'
            else:
                num_cities = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1], k=1)[0]
                location = '/'.join(random.sample(cities, num_cities))
        else:
            location = '不限地域'
        
        # 经验要求
        experience = random.choices(experience_levels, weights=[0.15, 0.3, 0.3, 0.15, 0.1], k=1)[0]
        
        # 教育要求
        education = random.choices(education_levels, weights=[0.1, 0.2, 0.5, 0.15, 0.05], k=1)[0]
        
        jobs.append({
            '岗位ID': f"JOB{str(_+1).zfill(5)}",
            '岗位分类': industry,
            '岗位标题': title,
            '岗位详情': generate_description(title, industry),
            '薪资待遇': salary_type,
            '薪资范围': generate_salary(salary_type, industry, title, employment_type),
            '工作性质': employment_type,
            '工作经验': experience,
            '教育要求': education,
            '招聘人数': str(random.randint(1, 10)),
            '招聘截止日期': generate_deadline(),
            '地域要求': location,
            '公司类型': random.choice(company_types),
            '公司规模': generate_company_size(),
            '岗位福利': generate_benefits()
        })
    return jobs

# 保存为CSV文件
def save_to_csv(jobs, filename='jobs_dataset.csv'):
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=jobs[0].keys())
        writer.writeheader()
        writer.writerows(jobs)

# 主程序
if __name__ == "__main__":
    print("开始生成岗位数据...")
    job_data = generate_job_data(1000)
    save_to_csv(job_data)
    print(f"已成功生成500条岗位数据并保存到 jobs_dataset.csv")
    print("字段包括：岗位ID, 岗位分类, 岗位标题, 岗位详情, 薪资待遇, 薪资范围, 工作性质, 工作经验, 教育要求, 招聘人数, 招聘截止日期, 地域要求, 公司类型, 公司规模, 岗位福利")


# In[ ]:




