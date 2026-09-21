"""React에서 호출하는 API만 노출한다."""
from django.urls import path
from app import views

urlpatterns = [
    path('api/health/', views.health),
    path('api/auth/csrf/', views.csrf),
    path('api/auth/me/', views.me),
    path('api/auth/signup/', views.signup),
    path('api/auth/login/', views.login),
    path('api/auth/logout/', views.logout),
    path('api/conversations/', views.conversations),
    path('api/conversations/<uuid:conversation_id>/', views.conversation_detail),
    path('api/conversations/<uuid:conversation_id>/messages/', views.messages),
    path('api/conversations/<uuid:conversation_id>/export/', views.conversation_export),
]
handler400 = 'app.views.bad_request'
handler403 = 'app.views.forbidden'
handler404 = 'app.views.not_found'
handler500 = 'app.views.server_error'
