"""GitHub Actions에서 실행. 토큰·앱 비밀값 없이 SSM 배포와 결과를 확인함."""
import json
import os
import re
import shlex
import subprocess
import time
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import urlopen


def required(name, pattern):
    value = os.environ.get(name, '')
    if not re.fullmatch(pattern, value):
        raise SystemExit(f'{name} 설정을 확인하세요')
    return value


def main():
    region = required('AWS_REGION', r'ap-northeast-2')
    account = required('AWS_ACCOUNT_ID', r'\d{12}')
    instance = required('EC2_INSTANCE_ID', r'i-[0-9a-f]{8,17}')
    backend = required('ECR_BACKEND_REPOSITORY', r'[a-z0-9][a-z0-9._/-]+')
    origin = required('ORIGIN_HOST', r'[A-Za-z0-9][A-Za-z0-9.-]+')
    version = required('RELEASE_TAG', r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}')
    app_url = os.environ.get('APP_URL', '').rstrip('/')
    url = urlsplit(app_url)
    if (url.scheme != 'https' or url.path or url.query or url.fragment
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]+\.[A-Za-z]{2,}', url.netloc)):
        raise SystemExit('APP_URL에는 https://전체도메인 형식으로 입력하세요')
    registry = f'{account}.dkr.ecr.{region}.amazonaws.com'
    command = shlex.join([
        'bash', '/home/ubuntu/chatbot-aws/deploy/deploy.sh',
        version, registry, backend, origin, app_url,
    ])
    base = ['aws', '--region', region, '--no-cli-pager', 'ssm']
    sent = subprocess.run(base + [
        'send-command', '--document-name', 'AWS-RunShellScript',
        '--instance-ids', instance, '--timeout-seconds', '120',
        '--parameters', json.dumps({'commands': [command], 'executionTimeout': ['1800']}),
        '--output', 'json',
    ], text=True, capture_output=True)
    if sent.returncode:
        raise SystemExit(sent.stderr)
    command_id = json.loads(sent.stdout)['Command']['CommandId']
    print('SSM 명령 ID:', command_id, flush=True)

    for _ in range(380):
        result = subprocess.run(base + [
            'get-command-invocation', '--command-id', command_id,
            '--instance-id', instance, '--output', 'json',
        ], text=True, capture_output=True)
        if result.returncode:
            if 'InvocationDoesNotExist' in result.stderr:
                time.sleep(5)
                continue
            raise SystemExit(result.stderr)
        invocation = json.loads(result.stdout)
        status = invocation['Status']
        if status in ('Pending', 'InProgress', 'Delayed'):
            time.sleep(5)
            continue
        print(invocation.get('StandardOutputContent', ''))
        if status != 'Success' or invocation.get('ResponseCode') != 0:
            print(invocation.get('StandardErrorContent', ''))
            raise SystemExit(f'SSM 배포 실패: {status}')
        break
    else:
        raise SystemExit('SSM 결과 대기 시간 초과. EC2에서 진행 상태를 확인하세요')

    # GitHub 실행기에서도 공개 DNS·HTTPS 인증서·앱 응답을 재확인함.
    # 일시적인 연결 실패에만 제한된 횟수로 재시도함.
    for attempt in range(12):
        try:
            with urlopen(app_url + '/api/health/', timeout=10) as response:
                health = json.load(response)
            if health.get('status') != 'ok' or health.get('database') != 'ok':
                raise ValueError('외부 API 상태 검사 실패')
            break
        except (URLError, OSError, ValueError) as error:
            if attempt == 11:
                raise SystemExit(f'외부 HTTPS 확인 실패: {error}') from error
            time.sleep(5)
    print('외부 HTTPS API·DB 상태 확인 완료:', version)


if __name__ == '__main__':
    main()
