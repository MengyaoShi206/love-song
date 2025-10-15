from django.shortcuts import render
from django.contrib.auth import authenticate, login
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserSerializer, ResumeSerializer, UserEvaluateSerializer
from .models import User, Resume, UserEvaluate
import uuid
from django.db import transaction

# Create your views here.
class RegisterView(APIView):
    """
    用户注册视图
    """
    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        phone = request.data.get('phone')
        gender = request.data.get('gender')
        avatar = request.data.get('avatar')
        
        # 验证必填字段
        if not username or not email:
            return Response({
                'code': 400,
                'message': '用户名和邮箱不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 检查用户名是否已存在
        if User.objects.filter(username=username).exists():
            return Response({
                'code': 400,
                'message': '用户名已存在'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 检查邮箱是否已存在
        if User.objects.filter(email=email).exists():
            return Response({
                'code': 400,
                'message': '邮箱已存在'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 创建用户
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        
        # 更新其他字段
        if phone:
            user.phone = phone
        if gender:
            user.gender = gender
        if avatar:
            user.avatar = avatar
        
        user.save()
        
        # 登录用户
        login(request, user)
        
        # 返回用户信息
        serializer = UserSerializer(user)
        return Response({
            'code': 200,
            'data': serializer.data,
            'message': '用户注册成功'
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    用户登录视图
    """
    def post(self, request):
        username = request.data.get('usrname')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({
                'code': 400,
                'message': '用户名和密码不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 尝试使用用户名、邮箱或电话号码登录
        user = None
        # 尝试用户名登录
        user = authenticate(username=username, password=password)
        
        # 如果用户名登录失败，尝试邮箱登录
        if user is None:
            try:
                user_obj = User.objects.get(email=username)
                user = authenticate(username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass
        
        # 如果邮箱登录失败，尝试电话登录
        if user is None:
            try:
                user_obj = User.objects.get(phone=username)
                user = authenticate(username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass
        
        if user is not None:
            login(request, user)
            serializer = UserSerializer(user)
            return Response({
                'code': 200,
                'data': serializer.data,
                'message': '用户登录成功'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'code': 401,
                'message': '用户名或密码错误'
            }, status=status.HTTP_401_UNAUTHORIZED)


class ModifyUserView(APIView):
    """
    个人信息更新视图
    """
    def post(self, request):
        username = request.data.get('username')
        
        # 验证用户名是否存在
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({
                'code': 404,
                'message': '用户不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 更新用户信息
        fields_to_update = [
            'email', 'password', 'phone', 'gender', 'avatar', 'ideal_job_type',
            'ideal_job', 'ideal_salary', 'ideal_city', 'anotherCity', 'ideal_area'
        ]
        
        for field in fields_to_update:
            value = request.data.get(field)
            if value is not None:
                # 特殊处理密码字段
                if field == 'password':
                    user.set_password(value)
                # 特殊处理anotherCity字段，映射到another_city
                elif field == 'anotherCity':
                    user.another_city = value
                else:
                    setattr(user, field, value)
        
        user.save()
        
        return Response({
            'code': 200,
            'message': '个人信息更新成功'
        }, status=status.HTTP_200_OK)


class PostResumeView(APIView):
    """
    上传简历视图
    """
    @transaction.atomic
    def post(self, request):
        # 获取用户名
        username = request.data.get('username')
        if not username:
            return Response({
                'code': 400,
                'message': '用户名不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 验证用户是否存在
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({
                'code': 404,
                'message': '用户不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 验证简历数据
        serializer = ResumeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'code': 400,
                'message': '简历数据无效',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 创建简历
        resume_id = str(uuid.uuid4())
        resume_data = serializer.validated_data
        resume_data['id'] = resume_id
        
        resume = Resume.objects.create(
            id=resume_id,
            user=user,
            **resume_data
        )
        
        # 更新用户的简历ID列表
        if user.resume_id_list is None:
            user.resume_id_list = []
        user.resume_id_list.append(str(resume.id))
        user.save()
        
        return Response({
            'code': 200,
            'message': '简历上传成功',
            'resume_id': str(resume.id)
        }, status=status.HTTP_201_CREATED)

class GetResumeView(APIView):
    """
    获取个人简历信息视图
    """
    def post(self, request):
        username = request.data.get('username')
        resume_id_list = request.data.get('resumeIDList', [])
        
        # 验证用户名是否存在
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({
                'code': 404,
                'message': '用户不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 如果没有提供简历ID列表，则获取用户的所有简历
        if not resume_id_list:
            resume_id_list = user.resume_id_list or []
        
        # 获取简历信息
        resume_list = []
        for resume_id in resume_id_list:
            try:
                resume = Resume.objects.get(id=resume_id, user=user)
                serializer = ResumeSerializer(resume)
                resume_list.append(serializer.data)
            except Resume.DoesNotExist:
                # 如果简历不存在，跳过
                continue
        
        return Response({
            'code': 200,
            'resumeList': resume_list,
            'message': '全部简历信息获取成功'
        }, status=status.HTTP_200_OK)

class GetUserEvaluateView(APIView):
    """
    获取用户实习/工作评价视图
    """
    def post(self, request):
        username = request.data.get('username')
        
        # 验证用户名是否存在
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({
                'code': 404,
                'message': '用户不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 获取用户评价
        evaluates = UserEvaluate.objects.filter(username=username)
        serializer = UserEvaluateSerializer(evaluates, many=True)
        
        # 获取用户信息
        user_serializer = UserSerializer(user)
        
        return Response({
            'code': 200,
            'data': user_serializer.data,
            'evaluates': serializer.data,
            'message': '获取用户评价成功'
        }, status=status.HTTP_200_OK)


from .storage_example import storage_example

class TestStorageView(APIView):
    """
    测试分布式存储系统视图
    """
    def get(self, request):
        # 执行存储系统测试
        storage_example()
        
        return Response({
            'code': 200,
            'message': '存储系统测试完成，请查看服务器日志获取详细信息'
        }, status=status.HTTP_200_OK)
