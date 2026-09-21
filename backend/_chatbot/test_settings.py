"""외부 DB/키와 분리한 단위 테스트 전용 설정이다. 배포에 사용하지 않는다."""
import os
# 실제 .env를 읽지 않는다. 테스트 프로세스의 설정을 고정한다.
os.environ['DJANGO_SECRET_KEY'] = 'isolated-unit-test-secret-only'
os.environ['CHATBOT_MODE'] = 'demo'
os.environ['OPENAI_API_KEY'] = ''
from .settings import *  # noqa: E402,F403
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']
DEBUG = False
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
S3_EXPORT_BUCKET = ''
AWS_DEFAULT_REGION = 'ap-northeast-2'
