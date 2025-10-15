import requests
import json
import uuid

# 测试添加用户评价数据（通过Django shell）
def test_add_user_evaluate():
    # 这个脚本不是直接测试API接口，而是通过Django shell添加测试数据
    # 实际使用时，需要在Django shell中执行以下代码
    
    print("请在Django shell中执行以下代码来添加用户评价数据：")
    print("""
    from api.models import UserEvaluate, User
    import uuid
    
    # 确保用户存在
    try:
        user = User.objects.get(username='testuser')
        
        # 创建用户评价
        evaluate = UserEvaluate.objects.create(
            id=str(uuid.uuid4()),
            username='testuser',
            company='测试公司',
            position='软件工程师',
            start_time='2022-01-01',
            end_time='2022-12-31',
            content='这是一条测试评价，该用户在公司表现优秀。',
            score=4.5
        )
        
        print(f'成功添加用户评价，ID: {evaluate.id}')
    except User.DoesNotExist:
        print('用户不存在，请先注册用户')
    """)
    
    print("\n或者，您可以运行以下命令启动Django shell：")
    print("python manage.py shell")

if __name__ == '__main__':
    test_add_user_evaluate()