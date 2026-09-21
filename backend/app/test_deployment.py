"""운영 연결 설정의 TLS 검증과 신뢰 프록시 경계를 확인한다."""
import os
import runpy
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, RequestFactory, override_settings


class DeploymentSettingsTests(SimpleTestCase):
    def load_settings(self, **environment):
        settings_file = Path(__file__).resolve().parents[1] / '_chatbot' / 'settings.py'
        base = {
            'DJANGO_SECRET_KEY': 'test-only-secret',
            'CHATBOT_MODE': 'demo',
            'DB_SSL_CA': '',
            'DJANGO_TRUST_PROXY': 'false',
        }
        with patch.dict(os.environ, {**base, **environment}, clear=True):
            return runpy.run_path(str(settings_file))

    def test_rds_requires_certificate_and_hostname_verification(self):
        configuration = self.load_settings(DB_SSL_CA='/app/certs/global-bundle.pem')
        options = configuration['DATABASES']['default']['OPTIONS']
        self.assertEqual(options['ssl'], {'ca': '/app/certs/global-bundle.pem'})
        self.assertEqual(options['ssl_mode'], 'VERIFY_IDENTITY')

    def test_local_mysql_has_no_rds_tls_requirement(self):
        configuration = self.load_settings()
        self.assertNotIn('ssl', configuration['DATABASES']['default']['OPTIONS'])
        self.assertNotIn('SECURE_PROXY_SSL_HEADER', configuration)

    def test_https_proxy_and_cookie_settings(self):
        configuration = self.load_settings(DJANGO_TRUST_PROXY='true', DJANGO_COOKIE_SECURE='true')
        self.assertTrue(configuration['SESSION_COOKIE_SECURE'])
        self.assertTrue(configuration['CSRF_COOKIE_SECURE'])
        with override_settings(SECURE_PROXY_SSL_HEADER=configuration['SECURE_PROXY_SSL_HEADER']):
            request = RequestFactory().get('/api/auth/me/', HTTP_X_FORWARDED_PROTO='https')
            self.assertTrue(request.is_secure())
