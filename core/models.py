from django.db import models

from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """
    Custom user model that extends the default Django user model.
    """
    # Add any additional fields you want to include in your custom user model
    # For example, you can add a 'bio' field:
    nickname = models.CharField("昵称", max_length=30, blank=True)
    avatar = models.URLField("头像", max_length=200, blank=True)
    phone = models.CharField("手机号", max_length=15, blank=True)
    is_phone_verified = models.BooleanField("手机号已验证", default=False)

    # 认证用户才有学号/院系
    student_id = models.CharField("学号", max_length=20, blank=True)
    department = models.CharField("院系", max_length=50, blank=True)
    is_verified_user = models.BooleanField("已认证用户", default=False)

    def __str__(self):
        return self.nickname or self.username