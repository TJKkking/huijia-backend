from django.shortcuts import render
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django.utils import timezone
import logging
import requests
import uuid
import os
from datetime import datetime
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .models import (
    User, Category, Tag, Post, Comment,
    Action, Conversation, PrivateMessage, Notification, StudentIDUpload
)
from .serializers import (
    UserSerializer, CategorySerializer, TagSerializer,
    PostSerializer, CommentSerializer, ActionSerializer,
    ConversationSerializer, PrivateMessageSerializer,
    NotificationSerializer, StudentIDUploadSerializer
)
from .permissions import (
    IsRegistered,
    IsAuthenticatedAndVerified,
    IsOwnerOrReadOnly,
    IsSelfOrAdmin
)

logger = logging.getLogger(__name__)
User = get_user_model()

WX_APPID = getattr(settings, "WECHAT_APP_ID", "your_appid")
WX_SECRET = getattr(settings, "WECHAT_APP_SECRET", "your_secret")

# 封装：生成随机用户名
def generate_username():
    return "wxuser_" + uuid.uuid4().hex[:10]

# 封装：调用微信接口换 openid + session_key
def get_wechat_session_info(code):
    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        'appid': WX_APPID,
        'secret': WX_SECRET,
        'js_code': code,
        'grant_type': 'authorization_code'
    }
    try:
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        raise AuthenticationFailed("请求微信超时")
    except requests.exceptions.RequestException as e:
        raise AuthenticationFailed(f"请求微信失败：{str(e)}")

# 封装：签发 JWT 并返回过期时间
def generate_jwt_token_for_user(user):
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token
    return {
        'refresh': str(refresh),
        'access': str(access),
        'access_expires': datetime.fromtimestamp(access['exp']).isoformat()
    }

class WXLoginView(APIView):
    permission_classes = []  

    def post(self, request, *args, **kwargs):
        code = request.data.get('code')
        if not code:
            return Response({'error': 'Code is required.'}, status=status.HTTP_400_BAD_REQUEST)

        wx_data = get_wechat_session_info(code)
        openid = wx_data.get('openid')
        session_key = wx_data.get('session_key')
        unionid = wx_data.get('unionid')

        if not openid:
            return Response({
                'error': wx_data.get('errmsg', '未获取到openid'),
                'detail': wx_data
            }, status=status.HTTP_400_BAD_REQUEST)

        nickname_from_frontend = request.data.get('nickName')
        avatar_from_frontend = request.data.get('avatarUrl')

        try:
            user, created = User.objects.get_or_create(
                openid=openid,
                defaults={
                    'username': openid,
                    'nickname': nickname_from_frontend or f"微信用户_{openid[-4:]}",
                    'avatar': avatar_from_frontend or settings.DEFAULT_AVATAR_URL,
                    # 'unionid': unionid
                }
            )

            if not created:
                update_fields = []
                if nickname_from_frontend and not user.nickname:
                    user.nickname = nickname_from_frontend
                    update_fields.append('nickname')
                if avatar_from_frontend and not user.avatar:
                    user.avatar = avatar_from_frontend
                    update_fields.append('avatar')
                if unionid and not user.unionid:
                    user.unionid = unionid
                    update_fields.append('unionid')
                if update_fields:
                    user.save(update_fields=update_fields)

            logger.info(f"User {user.id} login via WeChat: openid={openid}")

        except Exception as e:
            logger.error(f"User account creation/login failed: {str(e)}")
            return Response({'error': f'User account processing failed: {str(e)}'}, status=500)

        tokens = generate_jwt_token_for_user(user)
        user_data = UserSerializer(user, context={'request': request}).data

        return Response({
            'access': tokens['access'],
            'refresh': tokens['refresh'],
            'access_expires': tokens['access_expires'],
            'user': user_data
        }, status=200)

# 当前用户信息接口
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = UserSerializer(user, context={'request': request}).data
        return Response(data, status=200)

class BaseViewSet(viewsets.ModelViewSet):
    def get_permissions(self):
        # DEBUG 时绕过所有权限，直接放行
        if settings.DEBUG:
            return [permissions.AllowAny()]
        # 否则走正常逻辑
        return super().get_permissions()

