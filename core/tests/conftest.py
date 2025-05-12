import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from core.models import User
from core.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def test_user():
    return UserFactory()

@pytest.fixture
def authenticated_client(api_client, test_user):
    # 获取 token
    url = reverse('token_obtain_pair')
    response = api_client.post(url, {
        'username': test_user.username,
        'password': 'testpass123'
    })
    token = response.data['access']
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    return api_client

@pytest.fixture
def another_user():
    return UserFactory()

@pytest.fixture
def admin_user():
    return UserFactory(is_staff=True, is_superuser=True) 