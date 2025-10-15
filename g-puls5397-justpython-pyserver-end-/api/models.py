from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

# 继承了默认用户类
# 所以不需要自己定义密码、邮箱之类的，自带了
class User(AbstractUser):
    username = models.CharField(max_length=50, unique=True, verbose_name='用户名/电话/邮箱')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='电话')
    gender = models.CharField(max_length=10, blank=True, null=True, verbose_name='性别')
    avatar = models.CharField(max_length=200, blank=True, null=True, verbose_name='头像')
    ideal_job_type = models.CharField(max_length=20, blank=True, null=True, verbose_name='期望工作类型')
    ideal_job = models.CharField(max_length=50, blank=True, null=True, verbose_name='期望职位')
    ideal_salary = models.CharField(max_length=50, blank=True, null=True, verbose_name='期望薪资')
    ideal_city = models.CharField(max_length=50, blank=True, null=True, verbose_name='期望工作城市')
    another_city = models.JSONField(default=list, blank=True, null=True, verbose_name='其他感兴趣城市')
    ideal_area = models.CharField(max_length=50, blank=True, null=True, verbose_name='期望行业')
    card_id = models.CharField(max_length=50, blank=True, null=True, verbose_name='电子名片标识')
    resume_id_list = models.JSONField(default=list, blank=True, null=True, verbose_name='简历标识列表')
    project_id_list = models.JSONField(default=list, blank=True, null=True, verbose_name='我的项目标识列表')
    delivery_record = models.JSONField(default=list, blank=True, null=True, verbose_name='投递记录列表/投递岗位标识列表')
    homepage_hot = models.IntegerField(default=0, blank=True, null=True, verbose_name='主页热度')
    home_page_type = models.CharField(max_length=50, blank=True, null=True, verbose_name='主页分类')
    homepage_activity = models.IntegerField(default=0, blank=True, null=True, verbose_name='主页活跃度')
    money = models.IntegerField(default=0, blank=True, null=True, verbose_name='用户余额')
    certificates = models.JSONField(default=list, blank=True, null=True, verbose_name='工作证明列表/id')
    contract = models.CharField(max_length=200, blank=True, null=True, verbose_name='工作协议')
    signature = models.CharField(max_length=200, blank=True, null=True, verbose_name='个性签名')
    priority = models.IntegerField(default=0, blank=True, null=True, verbose_name='用户权限等级')
    workbench = models.BooleanField(default=False, blank=True, null=True, verbose_name='是否已开通工作台')
    
    class Meta:
        verbose_name = '用户'
        verbose_name_plural = verbose_name
        
    def __str__(self):
        return self.username

class Resume(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resumes')
    permission = models.JSONField(default=dict, blank=True, null=True)
    title = models.CharField(max_length=100, blank=True, null=True)
    desc = models.TextField(blank=True, null=True)
    photo = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=200, blank=True, null=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    birthday = models.CharField(max_length=20, blank=True, null=True)
    education = models.JSONField(default=list, blank=True, null=True)
    graduationYear = models.CharField(max_length=20, blank=True, null=True)
    workExperience = models.JSONField(default=list, blank=True, null=True)
    projectExperience = models.JSONField(default=list, blank=True, null=True)
    prize = models.JSONField(default=list, blank=True, null=True)
    scientific = models.JSONField(default=list, blank=True, null=True)
    introduction = models.TextField(blank=True, null=True)
    skill = models.JSONField(default=list, blank=True, null=True)
    resumeFile = models.JSONField(default=dict, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '简历'
        verbose_name_plural = verbose_name
        
    def __str__(self):
        return f"{self.user.username}的简历 - {self.title}"

class UserEvaluate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=50, blank=True, null=True)
    company = models.CharField(max_length=100, blank=True, null=True)
    PostingID = models.CharField(max_length=50, blank=True, null=True)
    rate = models.IntegerField(default=0, blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    createAt = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = '用户评价'
        verbose_name_plural = verbose_name
        
    def __str__(self):
        return f"{self.username}在{self.company}的评价"
