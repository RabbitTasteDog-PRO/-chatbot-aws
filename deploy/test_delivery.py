"""AWS를 호출하지 않고 배포 명령의 범위와 실패 처리를 확인한다."""
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ssm_deploy', ROOT / 'ssm_deploy.py')
ssm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ssm)
public_spec = importlib.util.spec_from_file_location('verify_public', ROOT / 'verify_public.py')
public = importlib.util.module_from_spec(public_spec)
public_spec.loader.exec_module(public)


class Response(io.BytesIO):
    status = 200


class DeliveryTests(unittest.TestCase):
    def env(self):
        return {'AWS_REGION': 'ap-northeast-2', 'AWS_ACCOUNT_ID': '123456789012',
                'EC2_INSTANCE_ID': 'i-1234567890abcdef0', 'ECR_BACKEND_REPOSITORY': 'chatbot-backend',
                'ORIGIN_HOST': 'ec2-example.compute.amazonaws.com', 'RELEASE_TAG': 'abc-1-1',
                'APP_URL': 'https://example.cloudfront.net'}

    def test_ssm_success_uses_one_backend_and_expected_path(self):
        results = [subprocess.CompletedProcess([], 0, json.dumps({'Command': {'CommandId': 'test'}}), ''),
                   subprocess.CompletedProcess([], 0, json.dumps({'Status': 'Success', 'ResponseCode': 0}), '')]
        with patch.dict(os.environ, self.env(), clear=True), patch.object(ssm.subprocess, 'run', side_effect=results) as run, patch.object(ssm, 'urlopen', return_value=io.BytesIO(b'{"status":"ok","database":"ok"}')):
            ssm.main()
        args = run.call_args_list[0].args[0]
        commands = json.loads(args[args.index('--parameters') + 1])['commands']
        self.assertIn('/home/ubuntu/chatbot-aws/deploy/deploy.sh', commands[0])
        self.assertIn('chatbot-backend', commands[0])
        self.assertNotIn('frontend', commands[0])

    def test_ssm_failure_does_not_report_success(self):
        results = [subprocess.CompletedProcess([], 0, json.dumps({'Command': {'CommandId': 'test'}}), ''),
                   subprocess.CompletedProcess([], 0, json.dumps({'Status': 'Failed', 'ResponseCode': 1}), '')]
        with patch.dict(os.environ, self.env(), clear=True), patch.object(ssm.subprocess, 'run', side_effect=results), self.assertRaises(SystemExit):
            ssm.main()

    def test_frontend_assets_before_index_no_delete_and_wait(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            (temp / 'dist/assets').mkdir(parents=True)
            (temp / 'dist/index.html').write_text('<div id="root"></div>')
            log = temp / 'commands'
            fake = temp / 'aws'
            fake.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$COMMAND_LOG"\ncase "$*" in *create-invalidation*) echo I123;; esac\n')
            fake.chmod(0o755)
            env = dict(os.environ, PATH=str(temp) + ':' + os.environ['PATH'], COMMAND_LOG=str(log))
            subprocess.run(['bash', str(ROOT / 'frontend.sh'), 'example-front', 'E123', str(temp / 'dist')], env=env, check=True)
            commands = log.read_text().splitlines()
            self.assertIn('/assets/', commands[0])
            self.assertIn('index.html', commands[2])
            self.assertIn('no-store', commands[2])
            self.assertTrue(commands[-1].startswith('cloudfront wait'))
            self.assertNotIn('--delete', '\n'.join(commands))

    def test_public_index_must_match_this_build(self):
        html = b'<div id="root"></div>'
        with patch.dict(os.environ, {'APP_URL': 'https://example.cloudfront.net'}), patch.object(public.Path, 'read_bytes', return_value=html), patch.object(public, 'urlopen', side_effect=[Response(html), Response(b'{"status":"ok","database":"ok"}')]):
            public.main()
        with patch.dict(os.environ, {'APP_URL': 'https://example.cloudfront.net'}), patch.object(public.Path, 'read_bytes', return_value=html + b'new'), patch.object(public, 'urlopen', return_value=Response(html)), self.assertRaises(SystemExit):
            public.main()

    def test_bad_tag_rejected_before_ec2_operations(self):
        result = subprocess.run(['bash', str(ROOT / 'deploy.sh'), 'bad;tag', '123456789012.dkr.ecr.ap-northeast-2.amazonaws.com', 'backend', 'example.com'], capture_output=True)
        self.assertEqual(result.returncode, 2)


if __name__ == '__main__':
    unittest.main()
