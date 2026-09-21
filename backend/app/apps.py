from django.apps import AppConfig


# INSTALLED_APPS가 이 앱의 모델·템플릿을 등록할 때 사용하는 설정이다.
class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'
