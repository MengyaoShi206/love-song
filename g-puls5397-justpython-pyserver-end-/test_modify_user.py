import requests
import json

# 测试修改用户信息接口
def test_modify_user():
    url = 'http://127.0.0.1:8000/modify_user/'
    data = {
        'username': 'testuser',  # 使用已注册的用户名
        'email': 'updated_email@example.com',
        'phone': '13900139000',
        'gender': 'female',
        'expectedWorkType': '全职',
        'position': '软件工程师',
        'salary': '15k-20k',
        'city': '北京',
        'anotherCity': '上海'
    }
    
    response = requests.post(url, json=data)
    print(f"状态码: {response.status_code}")
    print(f"响应内容: {json.dumps(response.json(), indent=4, ensure_ascii=False)}")
    
    return response.json()

if __name__ == '__main__':
    test_modify_user()