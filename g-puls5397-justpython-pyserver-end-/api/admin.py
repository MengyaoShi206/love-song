from django.contrib import admin
from .models import User, Resume, UserEvaluate

# Register your models here.
admin.site.register(User)
admin.site.register(Resume)
admin.site.register(UserEvaluate)
