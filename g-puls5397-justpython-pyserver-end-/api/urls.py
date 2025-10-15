from django.urls import path
from .views import LoginView, RegisterView, ModifyUserView, PostResumeView, GetResumeView, GetUserEvaluateView, TestStorageView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('modify_user/', ModifyUserView.as_view(), name='modify_user'),
    path('post_resume/', PostResumeView.as_view(), name='post_resume'),
    path('get_resume/', GetResumeView.as_view(), name='get_resume'),
    path('get_user_evaluate/', GetUserEvaluateView.as_view(), name='get_user_evaluate'),
    path('test_storage/', TestStorageView.as_view(), name='test_storage'),
]