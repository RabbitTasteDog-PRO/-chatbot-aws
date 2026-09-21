"""GitHub 실행기에서 캐시 갱신 후 공개 화면 및 DB 연결을 확인한다."""
import json
import hashlib
from pathlib import Path
import os
from urllib.parse import urlsplit
from urllib.request import urlopen


def main():
    app_url = os.environ['APP_URL'].rstrip('/')
    parsed = urlsplit(app_url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.path or parsed.query or parsed.fragment:
        raise SystemExit('APP_URL은 https://도메인 형식이어야 합니다')
    with urlopen(app_url + '/', timeout=20) as response:
        payload = response.read(1_000_000)
        html = payload.decode('utf-8')
        if response.status != 200 or 'id="root"' not in html:
            raise SystemExit('React index.html 확인 실패')
    expected = Path('frontend/dist/index.html').read_bytes()
    if hashlib.sha256(payload).digest() != hashlib.sha256(expected).digest():
        raise SystemExit('공개 index.html이 이번 빌드 결과와 다릅니다')
    with urlopen(app_url + '/api/health/', timeout=20) as response:
        health = json.load(response)
    if health.get('status') != 'ok' or health.get('database') != 'ok':
        raise SystemExit('API 또는 DB 상태 확인 실패')
    print('공개 React 화면 및 HTTPS API·DB 확인 완료')


if __name__ == '__main__':
    main()
