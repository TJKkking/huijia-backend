import io
import pytest
from PIL import Image
from django.urls import reverse
from core.models import StudentIDUpload  # 替换为你的模型路径

pytestmark = pytest.mark.django_db

def create_test_image(format='JPEG', size=(100, 100), color='blue', name='test.jpg'):
    """生成内存中的测试图片文件"""
    image = Image.new('RGB', size, color=color)
    byte_io = io.BytesIO()
    image.save(byte_io, format)
    byte_io.name = name
    byte_io.seek(0)
    return byte_io

class TestStudentIDUpload:

    def test_upload_idcard_authenticated(self, authenticated_client, test_user):
        """
        登录用户可以成功上传学生证图片
        """
        url = reverse('api_v1:upload-idcard')
        image_file = create_test_image()

        response = authenticated_client.post(
            url, {'image': image_file}, format='multipart'
        )

        assert response.status_code == 201
        data = response.data
        assert data['status'] == 'pending'
        assert 'image_url' in data

        upload = StudentIDUpload.objects.get(id=data['id'])
        assert upload.user == test_user
        assert upload.image.name.startswith('student_ids/')
        assert upload.status == 'pending'

    def test_upload_idcard_unauthenticated(self, client):
        """
        未登录用户上传应被拒绝
        """
        url = reverse('api_v1:upload-idcard')
        image_file = create_test_image()

        response = client.post(url, {'image': image_file}, format='multipart')
        assert response.status_code == 401

    def test_upload_invalid_file_format(self, authenticated_client):
        """
        上传非法格式文件（如 txt）应被拒绝
        """
        url = reverse('api_v1:upload-idcard')
        txt_file = io.BytesIO(b"Not an image")
        txt_file.name = "test.txt"
        txt_file.seek(0)

        response = authenticated_client.post(
            url, {'image': txt_file}, format='multipart'
        )
        assert response.status_code in (400, 415)  # 看你视图中如何处理

    def test_upload_empty_file(self, authenticated_client):
        """
        上传空文件应被拒绝
        """
        url = reverse('api_v1:upload-idcard')
        empty_file = io.BytesIO()
        empty_file.name = "empty.jpg"
        empty_file.seek(0)

        response = authenticated_client.post(
            url, {'image': empty_file}, format='multipart'
        )
        assert response.status_code in (400, 415)

    # def test_upload_oversized_file(self, authenticated_client):
    #     """
    #     超过文件大小限制应被拒绝
    #     """
    #     url = reverse('api_v1:upload-idcard')
    #     large_image = create_test_image(size=(5000, 5000))  # ~大于5MB
    #     large_image.name = 'large.jpg'

    #     response = authenticated_client.post(
    #         url, {'image': large_image}, format='multipart'
    #     )
    #     assert response.status_code in (400, 413)
