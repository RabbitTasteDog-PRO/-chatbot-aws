"""로컬 MySQL 또는 RDS MySQL과 연결하는 JSON API 설정이다. 비밀값은 Compose가 주입한다."""
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '').strip()
if not SECRET_KEY:
    raise ImproperlyConfigured('DJANGO_SECRET_KEY 환경변수가 필요하다.')
DEBUG = os.environ.get('DJANGO_DEBUG', 'false').lower() == 'true'
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]', 'backend'] + [
    value.strip() for value in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',') if value.strip()
]
CSRF_TRUSTED_ORIGINS = [value.strip() for value in os.environ.get(
    'DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if value.strip()]
# 로컬 HTTP Docker 수업에서는 false, 외부 HTTPS 배포에서는 true로 설정한다.
SESSION_COOKIE_SECURE = os.environ.get('DJANGO_COOKIE_SECURE', 'false').lower() == 'true'
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
# 신뢰하는 gateway가 클라이언트 헤더를 덮어쓴 경우에만 활성화한다.
if os.environ.get('DJANGO_TRUST_PROXY', 'false').lower() == 'true':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_HTTPONLY = True
CSRF_FAILURE_VIEW = 'app.views.csrf_failure'
INSTALLED_APPS = ['django.contrib.auth', 'django.contrib.contenttypes',
                  'django.contrib.sessions', 'app']
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = '_chatbot.urls'
WSGI_APPLICATION = '_chatbot.wsgi.application'
DATABASES = {'default': {
    'ENGINE': 'django.db.backends.mysql',
    'HOST': os.environ.get('DB_HOST', 'db'),
    'PORT': os.environ.get('DB_PORT', '3306'),
    'NAME': os.environ.get('DB_NAME', 'chatbot'),
    'USER': os.environ.get('DB_USER', 'chatbot'),
    'PASSWORD': os.environ.get('DB_PASSWORD', ''),
    'OPTIONS': {'charset': 'utf8mb4'},
}}
# RDS 연결에서는 암호화뿐 아니라 CA와 엔드포인트 호스트 이름까지 검증한다.
DB_SSL_CA = os.environ.get('DB_SSL_CA', '').strip()
if DB_SSL_CA:
    DATABASES['default']['OPTIONS'].update({
        'ssl': {'ca': DB_SSL_CA},
        'ssl_mode': 'VERIFY_IDENTITY',
    })
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
DATA_UPLOAD_MAX_MEMORY_SIZE = 32 * 1024
# 버킷을 지정하지 않으면 기존 Docker 실습은 AWS 연결 없이 동작한다.
S3_EXPORT_BUCKET = os.environ.get('S3_EXPORT_BUCKET', '').strip()
AWS_DEFAULT_REGION = os.environ.get('AWS_DEFAULT_REGION', 'ap-northeast-2').strip() or 'ap-northeast-2'
CHATBOT_MODE = os.environ.get('CHATBOT_MODE', 'demo').strip().lower()
if CHATBOT_MODE not in ('demo', 'openai'):
    raise ImproperlyConfigured('CHATBOT_MODE는 demo 또는 openai여야 한다.')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-5.6-luna')
