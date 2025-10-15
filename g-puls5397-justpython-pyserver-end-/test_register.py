import requests
import json

# 测试注册接口
def test_register():
    url = 'http://127.0.0.1:8000/register/'
    data = {
        'username': 'testuser',
        'password': 'testpassword',
        'email': 'testuser@example.com',
        'phone': '13800138000',
        'gender': 'male'
    }
    
    response = requests.post(url, json=data)
    print(f"状态码: {response.status_code}")
    print(f"响应内容: {json.dumps(response.json(), indent=4, ensure_ascii=False)}")
    
    return response.json()

if __name__ == '__main__':
    test_register()