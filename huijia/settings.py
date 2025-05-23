"""
Django settings for huijia project.

Generated by 'django-admin startproject' using Django 3.2.12.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

from pathlib import Path
import os
from boto3.session import Config
from botocore.client import Config as BotocoreConfig

from dotenv import load_dotenv
load_dotenv()  # 加载 .env 文件中的环境变量

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

SECRET_KEY = os.getenv('SECRET_KEY')

WECHAT_APP_ID = os.getenv('WECHAT_APP_ID')
WECHAT_APP_SECRET = os.getenv('WECHAT_APP_SECRET')

ALLOWED_HOSTS = []

AUTH_USER_MODEL = "core.User"

if os.getenv("GITHUB_ACTIONS") == "true" or os.getenv("CI") == "true":
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB', 'test_db'),
            'USER': os.getenv('POSTGRES_USER', 'test_user'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'test_pass'),
            'HOST': 'localhost',
            'PORT': '5432',
        }
    }

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "debug_toolbar",
    "django_extensions",
    "rest_framework_nested",
    "rest_framework",
    "drf_spectacular",
    "core.apps.CoreConfig",
    "storages",
]

# Storage
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME', 'huijia-337845818')
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'cn-hangzhou')
# 使用https会导致报错botocore.exceptions.ClientError: An error occurred (InvalidArgument) when calling the PutObject operation: aws-chunked encoding is not supported with the specified x-amz-content-sha256 value.
# 暂时使用http，参考：https://github.com/siyuan-note/siyuan/issues/14053
AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL', 'http://oss-cn-hangzhou.aliyuncs.com')

# --- NEW/MOVED SETTINGS ---
AWS_S3_ADDRESSING_STYLE = "virtual"  # or "path" if needed, "virtual" is common
AWS_S3_SIGNATURE_VERSION = "v4"      # For OSS, s3v4 is usually required

AWS_S3_CLIENT_CONFIG = BotocoreConfig(
    signature_version=AWS_S3_SIGNATURE_VERSION,
    region_name=AWS_S3_REGION_NAME,
    s3={'addressing_style': AWS_S3_ADDRESSING_STYLE}
)

# --- Other settings (keep as they are) ---
AWS_S3_FILE_OVERWRITE = True
AWS_DEFAULT_ACL = None  # This is usually handled by the custom storage classes' default_acl
AWS_QUERYSTRING_AUTH = True

# STORAGES = {
#     "default": {
#         "BACKEND": "core.storages.MediaStorage",
#     },
#     "staticfiles": {
#         "BACKEND": "core.storages.StaticStorage",
#     },
# }

# STATIC & MEDIA URL
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.{AWS_S3_ENDPOINT_URL.split("://")[1]}'
# STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
# MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles_collected')
MEDIA_ROOT = BASE_DIR / 'media_files_locally_for_dev_or_nominal' 

if DEBUG:
    # === 开发环境用本地 ===
    STATIC_URL = "/static/"
    MEDIA_URL = "/media/"

    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
    DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

else:
    # === 生产环境用 OSS ===
    STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/static/"
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"

    STORAGES = {
        "default": {
            "BACKEND": "core.storages.MediaStorage",
        },
        "staticfiles": {
            "BACKEND": "core.storages.StaticStorage",
        },
    }
# End of Storage

INTERNAL_IPS = [
    # ...
    "127.0.0.1",
    # ...
]

MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'huijia.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'huijia.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = '/static/'

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}
# 开发模式下，为了调试方便，一律允许匿名访问
if DEBUG:
    REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = [
        'rest_framework.permissions.AllowAny',
    ]

SPECTACULAR_SETTINGS = {
    'TITLE': 'Huijia API',
    'DESCRIPTION': 'API documentation for Huijia backend',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
    },
}

# JWT settings
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'core': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
