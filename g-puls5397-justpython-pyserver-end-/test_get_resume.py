import requests
import json

# 测试获取简历信息接口
def test_get_resume():
    url = 'http://127.0.0.1:8000/get_resume/'
    data = {
        'username': 'testuser',  # 使用已注册的用户名
        # 可以指定要获取的简历ID列表，如果不指定则获取所有简历
        # 'resumeIDList': ['resume_id_1', 'resume_id_2']
    }
    
    response = requests.post(url, json=data)
    print(f"状态码: {response.status_code}")
    print(f"响应内容: {json.dumps(response.json(), indent=4, ensure_ascii=False)}")
    
    return response.json()

if __name__ == '__main__':
    test_get_resume()