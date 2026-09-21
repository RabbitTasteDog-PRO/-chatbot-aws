# EC2 백엔드 실행과 CloudFront 연결

## 1. CloudFront에 React 원본 연결

**CloudFront:** 사용자에게 파일을 전달하고, 요청 경로에 따라 어느 서버로 보낼지 정하는 서비스임. 이번에는 같은 주소에서 화면과 API를 사용하도록 구성.

```text
https://CloudFront주소/          → S3의 React 파일
https://CloudFront주소/api/...   → EC2 gateway → Django → RDS
                                      └→ 기존 S3에 대화 TXT 저장
```

**AWS 콘솔 → CloudFront → 배포 → 배포 생성** 열기. 새 생성 화면의 구역이 다르면 같은 이름의 설정을 아래 값으로 맞춤.

| 항목 | 선택·입력값 |
| --- | --- |
| 배포 이름 또는 설명 | `skn33-chatbot-ALIAS` |
| 원본 유형 | Amazon S3 |
| 원본 도메인 | **React 전용 버킷** 선택. `버킷.s3.ap-northeast-2.amazonaws.com` 형태 |
| 원본 경로 | 비움 |
| 원본 액세스 | **Origin access control settings / OAC** |
| OAC | 새 제어 설정 생성 → 요청 서명 `Sign requests` 권장값 유지 |
| 원본 이름 | `react-s3` |
| 뷰어 프로토콜 정책 | **Redirect HTTP to HTTPS** |
| 허용 HTTP 메서드 | GET, HEAD |
| 캐시 정책 | **CachingOptimized** |
| 원본 요청 정책 | 없음 |
| 객체 자동 압축 | 예 |
| 대체 도메인·사용자 지정 인증서 | 지금은 설정하지 않음 |
| 기본 루트 객체 | `index.html` |

별도 유료 플랜·WAF 보안 기능을 묻는 경우 기관에서 승인한 구성을 선택. 이번 필수 실습 때문에 유료 보안 구독을 추가하지 않음. **배포 생성** 후 **일반 → 설정 편집**에서도 기본 루트 객체를 확인할 수 있음.

**확인 결과:** 배포 ID `E...`와 배포 도메인 `d....cloudfront.net` 기록. OAC는 S3 버킷에 대한 CloudFront의 읽기 권한을 연결하는 방식임. S3 웹 사이트 엔드포인트를 넣으면 이 설정을 사용할 수 없음.

## 2. S3 버킷 정책 반영

CloudFront 화면에 표시되는 **정책 복사(Copy policy)**를 클릭. **S3 → React 버킷 → 권한 → 버킷 정책 → 편집**에 붙여넣고 저장.

복사 버튼이 없으면 프로젝트의 `infra/frontend-bucket-policy.json`을 사용. `FRONTEND_BUCKET`, `ACCOUNT_ID`, `DISTRIBUTION_ID`를 방금 만든 실제 값으로 변경한 뒤 같은 편집기에 입력.

**확인 결과:** 서비스 주체가 `cloudfront.amazonaws.com`, 리소스가 **프론트 버킷**의 `/*`, 조건의 SourceArn이 **본인 CloudFront 배포 ID**임. 기존 대화 저장 버킷에 붙이지 않음. 퍼블릭 액세스 차단과 ACL 비활성화는 유지.

## 3. EC2 원본 추가

**CloudFront → 해당 배포 → 원본(Origins) → 원본 생성** 선택.

| 항목 | 선택·입력값 |
| --- | --- |
| 원본 도메인 | 새 EC2의 **퍼블릭 DNS**. `http://`, 경로, 포트를 붙이지 않음 |
| 프로토콜 | **HTTP only** |
| HTTP 포트 | 80 |
| 원본 경로 | 비움. `/api`를 넣지 않음 |
| 이름 | `django-ec2` |
| 추가 설정 → 응답 시간 제한(Response timeout) | 60초 |

외부 AI 응답이 기본 30초보다 늦어질 수 있어 응답 대기를 60초로 설정. 응답 완료 시간 제한이 별도로 활성화되어 있다면 60초보다 짧게 두지 않음. demo 모드로 먼저 확인하며, 60초를 넘는 처리는 비동기 작업·스트리밍 등 별도 설계가 필요함. [AWS 원본 시간 제한](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/DownloadDistValuesOrigin.html)

