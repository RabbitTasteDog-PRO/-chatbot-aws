"""배포 서버가 호출하는 Django 진입점이다. 로컬에서는 manage.py runserver를 사용한다."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', '_chatbot.settings')

application = get_wsgi_application()
