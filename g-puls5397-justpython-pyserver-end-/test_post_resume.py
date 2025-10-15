import requests
import json
import uuid

# 测试上传简历接口
def test_post_resume():
    url = 'http://127.0.0.1:8000/post_resume/'
    data = {
        'username': 'testuser',  # 使用已注册的用户名
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
    print(f"状态码: {response.status_code}")
    print(f"响应内容: {json.dumps(response.json(), indent=4, ensure_ascii=False)}")
    
    return response.json()

if __name__ == '__main__':
    test_post_resume()