원본 생성 후 **동작(Behaviors) → 동작 생성** 선택.

| 항목 | 선택·입력값 |
| --- | --- |
| 경로 패턴 | `/api/*` |
| 원본 | `django-ec2` |
| 뷰어 프로토콜 정책 | Redirect HTTP to HTTPS |
| 허용 HTTP 메서드 | **GET, HEAD, OPTIONS, PUT, POST, PATCH, DELETE** |
| 캐시 정책 | **CachingDisabled** |
| 원본 요청 정책 | **AllViewerExceptHostHeader** |

저장 후 `/api/*`가 기본 동작보다 우선 적용되는지 확인. 이 정책은 쿠키·쿼리·CSRF 관련 헤더를 전달하면서 **Host를 EC2 원본 DNS로 변경**함. 따라서 Django 허용 호스트에는 CloudFront 주소가 아니라 **EC2 퍼블릭 DNS**를 넣고, CSRF 신뢰 출처에는 **브라우저가 접속하는 CloudFront HTTPS 주소**를 넣음. [AWS 관리형 원본 요청 정책](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-managed-origin-request-policies.html)

**확인 결과:** 기본 동작은 `react-s3`, `/api/*`는 `django-ec2` 사용. 전체 배포의 403·404를 무조건 `/index.html`의 200 응답으로 바꾸지 않음. API 오류까지 HTML로 바뀌면 원인을 확인하기 어려워짐. 현재 앱은 루트 화면에서 사용하며 별도 SPA 경로 재작성은 필요 없음.

## 4. EC2 HTTP 인바운드 허용

**EC2 → 보안 그룹 → 새 EC2 보안 그룹 → 인바운드 규칙 편집 → 규칙 추가** 선택.

| 항목 | 값 |
| --- | --- |
| 유형 | HTTP |
| 포트 | 80 |
| 소스 유형 | 사용자 지정 |
| 소스 값 | `com.amazonaws.global.cloudfront.origin-facing` 검색 후 관리형 접두사 목록 선택 |

**규칙 저장** 클릭. SSH 22의 **내 IP**는 유지. 다른 연결 보안 그룹에 80번 `0.0.0.0/0`이 남아 있다면 이번 경로에서는 제거.

접두사 목록은 CloudFront 원본 접속 서버들의 주소 집합임. 보안 그룹 규칙 가중치가 55이므로 한도 초과 오류가 나면 관리자에게 한도 조정 또는 보안 그룹 분리를 요청. **본인 배포만 식별하는 인증 수단은 아니며**, Django 로그인·권한 검사는 계속 필요. [AWS CloudFront 원본 주소](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/LocationsOfEdgeServers.html)

## 5. EC2 환경 파일 작성

**새 EC2 터미널**로 돌아와 앞에서 전송한 파일 사용.

```bash
cd /home/ubuntu/chatbot-aws
cp .env.example .env
chmod 600 .env
python3 -c 'import secrets; print(secrets.token_urlsafe(50))'
nano .env
```

마지막 출력값을 `DJANGO_SECRET_KEY`에 입력. 이미 `.env`를 작성한 경우 복사 명령은 반복하지 않고 편집만 진행. 아래는 **수정할 항목의 설명**이며 예시 값을 그대로 복사하지 않음.

| 항목 | 입력할 값 |
| --- | --- |
| `DJANGO_SECRET_KEY` | 방금 생성한 값 |
| `DB_HOST` | RDS 엔드포인트. `https://`·포트 제외 |
| `DB_NAME` / `DB_USER` | `chatbot` / `chatbot` |
| `DB_PASSWORD` | RDS에서 만든 앱 계정 비밀번호 |
| `MYSQL_ROOT_PASSWORD` | 운영 Compose에서는 사용하지 않음. 로컬 MySQL용 항목 |
| `BACKEND_IMAGE` | ECR 저장소 URI 뒤에 `:manual-v1` 추가 |
| `DJANGO_ALLOWED_HOSTS` | 새 EC2 퍼블릭 DNS |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://실제CloudFront도메인` |
| `CHATBOT_MODE` | 우선 `demo` |
| `OPENAI_API_KEY` | demo에서는 비워 둠 |
| `S3_EXPORT_BUCKET` | 기존 대화 TXT 버킷 이름 |
| `AWS_DEFAULT_REGION` | `ap-northeast-2` |

