from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from .models import (
    User, Category, Tag, Post, Comment, 
    Action, Conversation, PrivateMessage, Notification, StudentIDUpload
)
import logging

logger = logging.getLogger(__name__)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'nickname', 'avatar', 'gender',
            'phone', 'is_phone_verified', 'student_id', 'department',
            'is_verified_user', 'verification_submitted_at',
            'verification_approved_at', 'openid'
        ]
        read_only_fields = [
            'is_phone_verified', 'is_verified_user',
            'verification_submitted_at', 'verification_approved_at',
            'openid', 'username'
        ]

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'parent', 'created_at']
        read_only_fields = ['slug', 'created_at']

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'created_at']
        read_only_fields = ['slug', 'created_at']

class CommentSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    replies_count = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'post', 'author', 'content', 'created_at',
            'is_anonymous', 'parent', 'replies', 'replies_count'
        ]
        read_only_fields = ['created_at']

    def get_author(self, obj):
        if obj.is_anonymous:
            return {
                'id': None,
                'nickname': '匿名用户',
                'avatar': getattr(settings, 'DEFAULT_ANONYMOUS_AVATAR', '/static/images/anonymous.png')
            }
        return UserSerializer(obj.author).data

    def get_replies_count(self, obj):
        return obj.replies.count()

    def get_replies(self, obj):
        # Only get direct replies to prevent deep nesting
        queryset = obj.replies.all().order_by('created_at')
        return CommentSerializer(queryset, many=True, context=self.context).data

class PostSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    
    # Write-only fields for category and tags
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True,
        allow_null=True,
        required=False
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        source='tags',
        many=True,
        write_only=True,
        required=False
    )

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'content', 'author', 'created_at', 'updated_at',
            'is_anonymous', 'status', 'is_pinned',
            'category', 'tags',  # Read-only nested fields
            'category_id', 'tag_ids'  # Write-only fields
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_author(self, obj):
        if obj.is_anonymous:
            return {
                'id': None,
                'nickname': '匿名用户',
                'avatar': getattr(settings, 'DEFAULT_ANONYMOUS_AVATAR', '/static/images/anonymous.png')
            }
        return UserSerializer(obj.author).data

class ActionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    target_object = serializers.SerializerMethodField()

    class Meta:
        model = Action
        fields = [
            'id', 'user', 'action_type', 'content_type', 'object_id',
            'created_at', 'target_object'
        ]
        read_only_fields = ['user', 'created_at']

    def get_target_object(self, obj):
        if not obj.target:
            return None
            
        if isinstance(obj.target, Post):
            return {
                'type': 'post',
                'id': obj.target.id,
                'title': obj.target.title
            }
        elif isinstance(obj.target, Comment):
            return {
                'type': 'comment',
                'id': obj.target.id,
                'content_preview': obj.target.content[:50]
            }
        return None

class PrivateMessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)

    class Meta:
        model = PrivateMessage
        fields = [
            'id', 'conversation', 'sender', 'receiver',
            'content', 'sent_at', 'is_read',
            'sender_deleted', 'receiver_deleted'
        ]
        read_only_fields = ['sender', 'sent_at']

class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    last_message = PrivateMessageSerializer(read_only=True)
    participant_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        many=True,
        write_only=True,
        required=False,
        help_text="List of user IDs to add as participants"
    )

    class Meta:
        model = Conversation
        fields = [
            'id', 'participants', 'created_at', 'updated_at', 
            'last_message', 'participant_ids'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        participant_ids = validated_data.pop('participant_ids', [])
        conversation = super().create(validated_data)
        
        # Add participants
        if participant_ids:
            conversation.participants.add(*participant_ids)
        
        return conversation

    def update(self, instance, validated_data):
        participant_ids = validated_data.pop('participant_ids', None)
        conversation = super().update(instance, validated_data)
        
        # Update participants if provided
        if participant_ids is not None:
            conversation.participants.clear()
            conversation.participants.add(*participant_ids)
        
        return conversation

class NotificationSerializer(serializers.ModelSerializer):
    recipient = UserSerializer(read_only=True)
    target_object = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'notif_type', 'content_type',
            'object_id', 'created_at', 'is_read', 'extra_data',
            'target_object'
        ]
        read_only_fields = ['recipient', 'created_at']

    def get_target_object(self, obj):
        if not obj.target:
            return None
            
        if isinstance(obj.target, Post):
            return {
                'type': 'post',
                'id': obj.target.id,
                'title': obj.target.title
            }
        elif isinstance(obj.target, Comment):
            return {
                'type': 'comment',
                'id': obj.target.id,
                'content_preview': obj.target.content[:50]
            }
        return None 

class StudentIDUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentIDUpload
        fields = ['id', 'image', 'uploaded_at', 'status']
        read_only_fields = ['id', 'uploaded_at', 'status']

    def create(self, validated_data):
        return StudentIDUpload.objects.create(
            user=self.context['request'].user,
            **validated_data
        )