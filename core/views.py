from django.shortcuts import render
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django.utils import timezone
import logging
from .models import (
    User, Category, Tag, Post, Comment,
    Action, Conversation, PrivateMessage, Notification
)
from .serializers import (
    UserSerializer, CategorySerializer, TagSerializer,
    PostSerializer, CommentSerializer, ActionSerializer,
    ConversationSerializer, PrivateMessageSerializer,
    NotificationSerializer
)

logger = logging.getLogger(__name__)

class IsSelfOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow users to edit their own profile,
    or admins to edit any profile.
    """
    def has_object_permission(self, request, view, obj):
        return obj == request.user or request.user.is_staff

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        # For different models, check different owner fields
        if isinstance(obj, Notification):
            return obj.recipient == request.user
        elif hasattr(obj, 'author'):
            return obj.author == request.user
        return False

class UserViewSet(viewsets.ModelViewSet):
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

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticatedOrReadOnly()]

class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticatedOrReadOnly()]

class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
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

class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
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

class ActionViewSet(viewsets.ModelViewSet):
    serializer_class = ActionSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post']  # Only allow GET and POST

    def get_queryset(self):
        return Action.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ConversationViewSet(viewsets.ModelViewSet):
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

class PrivateMessageViewSet(viewsets.ModelViewSet):
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

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
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
