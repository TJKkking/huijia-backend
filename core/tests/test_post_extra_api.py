import pytest
from django.urls import reverse
from core.models import Post, Comment, Action, Notification
from core.tests.factories import PostFactory, UserFactory, CommentFactory

pytestmark = pytest.mark.django_db

class TestCommentAPI:
    def test_create_and_get_comment(self, authenticated_client, test_user):
        post = PostFactory()
        url = reverse('api_v1:post-comments-list', kwargs={'post_pk': post.id})
        data = {'content': 'This is a comment', 'post': post.id}
        response = authenticated_client.post(url, data)
        assert response.status_code == 201
        comment_id = response.data['id']
        # 获取评论列表
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert any(c['id'] == comment_id for c in response.data)

    def test_comment_permission(self, authenticated_client, another_user):
        post = PostFactory()
        comment = CommentFactory(post=post, author=another_user)
        url = reverse('api_v1:post-comments-detail', kwargs={'post_pk': post.id, 'pk': comment.id})
        # 不能删除他人评论
        response = authenticated_client.delete(url)
        assert response.status_code == 403

class TestLikeFavoriteAPI:
    def test_like_and_unlike_post(self, authenticated_client, test_user):
        post = PostFactory()
        url = reverse('api_v1:post-like', kwargs={'pk': post.id})
        # 点赞
        response = authenticated_client.post(url)
        assert response.status_code == 200
        assert response.data['status'] == 'liked'
        # 再次点赞为取消
        response = authenticated_client.post(url)
        assert response.status_code == 200
        assert response.data['status'] == 'unliked'

    def test_favorite_and_unfavorite_post(self, authenticated_client, test_user):
        post = PostFactory()
        url = reverse('api_v1:post-favorite', kwargs={'pk': post.id})
        # 收藏
        response = authenticated_client.post(url)
        assert response.status_code == 200
        assert response.data['status'] == 'favorited'
        # 再次收藏为取消
        response = authenticated_client.post(url)
        assert response.status_code == 200
        assert response.data['status'] == 'unfavorited'

class TestNotificationAPI:
    def test_get_and_mark_notification(self, authenticated_client, test_user):
        # 创建一条通知（使用正确字段）
        notification = Notification.objects.create(
            recipient=test_user,
            notif_type='system',
            is_read=False,
        )
        url = reverse('api_v1:notification-list')
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert any(n['id'] == notification.id for n in response.data)
        # 标记为已读
        mark_url = reverse('api_v1:notification-mark-as-read', kwargs={'pk': notification.id})
        response = authenticated_client.post(mark_url)
        assert response.status_code == 200
        notification.refresh_from_db()
        assert notification.is_read is True 