"""외부 API 대신 모의 응답으로 인증·소유권·쌍 저장을 검증한다."""
import json
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase, Client, override_settings
from .models import ChatSession, ChatMessage


class ApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='learner01', password='Study-Ready!42')
        self.other = get_user_model().objects.create_user(username='learner02', password='Other-Ready!42')
        self.conversation = ChatSession.objects.create(owner=self.user)
        self.client.force_login(self.user)
        self.url = f'/api/conversations/{self.conversation.pk}/'

    def post_json(self, url, data, client=None):
        return (client or self.client).post(url, data=json.dumps(data), content_type='application/json')

    def test_health_and_me(self):
        self.assertEqual(self.client.get('/api/health/').json()['database'], 'ok')
        self.assertEqual(self.client.get('/api/auth/me/').json(), {
            'user': {'id': self.user.pk, 'username': self.user.username}, 'chat_mode': 'demo',
            's3_export_enabled': False})

    def test_unauthenticated_is_json_401(self):
        self.client.logout()
        self.assertIsNone(self.client.get('/api/auth/me/').json()['user'])
        for url in ['/api/conversations/', self.url, self.url + 'messages/']:
            response = self.client.post(url) if url.endswith('messages/') else self.client.get(url)
            self.assertEqual(response.status_code, 401)
            self.assertIn('error', response.json())

    def test_csrf_protects_signup_login_and_authenticated_write(self):
        client = Client(enforce_csrf_checks=True)
        for url in ['/api/auth/signup/', '/api/auth/login/']:
            self.assertEqual(self.post_json(url, {}, client).status_code, 403)
        token = client.get('/api/auth/csrf/').json()['csrfToken']
        response = client.post('/api/auth/login/', data=json.dumps({
            'username': 'learner01', 'password': 'Study-Ready!42'}),
            content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        # 로그인은 CSRF 토큰을 교체한다. 프런트도 다시 발급받은 토큰으로 요청한다.
        self.assertEqual(client.post('/api/conversations/').status_code, 403)
        new_token = client.get('/api/auth/csrf/').json()['csrfToken']
        self.assertNotEqual(token, new_token)
        # multipart는 CSRF 미들웨어가 본문을 먼저 읽더라도 500 대신 JSON 400으로 거부한다.
        wrong_type = client.post('/api/conversations/', data={'unexpected': 'form'},
                                 HTTP_X_CSRFTOKEN=new_token)
        self.assertEqual(wrong_type.status_code, 400)
        self.assertIn('error', wrong_type.json())
        self.assertEqual(client.post('/api/conversations/', data='{}', content_type='application/json',
                                     HTTP_X_CSRFTOKEN=new_token).status_code, 201)
        self.assertEqual(client.post('/api/auth/logout/', data='{}', content_type='application/json',
                                     HTTP_X_CSRFTOKEN=new_token).status_code, 204)

    def test_signup_hashes_password_without_login(self):
        client = Client()
        response = self.post_json('/api/auth/signup/', {'username': 'newstudent',
                                  'password1': 'Safe-Pass!987', 'password2': 'Safe-Pass!987'}, client)
        self.assertEqual(response.status_code, 201)
        user = get_user_model().objects.get(username='newstudent')
        self.assertTrue(user.check_password('Safe-Pass!987'))
        self.assertFalse(user.is_staff)
        self.assertIsNone(client.get('/api/auth/me/').json()['user'])

    def test_signup_rejects_mismatch_weak_and_duplicate(self):
        for data in [
            {'username': 'newstudent', 'password1': 'Safe-Pass!987', 'password2': 'Different!23'},
            {'username': 'newstudent', 'password1': '12345678', 'password2': '12345678'},
            {'username': 'learner01', 'password1': 'Safe-Pass!987', 'password2': 'Safe-Pass!987'},
        ]:
            with self.subTest(data=data['username']):
                self.assertEqual(self.post_json('/api/auth/signup/', data).status_code, 400)
        self.assertEqual(get_user_model().objects.count(), 2)

    def test_signup_duplicate_race_is_400(self):
        with patch('app.views.SignupForm.save', side_effect=IntegrityError):
            response = self.post_json('/api/auth/signup/', {'username': 'newstudent',
                                      'password1': 'Safe-Pass!987', 'password2': 'Safe-Pass!987'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('username', response.json()['fields'])

    def test_wrong_login_and_inactive_user(self):
        response = self.post_json('/api/auth/login/', {'username': 'learner01', 'password': 'wrong'})
        self.assertEqual(response.status_code, 401)
        self.user.is_active = False
        self.user.save()
        response = self.post_json('/api/auth/login/', {'username': 'learner01', 'password': 'Study-Ready!42'})
        self.assertEqual(response.status_code, 401)

    def test_other_user_cannot_list_read_delete_or_write(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get('/api/conversations/').json()['conversations'], [])
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.delete(self.url).status_code, 404)
        self.assertEqual(self.post_json(self.url + 'messages/', {'query': 'hello'}).status_code, 404)
        self.assertTrue(ChatSession.objects.filter(pk=self.conversation.pk).exists())
        self.assertFalse(ChatMessage.objects.exists())

    def test_invalid_json_types_and_length(self):
        for data in [[], None, 'text', {'query': 1}, {'query': []}, {'query': True},
                     {'query': ' '}, {'query': 'x' * 2001}, {}]:
            self.assertEqual(self.post_json(self.url + 'messages/', data).status_code, 400)
        self.assertEqual(self.client.post(self.url + 'messages/', data='{',
                                         content_type='application/json').status_code, 400)
        self.assertEqual(self.client.post(self.url + 'messages/', data={'query': 'hello'}).status_code, 400)
        for data in [{'username': [], 'password': 'pass'}, {'username': 'x', 'password': 12}]:
            self.assertEqual(self.post_json('/api/auth/login/', data).status_code, 400)
        self.assertEqual(self.post_json('/api/conversations/', []).status_code, 400)
        self.assertEqual(self.post_json('/api/auth/logout/', []).status_code, 400)
        self.assertFalse(ChatMessage.objects.exists())

    def test_demo_stores_pair_restores_and_deletes(self):
        with patch('app.views.invoke') as invoke:
            response = self.post_json(self.url + 'messages/', {'query': '  Docker 공부  '})
            invoke.assert_not_called()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['mode'], 'demo')
        self.assertEqual([m['role'] for m in response.json()['messages']], ['human', 'ai'])
        self.assertIn('[Docker 실습 응답]', response.json()['messages'][1]['content'])
        self.assertEqual(ChatMessage.objects.count(), 2)
        restored = self.client.get(self.url).json()
        self.assertEqual(restored['messages'], response.json()['messages'])
        self.assertEqual(restored['conversation']['title'], 'Docker 공부')
        self.assertEqual(self.client.delete(self.url).status_code, 204)
        self.assertFalse(ChatMessage.objects.exists())

    @override_settings(CHATBOT_MODE='openai', OPENAI_API_KEY='')
    def test_openai_missing_key_does_not_store(self):
        response = self.post_json(self.url + 'messages/', {'query': 'IT 진로'})
        self.assertEqual(response.status_code, 503)
        self.assertFalse(ChatMessage.objects.exists())

    @override_settings(CHATBOT_MODE='openai')
    def test_openai_failure_does_not_store_or_expose_error(self):
        with patch('app.views.invoke', side_effect=RuntimeError('sensitive external detail')):
            response = self.post_json(self.url + 'messages/', {'query': 'private question'})
        self.assertEqual(response.status_code, 502)
        self.assertNotIn('sensitive', response.content.decode())
        self.assertNotIn('private', response.content.decode())
        self.assertFalse(ChatMessage.objects.exists())

    def test_second_save_failure_rolls_back_pair(self):
        original = ChatMessage.objects.create
        def fail_ai(**kwargs):
            if kwargs['message_type'] == 'ai':
                raise IntegrityError('test failure')
            return original(**kwargs)
        with patch('app.views.ChatMessage.objects.create', side_effect=fail_ai):
            self.assertEqual(self.post_json(self.url + 'messages/', {'query': 'hello'}).status_code, 502)
        self.assertFalse(ChatMessage.objects.exists())

    def test_wrong_method_and_unknown_route_are_json(self):
        response = self.client.get('/api/auth/signup/')
        self.assertEqual(response.status_code, 405)
        self.assertIn('error', response.json())
        self.assertEqual(self.client.get('/api/conversations/not-a-uuid/').status_code, 404)
