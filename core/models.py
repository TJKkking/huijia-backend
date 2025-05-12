from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """
    Custom user model that extends the default Django user model.
    """
    nickname = models.CharField("昵称", max_length=30, blank=True)
    avatar = models.URLField("头像", max_length=200, blank=True)
    gender = models.CharField("性别", max_length=10, choices=[
        ("男", "男"),
        ("女", "女"),
        ("其他", "其他"),
        ("保密", "保密"),
    ], blank=True)
    phone = models.CharField("手机号", max_length=15, blank=True, unique=True)
    is_phone_verified = models.BooleanField("手机号已验证", default=False)

    openid = models.CharField("微信 OpenID", max_length=128, unique=True, blank=True, null=True, db_index=True)

    # 认证用户才有学号/院系
    student_id = models.CharField("学号", max_length=20, blank=True)
    department = models.CharField("院系", max_length=50, blank=True)
    is_verified_user = models.BooleanField("已认证用户", default=False)
    verification_submitted_at = models.DateTimeField("认证提交时间", blank=True, null=True)
    verification_approved_at = models.DateTimeField("认证审核时间", blank=True, null=True)

    def __str__(self):
        return self.nickname or self.username
    
class Category(models.Model):
    """
    Model representing a category for posts.
    """
    name = models.CharField("分类名称", max_length=100, unique=True)
    slug = models.SlugField(
        "URL 别名", max_length=100, unique=True, db_index=True
    )
    description = models.TextField("分类描述", blank=True)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE,
        related_name='children', blank=True, null=True
    )
    created_at = models.DateTimeField("创建时间", default=timezone.now, db_index=True)

    class Meta:
        verbose_name = "分类"
        verbose_name_plural = "分类"
        ordering = ["name"]

    def __str__(self):
        return self.name
    
class Tag(models.Model):
    """
    Model representing a tag for posts.
    """
    name = models.CharField("标签名称", max_length=100, unique=True)
    slug = models.SlugField(
        "URL 别名", max_length=50, unique=True, db_index=True
    )
    created_at = models.DateTimeField("创建时间", default=timezone.now, db_index=True)

    class Meta:
        verbose_name = "标签"
        verbose_name_plural = "标签"
        ordering = ["name"]

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
class Post(models.Model):
    """
    Model representing a post.
    """
    title = models.CharField("标题", max_length=200)
    content = models.TextField("内容")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="posts")
    created_at = models.DateTimeField("创建时间", default=timezone.now)
    updated_at = models.DateTimeField("更新时间", auto_now=True)
    is_anonymous = models.BooleanField("匿名", default=False)

    status = models.CharField(
        "状态", max_length=10, choices=[
            ("draft", "草稿"),
            ("published", "已发布"),
            ("archived", "已归档"),
        ], default="draft"
    )
    is_pinned = models.BooleanField("是否置顶", default=False)

    # 分类，标签
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, 
        related_name="posts", blank=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="posts")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
    
class Comment(models.Model):
    """
    Model representing a comment on a post.
    """
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    content = models.TextField("内容")
    created_at = models.DateTimeField("创建时间", default=timezone.now)
    # updated_at = models.DateTimeField("更新时间", auto_now=True)

    # 支持匿名评论
    is_anonymous = models.BooleanField("匿名", default=False)

    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, 
        related_name="replies", blank=True, null=True, db_index=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Comment by {self.author} on {self.post}"
    
class Action(models.Model):
    """
    用于点赞、收藏、举报等可复用的行为模型
    """
    # 举报后期考虑独立
    ACTION_TYPES = (
        ("like", "点赞"),
        ("favorite", "收藏"),
        ("report", "举报"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="actions", db_index=True
    )
    action_type = models.CharField(
        "类型", max_length=10, choices=ACTION_TYPES
    )

    # Generic ForeignKey 指向 Post 或 Comment
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, db_index=True)
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey("content_type", "object_id")
    
    created_at = models.DateTimeField("操作时间", default=timezone.now, db_index=True)

    class Meta:
        unique_together = ("user", "action_type", "content_type", "object_id")

    def __str__(self):
        return f"{self.user} {self.action_type} {self.target}"
    
class Conversation(models.Model):
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name='conversations'
    )
    created_at = models.DateTimeField("创建时间", default=timezone.now, db_index=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)
    last_message = models.ForeignKey(
        'PrivateMessage', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+', db_index=True)

    def __str__(self):
        return f"Conversation ({', '.join([u.username for u in self.participants.all()])})"

# 8. 私信模型（支持软删除）
class PrivateMessage(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE,
        related_name='messages', db_index=True
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='sent_messages', db_index=True
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='received_messages', db_index=True
    )
    content = models.TextField("消息内容")
    sent_at = models.DateTimeField(
        "发送时间", default=timezone.now, db_index=True
    )
    is_read = models.BooleanField("已读", default=False)
    sender_deleted = models.BooleanField("发送者已删除", default=False)
    receiver_deleted = models.BooleanField("接收者已删除", default=False)

    class Meta:
        ordering = ['sent_at']

class Notification(models.Model):
    NOTIF_TYPES = (
        ("comment", "评论通知"),
        ("reply", "回复通知"),
        ("mention", "@ 通知"),
        ("system", "系统通知"),
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications', db_index=True
    )
    notif_type = models.CharField("通知类型", max_length=10, choices=NOTIF_TYPES)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="关联对象的内容类型，如 Post 或 Comment"
    )
    object_id = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="关联对象的主键，如 Post.id 或 Comment.id"
    )
    target = GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField(
        "创建时间", default=timezone.now, db_index=True
    )
    is_read = models.BooleanField("已读", default=False)
    extra_data = models.JSONField("扩展数据", blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification(type={self.notif_type}, recipient={self.recipient.username})"

    def is_orphan(self):
        """
        判断当前通知是否已失效（关联对象被删除）。
        """
        return self.content_type is None or self.target is None

    def mark_orphan(self):
        """
        通知失效处理，例如标记为已读或归档。
        """
        if self.is_orphan():
            self.is_read = True
            self.save()