class UserViewSet(BaseViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'nickname', 'student_id']

    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            return [permissions.IsAdminUser()]
        elif self.action in ['update', 'partial_update']:
            return [permissions.IsAuthenticated(), IsSelfOrAdmin()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=['get', 'put', 'patch'])
    def me(self, request):
        if request.method in ['PUT', 'PATCH']:
            serializer = self.get_serializer(request.user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        else:
            serializer = self.get_serializer(request.user)
        return Response(serializer.data)

class CategoryViewSet(BaseViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticatedOrReadOnly()]

class TagViewSet(BaseViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticatedOrReadOnly()]

class PostViewSet(BaseViewSet):
    serializer_class = PostSerializer
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.action in ['like', 'favorite']:
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = Post.objects.all()

        # Filter by category
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category_id=category)

        # Filter by tags
        tags = self.request.query_params.getlist('tags', [])
        if tags:
            queryset = queryset.filter(tags__id__in=tags).distinct()

        # Filter by status
        status = self.request.query_params.get('status', None)
        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise permissions.NotAuthenticated()
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        serializer.save()  # Don't update author on update

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        post = self.get_object()
        post_content_type = ContentType.objects.get_for_model(Post)
        action, created = Action.objects.get_or_create(
            user=request.user,
            content_type=post_content_type,
            object_id=post.id,
            action_type='like'
        )
        if not created:
            action.delete()
            liked = False
        else:
            liked = True
        
        # Refresh post to get updated counts
        post.refresh_from_db()
        serializer = self.get_serializer(post)
        return Response({
            'status': 'unliked' if not liked else 'liked',
            'post': serializer.data
        })

    @action(detail=True, methods=['post'])
    def favorite(self, request, pk=None):
        post = self.get_object()
        post_content_type = ContentType.objects.get_for_model(Post)
        action, created = Action.objects.get_or_create(
            user=request.user,
            content_type=post_content_type,
            object_id=post.id,
            action_type='favorite'
        )
        if not created:
            action.delete()
            favorited = False
        else:
            favorited = True
        
        # Refresh post to get updated counts
        post.refresh_from_db()
        serializer = self.get_serializer(post)
        return Response({
            'status': 'unfavorited' if not favorited else 'favorited',
            'post': serializer.data
        })
    def get_permissions(self):
        # 发帖、更新、删除：必须登录且已认证
        if self.action in ['create']:
            return [IsAuthenticatedAndVerified()]

        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticatedAndVerified(), IsOwnerOrReadOnly()]

        # 点赞/收藏：必须登录（注册用户）
        elif self.action in ['like', 'favorite']:
            return [IsRegistered()]

        # 浏览列表/详情：任何人都能看
        return [permissions.AllowAny()]

class CommentViewSet(BaseViewSet):
    serializer_class = CommentSerializer
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return Comment.objects.filter(post_id=self.kwargs['post_pk'])

    def perform_create(self, serializer):
        post = get_object_or_404(Post, pk=self.kwargs['post_pk'])
        serializer.save(
            author=self.request.user,
            post=post
        )

    def perform_update(self, serializer):
        serializer.save()  # Don't update author on update

    def get_permissions(self):
        # 发布评论：必须登录（注册用户）
        if self.action == 'create':
            return [IsRegistered()]

        # 修改/删除评论：只能评论的作者本人
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsOwnerOrReadOnly()]

        # 浏览评论：任何人都能看
        return [permissions.AllowAny()]

class ActionViewSet(BaseViewSet):
    serializer_class = ActionSerializer
    # permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post']  # Only allow GET and POST

    def get_queryset(self):
        return Action.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_permissions(self):
        # 点赞 & 收藏操作：必须登录（注册用户）
        return [permissions.IsAuthenticated(), IsRegistered()]

class ConversationViewSet(BaseViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['updated_at']
    ordering = ['-updated_at']

    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user)

    def perform_create(self, serializer):
        # Get participant IDs from request data
        participant_ids = serializer.validated_data.pop('participant_ids', [])
        conversation = serializer.save()
        
        # Add creator as participant
        conversation.participants.add(self.request.user)
        
        # Add other participants
        for user_id in participant_ids:
            user = get_object_or_404(User, id=user_id)
            conversation.participants.add(user)

    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        conversation = self.get_object()
        user_id = request.data.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = get_object_or_404(User, id=user_id)
        if user in conversation.participants.all():
            return Response(
                {'error': 'User is already a participant'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        conversation.participants.add(user)
        return Response({'status': 'participant added'})

    @action(detail=True, methods=['post'])
    def mark_all_messages_read(self, request, pk=None):
        conversation = self.get_object()
        PrivateMessage.objects.filter(
            conversation=conversation,
            receiver=request.user,
            is_read=False
        ).update(is_read=True)
        return Response({'status': 'all messages marked as read'})

class PrivateMessageViewSet(BaseViewSet):
    serializer_class = PrivateMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['sent_at']
    ordering = ['-sent_at']

    def get_queryset(self):
        return PrivateMessage.objects.filter(
            Q(sender=self.request.user) | Q(receiver=self.request.user),
            conversation_id=self.kwargs['conversation_pk']
        )

    def perform_create(self, serializer):
        conversation = get_object_or_404(
            Conversation,
            pk=self.kwargs['conversation_pk'],
            participants=self.request.user
        )
        receiver_id = self.request.data.get('receiver')
        if not receiver_id:
            return Response(
                {'error': 'receiver is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        receiver = get_object_or_404(User, id=receiver_id)
        if receiver not in conversation.participants.all():
            return Response(
                {'error': 'receiver is not a participant in this conversation'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer.save(
            sender=self.request.user,
            receiver=receiver,
            conversation=conversation
        )

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None, conversation_pk=None):
        message = self.get_object()
        if message.receiver == request.user:
            message.is_read = True
            message.save()
            return Response({'status': 'marked as read'})
        return Response(
            {'error': 'not authorized'},
            status=status.HTTP_403_FORBIDDEN
        )

class NotificationViewSet(BaseViewSet):
    serializer_class = NotificationSerializer
    # permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    http_method_names = ['get', 'post', 'delete']  # Only allow GET, POST, and DELETE

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        self.get_queryset().update(is_read=True)
        return Response({'status': 'all marked as read'})

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'marked as read'})

    def get_permissions(self):
        # 所有通知操作：必须登录（注册用户）
        return [permissions.IsAuthenticated(), IsRegistered()]

class UploadStudentIDView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = StudentIDUploadSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            instance = serializer.save()
            return Response({
                'id': instance.id,
                'image_url': instance.image.url,
                'status': instance.status
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)