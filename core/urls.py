from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from . import views

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'categories', views.CategoryViewSet, basename='category')
router.register(r'tags', views.TagViewSet, basename='tag')
router.register(r'posts', views.PostViewSet, basename='post')
router.register(r'actions', views.ActionViewSet, basename='action')
router.register(r'conversations', views.ConversationViewSet, basename='conversation')
router.register(r'notifications', views.NotificationViewSet, basename='notification')

# Nested routers for comments and messages
posts_router = routers.NestedDefaultRouter(router, r'posts', lookup='post')
posts_router.register(r'comments', views.CommentViewSet, basename='post-comments')

conversations_router = routers.NestedDefaultRouter(router, r'conversations', lookup='conversation')
conversations_router.register(r'messages', views.PrivateMessageViewSet, basename='conversation-messages')

# API v1 URL patterns
api_v1_patterns = [
    path('', include(router.urls)),
    path('', include(posts_router.urls)),
    path('', include(conversations_router.urls)),
]

# Root URL patterns
urlpatterns = [
    path('api/v1/', include((api_v1_patterns, 'api_v1'), namespace='api_v1')),
] 