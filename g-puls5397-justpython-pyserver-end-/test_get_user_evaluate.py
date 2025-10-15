import requests
import json

# 测试获取用户评价接口
def test_get_user_evaluate():
    url = 'http://127.0.0.1:8000/get_user_evaluate/'
    data = {
        'username': 'testuser'  # 使用已注册的用户名
    }
    
    response = requests.post(url, json=data)
    print(f"状态码: {response.status_code}")
    print(f"响应内容: {json.dumps(response.json(), indent=4, ensure_ascii=False)}")
    
    return response.json()

if __name__ == '__main__':
    test_get_user_evaluate()