import requests
import json
import time

# 测试所有API接口
BASE_URL = 'http://127.0.0.1:8000'

def print_response(response):
    print(f"状态码: {response.status_code}")
    print(f"响应内容: {json.dumps(response.json(), indent=4, ensure_ascii=False)}")
    print("\n" + "-"*50 + "\n")

def test_register():
    print("测试注册接口...")
    url = f'{BASE_URL}/register/'
    data = {
        'username': 'testuser2',  # 使用新的用户名避免冲突
        'password': 'testpassword',
        'email': 'testuser2@example.com',
        'phone': '13800138002',
        'gender': 'male'
    }
    
    response = requests.post(url, json=data)
    print_response(response)
    return response.json()

def test_login():
    print("测试登录接口...")
    url = f'{BASE_URL}/login/'
    data = {
        'username': 'testuser2',
        'password': 'testpassword'
    }
    
    response = requests.post(url, json=data)
    print_response(response)
    return response.json()

def test_modify_user():
    print("测试修改用户信息接口...")
    url = f'{BASE_URL}/modify_user/'
    data = {
        'username': 'testuser2',
        'email': 'updated_email@example.com',
        'phone': '13900139002',
        'gender': 'female',
        'expectedWorkType': '全职',
        'position': '软件工程师',
        'salary': '15k-20k',
        'city': '北京',
        'anotherCity': '上海'
    }
    
    response = requests.post(url, json=data)
    print_response(response)
    return response.json()

def test_post_resume():
    print("测试上传简历接口...")
    url = f'{BASE_URL}/post_resume/'
    data = {
        'username': 'testuser2',
        'name': '测试简历',
        'education': '本科',
        'school': '测试大学',
        'major': '计算机科学与技术',
        'experience': '3年工作经验',
        'skills': '熟悉Python, Django, RESTful API设计',
        'projects': [
            {
                'name': '项目1',
                'description': '这是一个测试项目',
                'role': '开发者',
                'duration': '2020-2021'
            }
        ],
        'self_evaluation': '我是一个积极主动、善于学习的开发者'
    }
    
    response = requests.post(url, json=data)
    print_response(response)
    resume_id = response.json().get('resume_id')
    return resume_id

def test_get_resume(resume_id=None):
    print("测试获取简历信息接口...")
    url = f'{BASE_URL}/get_resume/'
    data = {
        'username': 'testuser2'
    }
    
    if resume_id:
        data['resumeIDList'] = [resume_id]
    
    response = requests.post(url, json=data)
    print_response(response)
    return response.json()

def test_get_user_evaluate():
    print("测试获取用户评价接口...")
    url = f'{BASE_URL}/get_user_evaluate/'
    data = {
        'username': 'testuser2'
    }
    
    response = requests.post(url, json=data)
    print_response(response)
    return response.json()

def run_all_tests():
    print("开始测试所有API接口...\n")
    
    # 注册新用户
    register_result = test_register()
    time.sleep(1)
    
    # 登录
    login_result = test_login()
    time.sleep(1)
    
    # 修改用户信息
    modify_result = test_modify_user()
    time.sleep(1)
    
    # 上传简历
    resume_id = test_post_resume()
    time.sleep(1)
    
    # 获取简历信息
    resume_result = test_get_resume(resume_id)
    time.sleep(1)
    
    # 获取用户评价
    evaluate_result = test_get_user_evaluate()
    
    print("所有API接口测试完成！")

if __name__ == '__main__':
    run_all_tests()