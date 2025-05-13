# core/storages.py
from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings
# No need to import or define custom_boto3_client_config here anymore

class MediaStorage(S3Boto3Storage):
    location = "media"
    file_overwrite = False
    querystring_auth = True
    # The 'config' attribute is removed, it will use settings.AWS_S3_CLIENT_CONFIG

class StaticStorage(S3Boto3Storage):
    location = "static"
    # querystring_auth = getattr(settings, 'AWS_STATIC_QUERYSTRING_AUTH', False)
    # The 'config' attribute is removed, it will use settings.AWS_S3_CLIENT_CONFIG