from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'gender', 'avatar', 'ideal_job_type', 'ideal_job', 'ideal_salary',
                 'ideal_city', 'another_city', 'ideal_area', 'card_id', 'resume_id_list', 'project_id_list',
                 'delivery_record', 'homepage_hot', 'home_page_type', 'homepage_activity', 'money', 'certificates']
        extra_kwargs = {
            'password': {'write_only': True}
        }

class ResumeSerializer(serializers.Serializer):
    permission = serializers.JSONField(required=False)
    title = serializers.CharField(required=False, allow_blank=True)
    desc = serializers.CharField(required=False, allow_blank=True)
    id = serializers.CharField(required=False, allow_blank=True)
    photo = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    name = serializers.CharField(required=False, allow_blank=True)
    gender = serializers.CharField(required=False, allow_blank=True)
    birthday = serializers.CharField(required=False, allow_blank=True)
    education = serializers.ListField(required=False, default=list)
    graduationYear = serializers.CharField(required=False, allow_blank=True)
    workExperience = serializers.ListField(required=False, default=list)
    projectExperience = serializers.ListField(required=False, default=list)
    prize = serializers.ListField(required=False, default=list)
    scientific = serializers.ListField(required=False, default=list)
    introduction = serializers.CharField(required=False, allow_blank=True)
    skill = serializers.ListField(required=False, default=list)
    resumeFile = serializers.JSONField(required=False)

class UserEvaluateSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, allow_blank=True)
    company = serializers.CharField(required=False, allow_blank=True)
    PostingID = serializers.CharField(required=False, allow_blank=True)
    rate = serializers.IntegerField(required=False)
    content = serializers.CharField(required=False, allow_blank=True)
    createAt = serializers.CharField(required=False, allow_blank=True)