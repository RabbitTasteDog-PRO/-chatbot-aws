"""CloudFront가 Host를 원본으로 바꾸어도 세션·CSRF 경계가 유지되는지 검사한다."""
import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings


@override_settings(
    ALLOWED_HOSTS=['origin.example.com'],
    CSRF_TRUSTED_ORIGINS=['https://www.example.com', 'https://demo.cloudfront.net'],
    SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'),
    SESSION_COOKIE_SECURE=True,
    CSRF_COOKIE_SECURE=True,
)
class CloudFrontSessionTests(TestCase):
    def setUp(self):
        get_user_model().objects.create_user(username='cloudlearner', password='Demo-Password!42')
        self.client = Client(enforce_csrf_checks=True)
        self.headers = {
            'HTTP_HOST': 'origin.example.com',
            'HTTP_X_FORWARDED_PROTO': 'https',
            'HTTP_ORIGIN': 'https://www.example.com',
        }

    def test_viewer_origin_login_and_authenticated_write(self):
        csrf = self.client.get('/api/auth/csrf/', **self.headers)
        self.assertTrue(csrf.cookies['csrftoken']['secure'])
        login = self.client.post('/api/auth/login/', data=json.dumps({
            'username': 'cloudlearner', 'password': 'Demo-Password!42',
        }), content_type='application/json', HTTP_X_CSRFTOKEN=csrf.json()['csrfToken'], **self.headers)
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.cookies['sessionid']['secure'])
        self.assertFalse(login.cookies['sessionid']['domain'])
        fresh = self.client.get('/api/auth/csrf/', **self.headers).json()['csrfToken']
        created = self.client.post('/api/conversations/', data='{}', content_type='application/json',
                                   HTTP_X_CSRFTOKEN=fresh, **self.headers)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(self.client.get('/api/auth/me/', **self.headers).json()['user']['username'],
                         'cloudlearner')

    def test_untrusted_browser_origin_is_rejected_even_with_valid_token(self):
        token = self.client.get('/api/auth/csrf/', **self.headers).json()['csrfToken']
        bad_headers = {**self.headers, 'HTTP_ORIGIN': 'https://untrusted.example.net'}
        response = self.client.post('/api/auth/login/', data=json.dumps({
            'username': 'cloudlearner', 'password': 'Demo-Password!42',
        }), content_type='application/json', HTTP_X_CSRFTOKEN=token, **bad_headers)
        self.assertEqual(response.status_code, 403)
        self.assertIn('error', response.json())
