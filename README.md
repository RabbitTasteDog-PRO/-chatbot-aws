# AWS 분리 배포 챗봇

React 화면은 S3 + CloudFront, Django API는 ECR + EC2, 데이터는 RDS MySQL에 배포하는 실습 프로젝트임. 기존 Docker 챗봇의 회원가입·로그인·대화·S3 TXT 내보내기 기능을 유지함.

```text
브라우저 → CloudFront ┬→ 비공개 S3: React dist/
                     └→ /api/* → EC2 gateway → Django → RDS
                                                   └→ 기존 S3: 대화 TXT
최종 단계: CloudFront와 EC2 사이에 HTTPS ALB 추가
```

## 1. 로컬에서 실행

내 PC의 `chatbot_aws` 폴더에서 실행. Docker Desktop이 실행 중이어야 함.

```bash
cp .env.example .env
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

`.env`에서 `DJANGO_SECRET_KEY`, `DB_PASSWORD`, `MYSQL_ROOT_PASSWORD`를 직접 생성한 값으로 변경. 위 명령을 필요할 때 다시 실행하여 서로 다른 값을 생성. 로컬은 `CHATBOT_MODE=demo`로 시작할 수 있음.

```bash
docker compose -f compose.local.yaml up -d --build
```

브라우저에서 `http://localhost:5173` 접속. 회원가입 → 로그인 → 대화 전송 → 새로고침 후 대화 유지 확인. 로컬 기본 실습은 S3 기능을 끈 상태이며 AWS 자격 증명이 필요하지 않음.

```bash
docker compose -f compose.local.yaml down
```

종료 후에도 MySQL 볼륨은 유지됨. `down -v`는 저장한 계정과 대화를 삭제하므로 재시작 용도로 사용하지 않음.

## 2. AWS 배포 순서

[단계별 실습 문서](docs/) 순서로 진행. 운영 EC2 작업 폴더는 `/home/ubuntu/chatbot-aws`임.

1. 기존 EC2의 필요한 자료를 확보하고 중지한 뒤 새 Ubuntu 24.04 EC2 준비.
2. 같은 VPC에 RDS MySQL 생성 및 앱 계정 준비.
3. 기존 비공개 S3는 대화 TXT용으로 유지하고, React 배포용 버킷은 별도 생성.
4. 내 PC에서 **백엔드 이미지 하나**를 빌드하여 ECR에 업로드.
5. React `dist/`를 프론트 S3에 업로드하고 CloudFront의 `/api/*`는 EC2 gateway로 연결.
6. 수동 배포 검증 후 GitHub Actions 자동 배포 구성.
7. 사용자 도메인·ACM·ALB 추가 후 검증하고 기존 EC2 정리.

운영 `compose.prod.yaml`은 백엔드 이미지와 API 전용 Nginx gateway만 실행함. React 컨테이너와 MySQL 컨테이너는 실행하지 않음. `.env`, `certs/global-bundle.pem`, `deploy/nginx.conf`를 준비해야 함.

운영 연결에서 필요한 설정은 다음과 같음.

| 설정 | 입력 내용 |
| --- | --- |
| `BACKEND_IMAGE` | ECR 백엔드 이미지 전체 주소와 변경하지 않는 태그 |
| `DB_HOST` | RDS 엔드포인트. 주소 앞에 `https://`를 붙이지 않음 |
| `DB_USER`, `DB_PASSWORD` | RDS에 생성한 앱 전용 계정 |
| `DJANGO_ALLOWED_HOSTS` | 최초 EC2 퍼블릭 DNS, 최종 ALB 원본용 도메인. 쉼표로 구분 |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | 브라우저가 사용하는 CloudFront HTTPS 주소·서비스 도메인. 쉼표로 구분 |
| `S3_EXPORT_BUCKET` | 기존 대화 저장용 비공개 버킷. 프론트 버킷을 입력하지 않음 |

`DB_SSL_CA`는 Compose에서 인증서 경로로 고정하며 RDS 서버 이름까지 검증함. 운영 쿠키는 HTTPS 전용임. gateway가 전달하는 HTTPS 헤더를 신뢰하므로 EC2 80 포트는 가이드대로 CloudFront 또는 ALB에서만 접근하도록 제한.

S3 내보내기는 EC2 IAM 역할을 사용함. 컨테이너가 역할을 사용하도록 IMDSv2 응답 홉 제한을 2로 설정하며, AWS 액세스 키를 `.env`나 이미지에 넣지 않음. 내보낸 TXT의 다운로드 URL은 10분 유효하며 해당 사용자 대화만 내보낼 수 있음.

## 3. 검증 범위

로컬 단위 테스트와 프론트 빌드 통과 여부는 AWS 리소스 연결 성공과 다름. 실제 배포 후 CloudFront 주소에서 회원가입·로그인·채팅·새로고침·S3 내보내기 및 재배포 후 데이터 보존을 확인해야 함.
