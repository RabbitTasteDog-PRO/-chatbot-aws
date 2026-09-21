"""S3는 모의 클라이언트로 대체하고 인증·소유권·저장 내용·실패 응답을 검증한다."""
from datetime import datetime, timezone as datetime_timezone
from unittest.mock import patch
from botocore.exceptions import ClientError, NoCredentialsError
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from .exports import MAX_EXPORT_BYTES, MAX_EXPORT_MESSAGES
from .models import ChatSession, ChatMessage


@override_settings(S3_EXPORT_BUCKET='classroom-private-bucket')
class ExportTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='export-owner')
        self.other = get_user_model().objects.create_user(username='other-owner')
        self.conversation = ChatSession.objects.create(owner=self.user)
        self.url = f'/api/conversations/{self.conversation.pk}/export/'
        self.client.force_login(self.user)
        self.factory_patch = patch('app.exports.boto3.client')
        self.factory = self.factory_patch.start()
        self.addCleanup(self.factory_patch.stop)
        self.s3 = self.factory.return_value
        self.s3.generate_presigned_url.return_value = 'https://example.invalid/temporary-download'

    def add_message(self, content='안녕하세요', role='human', hour=1):
        return ChatMessage.objects.create(
            conversation=self.conversation, message_type=role, content=content,
            created_at=datetime(2026, 9, 18, hour, tzinfo=datetime_timezone.utc))

    def post(self, **kwargs):
        return self.client.post(self.url, data='{}', content_type='application/json', **kwargs)

    def test_export_uses_db_order_utf8_private_metadata_and_stable_key(self):
        self.add_message('답변입니다.', 'ai', 2)
        self.add_message('안녕하세요', 'human', 1)
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertIn('no-store', response['Cache-Control'])
        filename = f'conversation-{self.conversation.pk}.txt'
        self.assertEqual(response.json(), {
            'download_url': 'https://example.invalid/temporary-download',
            'filename': filename, 'expires_in': 600})
        key = f'day2/chat-exports/{self.user.pk}/{self.conversation.pk}.txt'
        args = self.s3.put_object.call_args.kwargs
        self.assertEqual(args, {
            'Bucket': 'classroom-private-bucket', 'Key': key,
            'Body': (f'상담 기록: {self.conversation.pk}\n\n'
                     '[2026-09-18T10:00:00+09:00] 사용자\n안녕하세요\n\n'
                     '[2026-09-18T11:00:00+09:00] 챗봇\n답변입니다.\n\n').encode('utf-8'),
            'ContentType': 'text/plain; charset=utf-8',
            'ContentDisposition': f'attachment; filename="{filename}"',
            'CacheControl': 'private, no-store'})
        self.s3.generate_presigned_url.assert_called_once_with(
            'get_object', Params={'Bucket': 'classroom-private-bucket', 'Key': key}, ExpiresIn=600)
        self.assertEqual(self.factory.call_args.kwargs['config'].signature_version, 's3v4')
        self.assertNotIn('aws_access_key_id', self.factory.call_args.kwargs)
        self.post()
        self.assertEqual(self.s3.put_object.call_args.kwargs['Key'], key)

    def test_login_and_ownership_are_required_before_aws_call(self):
        self.client.logout()
        response = self.post()
        self.assertEqual(response.status_code, 401)
        self.assertIn('no-store', response['Cache-Control'])
        self.client.force_login(self.other)
        self.assertEqual(self.post().status_code, 404)
        self.factory.assert_not_called()

    def test_csrf_is_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(self.url).status_code, 403)
        self.factory.assert_not_called()

    @override_settings(S3_EXPORT_BUCKET='')
    def test_unconfigured_bucket_does_not_call_aws(self):
        self.assertEqual(self.post().status_code, 503)
        self.assertFalse(self.client.get('/api/auth/me/').json()['s3_export_enabled'])
        self.factory.assert_not_called()

    def test_enabled_flag_and_empty_conversation(self):
        self.assertTrue(self.client.get('/api/auth/me/').json()['s3_export_enabled'])
        self.assertEqual(self.post().status_code, 400)
        self.factory.assert_not_called()

    def test_byte_limit_counts_utf8_and_cumulative_messages(self):
        self.add_message('가' * (MAX_EXPORT_BYTES // 6 + 1))
        self.add_message('나' * (MAX_EXPORT_BYTES // 6 + 1), 'ai')
        self.assertEqual(self.post().status_code, 400)
        self.factory.assert_not_called()

    def test_invalid_body_is_rejected(self):
        response = self.client.post(self.url, data='[]', content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.factory.assert_not_called()

    def test_message_limit_rejects_instead_of_silently_truncating(self):
        ChatMessage.objects.bulk_create([
            ChatMessage(conversation=self.conversation, message_type='human', content='짧은 질문')
            for _ in range(MAX_EXPORT_MESSAGES + 1)])
        response = self.post()
        self.assertEqual(response.status_code, 400)
        self.assertIn('500', response.json()['error'])
        self.factory.assert_not_called()

    def test_oversized_text_is_rejected_before_loading_message_bodies(self):
        self.add_message('a' * (MAX_EXPORT_BYTES + 1))
        # 인증/세션 쿼리와 별도로 메시지 조회 SQL에 LIMIT와 길이 집계가 적용된다.
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as queries:
            response = self.post()
        self.assertEqual(response.status_code, 400)
        message_queries = [row['sql'] for row in queries.captured_queries
                           if 'FROM "app_chatmessage"' in row['sql']]
        self.assertEqual(len(message_queries), 1)
        self.assertIn('LENGTH(', message_queries[0])
        self.assertIn('LIMIT 501', message_queries[0])
        self.factory.assert_not_called()

    def test_s3_failure_does_not_expose_aws_error_or_return_url(self):
        self.add_message()
        self.s3.put_object.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'private-resource-details'}}, 'PutObject')
        response = self.post()
        self.assertEqual(response.status_code, 502)
        self.assertIn('no-store', response['Cache-Control'])
        self.assertNotIn('private-resource-details', response.content.decode())
        self.assertNotIn('download_url', response.json())
        self.s3.generate_presigned_url.assert_not_called()

    def test_missing_credentials_is_safe_error(self):
        self.add_message()
        self.factory.side_effect = NoCredentialsError()
        self.assertEqual(self.post().status_code, 502)