**Ctrl + O → Enter → Ctrl + X**로 저장·종료. 운영 파일이 `DJANGO_COOKIE_SECURE=true`와 프록시 HTTPS 인식을 적용하므로 로그인 실습은 CloudFront HTTPS 주소에서 진행.

## 6. ECR 이미지로 실행

같은 EC2 폴더에서 아래 자리표시자를 실제 값으로 변경해 한 줄 실행. `ACCOUNT_ID`, 저장소의 `ALIAS`, `EC2_PUBLIC_DNS`를 변경하고 `manual-v1`은 앞에서 올린 태그 사용.

```bash
sudo bash deploy/deploy.sh manual-v1 ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com skn33-chatbot-backend-ALIAS EC2_PUBLIC_DNS
```

EC2 역할로 ECR 로그인 → 이미지 다운로드 → backend·gateway 실행 → DB 마이그레이션·상태 확인 순서. **EC2에서는 이미지를 빌드하거나 ECR로 업로드하지 않음.** 성공하면 `deploy/release.env`에 실행 이미지 기록.

```bash
sudo docker compose --env-file .env --env-file deploy/release.env -f compose.prod.yaml ps
curl -fsS -H 'Host: EC2_PUBLIC_DNS' http://127.0.0.1/api/health/
```

**확인 결과:** `backend`가 healthy, `gateway`가 실행 중이며 `0.0.0.0:80->80/tcp` 표시. API 응답의 `status`, `database`가 모두 `ok`. 이 시점에는 EC2 내부 연결까지만 확인한 것임. EC2의 `/`는 React를 제공하지 않으므로 404가 정상.

Nginx gateway는 API 전용임. HTTPS는 CloudFront에서 처리하며 gateway는 Django에 HTTPS 요청임을 알려줌. 이 설정은 **뷰어 HTTPS와 EC2 원본 접근 제한을 함께 유지하는 것**이 전제임.

## 7. 브라우저에서 전체 기능 확인

CloudFront 배포 설정 반영이 완료된 후 **내 PC 브라우저**에서 `https://실제CloudFront도메인` 접속.

1. React 로그인 화면 확인.
2. 새 회원가입·로그인 진행. 새 RDS에는 예전 회원 정보가 없음.
3. 질문을 보내고 demo 답변 확인.
4. 새로고침 후 기존 대화 조회.
5. **대화 내보내기 → TXT 다운로드**로 파일 받기.
6. **S3 → 기존 대화 버킷 → day2/ → chat-exports/**에서 생성된 TXT 확인.

| 증상 | 확인할 부분 |
| --- | --- |
| 화면 전체가 S3 AccessDenied | OAC·프론트 버킷 정책·기본 루트 객체·최상위 index.html |
| 화면은 보이지만 API 오류 | `/api/*` 원본·7개 메서드·캐시 비활성·EC2 80 소스 |
| 로그인 POST가 403 | CSRF 신뢰 출처에 실제 `https://CloudFront주소`, 쿠키·Origin 전달 |
| Django DisallowedHost | 허용 호스트가 EC2 원본 DNS인지 확인 |
| 대화 내보내기 실패 | EC2 역할 S3 경로·기존 버킷 이름·메타데이터 홉 제한 2 |
| API가 502·504 | EC2 인바운드·컨테이너 상태·백엔드 로그·원본 응답 시간 |

설정을 수정했다면 `restart`만 하지 말고 위 배포 명령으로 컨테이너 재생성. 최초 배포가 실패해 `release.env`가 없으면 `.env`의 `BACKEND_IMAGE`를 사용해 아래 로그 조회.

```bash
sudo docker compose --env-file .env -f compose.prod.yaml logs --tail=80 backend gateway
```

**확인 결과:** 화면·로그인·DB 저장·TXT 다운로드까지 성공해야 수동 배포 완료. 다음 CI/CD는 이 상태에서 시작.

> 기본 CloudFront 주소의 인증서는 AWS가 제공. 브라우저→CloudFront는 HTTPS지만 CloudFront→EC2는 HTTP인 학습 단계임. 7단계에서 ACM·ALB를 연결해 원본 구간도 HTTPS로 변경. [AWS HTTPS 안내](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-https-viewers-to-cloudfront.html)
