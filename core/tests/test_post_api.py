import pytest
from django.urls import reverse
from core.models import Post
from core.tests.factories import PostFactory, CategoryFactory, TagFactory

pytestmark = pytest.mark.django_db

class TestPostAPI:
    def test_create_post(self, authenticated_client):
        """测试创建帖子"""
        url = reverse('api_v1:post-list')
        category = CategoryFactory()
        tags = [TagFactory(), TagFactory()]
        
        data = {
            'title': 'Test Post',
            'content': 'Test Content',
            'status': 'published',
            'category_id': category.id,
            'tag_ids': [tag.id for tag in tags]
        }
        
        response = authenticated_client.post(url, data)
        assert response.status_code == 201
        assert response.data['title'] == data['title']
        assert response.data['content'] == data['content']
        assert response.data['status'] == data['status']
        assert response.data['category']['id'] == category.id
        assert len(response.data['tags']) == len(tags)

    def test_get_posts(self, authenticated_client):
        """测试获取帖子列表"""
        # 创建一些测试帖子
        posts = PostFactory.create_batch(3)
        
        url = reverse('api_v1:post-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        assert isinstance(response.data, list)
        assert len(response.data) >= len(posts)

    def test_get_post_detail(self, authenticated_client):
        """测试获取帖子详情"""
        post = PostFactory()
        
        url = reverse('api_v1:post-detail', kwargs={'pk': post.id})
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        assert response.data['id'] == post.id
        assert response.data['title'] == post.title
        assert response.data['content'] == post.content

    def test_update_post(self, authenticated_client, test_user):
        """测试更新帖子"""
        post = PostFactory(author=test_user)
        
        url = reverse('api_v1:post-detail', kwargs={'pk': post.id})
        data = {
            'title': 'Updated Title',
            'content': 'Updated Content'
        }
        
        response = authenticated_client.patch(url, data)
        assert response.status_code == 200
        assert response.data['title'] == data['title']
        assert response.data['content'] == data['content']

    def test_delete_post(self, authenticated_client, test_user):
        """测试删除帖子"""
        post = PostFactory(author=test_user)
        
        url = reverse('api_v1:post-detail', kwargs={'pk': post.id})
        response = authenticated_client.delete(url)
        
        assert response.status_code == 204
        assert not Post.objects.filter(id=post.id).exists()

    @pytest.mark.parametrize("title,content,expected_status", [
        ("Valid Title", "Valid Content", 201),
        ("", "Valid Content", 400),
        ("Valid Title", "", 400),
        ("A" * 201, "Valid Content", 400),  # 标题超长
    ])
    def test_post_validation(self, authenticated_client, title, content, expected_status):
        """测试帖子验证"""
        url = reverse('api_v1:post-list')
        data = {
            'title': title,
            'content': content,
            'status': 'published'
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == expected_status

    def test_filter_posts_by_category(self, authenticated_client):
        """测试按分类筛选帖子"""
        category = CategoryFactory()
        posts = PostFactory.create_batch(3, category=category)
        PostFactory.create_batch(2)  # 其他分类的帖子
        
        url = reverse('api_v1:post-list')
        response = authenticated_client.get(url, {'category': category.id})
        
        assert response.status_code == 200
        assert len(response.data) == len(posts)
        assert all(post['category']['id'] == category.id for post in response.data)

    def test_filter_posts_by_tags(self, authenticated_client):
        """测试按标签筛选帖子"""
        tags = [TagFactory(), TagFactory()]
        posts = PostFactory.create_batch(3)
        for post in posts:
            post.tags.add(*tags)
        
        PostFactory.create_batch(2)  # 没有标签的帖子
        
        url = reverse('api_v1:post-list')
        response = authenticated_client.get(url, {'tags': [tag.id for tag in tags]})
        
        assert response.status_code == 200
        assert len(response.data) == len(posts)
        # 检查返回的帖子都包含指定的标签
        for post in response.data:
            post_tag_ids = {tag['id'] for tag in post['tags']}
            assert all(tag.id in post_tag_ids for tag in tags)

    def test_filter_posts_by_status(self, authenticated_client):
        """测试按状态筛选帖子"""
        published_posts = PostFactory.create_batch(3, status='published')
        PostFactory.create_batch(2, status='draft')
        
        url = reverse('api_v1:post-list')
        response = authenticated_client.get(url, {'status': 'published'})
        
        assert response.status_code == 200
        assert len(response.data) == len(published_posts)
        assert all(post['status'] == 'published' for post in response.data)

    def test_order_posts(self, authenticated_client):
        """测试帖子排序"""
        posts = PostFactory.create_batch(3)
        
        # 测试按创建时间排序
        url = reverse('api_v1:post-list')
        response = authenticated_client.get(url, {'ordering': '-created_at'})
        
        assert response.status_code == 200
        assert len(response.data) >= len(posts)
        created_times = [post['created_at'] for post in response.data]
        assert created_times == sorted(created_times, reverse=True)

    def test_anonymous_post(self, authenticated_client):
        """测试匿名发帖"""
        url = reverse('api_v1:post-list')
        data = {
            'title': 'Anonymous Post',
            'content': 'This is an anonymous post',
            'status': 'published',
            'is_anonymous': True
        }
        
        response = authenticated_client.post(url, data)
        assert response.status_code == 201
        assert response.data['is_anonymous'] is True
        assert response.data['author']['nickname'] == '匿名用户'

    def test_pin_post(self, authenticated_client, test_user):
        """测试帖子置顶"""
        post = PostFactory(author=test_user)
        
        url = reverse('api_v1:post-detail', kwargs={'pk': post.id})
        data = {'is_pinned': True}
        
        response = authenticated_client.patch(url, data)
        assert response.status_code == 200
        assert response.data['is_pinned'] is True

    def test_search_posts(self, authenticated_client):
        """测试帖子搜索"""
        PostFactory(title='Python Programming', content='Learn Python')
        PostFactory(title='Django Framework', content='Web development with Django')
        PostFactory(title='Data Science', content='Python for data analysis')
        
        url = reverse('api_v1:post-list')
        response = authenticated_client.get(url, {'search': 'Python'})
        
        assert response.status_code == 200
        assert len(response.data) == 2  # 应该找到两个包含 Python 的帖子

    def test_unauthorized_update(self, authenticated_client, another_user):
        """测试未授权更新"""
        post = PostFactory(author=another_user)
        
        url = reverse('api_v1:post-detail', kwargs={'pk': post.id})
        data = {'title': 'Unauthorized Update'}
        
        response = authenticated_client.patch(url, data)
        assert response.status_code == 403

    def test_unauthorized_delete(self, authenticated_client, another_user):
        """测试未授权删除"""
        post = PostFactory(author=another_user)
        
        url = reverse('api_v1:post-detail', kwargs={'pk': post.id})
        response = authenticated_client.delete(url)
        
        assert response.status_code == 403
        assert Post.objects.filter(id=post.id).exists() 