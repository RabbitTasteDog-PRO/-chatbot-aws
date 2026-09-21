# GitHub Actions로 프론트·백엔드 자동 배포

## 1. 자동화할 작업 확인

앞 단계에서 수동으로 배포한 **같은 `chatbot_aws` 소스**를 GitHub에 반영. 새 코드를 따로 만들지 않음.

```text
GitHub main 변경
  → Django 테스트·React 테스트와 빌드
  → OIDC로 AWS 임시 권한 획득
  → 백엔드 이미지 ECR 업로드
  → SSM으로 EC2 배포·HTTPS API 확인
  → React 빌드 파일 S3 업로드·CloudFront 캐시 갱신
  → 공개 화면과 API 확인
```

프론트·백엔드는 다른 경로로 배포하지만 이번 예제는 한 워크플로에서 순서대로 진행. 백엔드가 먼저 성공한 뒤 프론트를 교체하며, 두 서비스의 동시 교체나 자동 원복을 보장하는 방식은 아님.

## 2. GitHub 저장소 준비

1. GitHub에서 수업용 **새 저장소** 생성. README·라이선스 자동 생성은 선택하지 않음.
2. 저장소 URL 복사.
3. **내 PC의 `chatbot_aws` 폴더**에서 아래 명령 실행. `OWNER/REPOSITORY`를 본인의 값으로 변경.

```bash
git init
git branch -M main
git add .
git diff --cached --name-only
```

**확인 결과:** backend·frontend·deploy·infra·워크플로와 `.env.example`은 포함되고, 실제 `.env`, 개인 키, `node_modules`, 대화 파일은 없음. `git add` 전에 만든 비밀 백업도 목록에 없어야 함. 문제가 있으면 커밋 전에 제외.

```bash
git commit -m "Prepare React S3 and Django EC2 deployment"
git remote add origin https://github.com/OWNER/REPOSITORY.git
git push -u origin main
```

처음 push하면 **Test chatbot** CI가 AWS 없이 테스트·빌드를 검사. `AWS_DEPLOY_ROLE_ARN`이 없으면 AWS 배포는 건너뜀. **Actions → Test chatbot**에서 CI 성공을 먼저 확인한 뒤 OIDC를 연결. 기존 저장소를 사용하는 경우 `git init`, 원격 추가, 브랜치 생성은 반복하지 않고 현재 원격·브랜치 확인.

## 3. OIDC·SSM 권한 연결

[GitHub OIDC·SSM 권한 준비](09_GitHub_OIDC_SSM.md)를 진행. GitHub 역할은 **이 저장소의 main 브랜치**만 사용할 수 있게 제한. EC2 역할과 GitHub 역할은 다른 역할임.

| 역할 | 사용하는 주체 | 용도 |
| --- | --- | --- |
| EC2 앱 역할 | EC2·Django | ECR 다운로드, SSM 연결, 대화 TXT 저장 |
| GitHub 배포 역할 | GitHub Actions | ECR 업로드, 프론트 S3 업로드, CloudFront 갱신, 해당 EC2에 SSM 명령 |

AWS 액세스 키와 시크릿 키를 GitHub Secrets에 넣는 방식으로 바꾸지 않음. OIDC가 짧게 유효한 AWS 자격 증명을 발급함. `id-token: write`는 이 토큰 발급에 필요한 GitHub 권한임.

## 4. 저장소 변수 입력

**GitHub 저장소 → Settings → Secrets and variables → Actions → Variables → New repository variable**에서 하나씩 등록.

| 변수 이름 | 값 |
| --- | --- |
| `AWS_REGION` | `ap-northeast-2` |
| `AWS_ACCOUNT_ID` | AWS 계정의 12자리 ID |
| `ECR_BACKEND_REPOSITORY` | `skn33-chatbot-backend-ALIAS`. URI 전체가 아님 |
| `EC2_INSTANCE_ID` | **새 EC2**의 `i-...` |
| `ORIGIN_HOST` | 새 EC2 퍼블릭 DNS. 프로토콜·경로 제외 |
| `APP_URL` | `https://실제CloudFront도메인`. 마지막 `/` 제외 |
| `FRONTEND_BUCKET` | React 전용 S3 버킷 이름 |
| `CLOUDFRONT_DISTRIBUTION_ID` | CloudFront의 `E...` 배포 ID. 도메인이 아님 |
| `AWS_DEPLOY_ROLE_ARN` | **마지막에 등록.** OIDC 가이드에서 만든 GitHub 역할 ARN |

위 8개 배포 대상 변수를 먼저 등록하고, `AWS_DEPLOY_ROLE_ARN`은 **마지막에 등록하여 배포 활성화**. 09 가이드에서 이미 등록했다면 같은 값을 확인만 함.

DB 비밀번호·Django 키·LLM 키는 EC2 `.env`에 유지. 위 표에 없는 `FRONTEND_IMAGE`·프론트 ECR 저장소는 이번 구조에서 사용하지 않음.

## 5. 워크플로 실행과 확인

**GitHub → Actions → Deploy React and Django → Run workflow → main → Run workflow** 선택.

| 실행 단계 | 확인할 결과 |
| --- | --- |
| Test backend and build frontend | Django·React 테스트와 빌드 통과 |
| AWS credentials through OIDC | 역할 획득 성공 |
| Build and push backend image | ECR에 커밋·실행 ID가 포함된 새 태그 생성 |
| Deploy backend and verify HTTPS API | SSM 명령 완료, EC2 API·DB 정상 |
| Upload frontend and invalidate CloudFront | 프론트 업로드, 무효화 완료 |
| Verify public frontend and API | 공개 주소의 HTML과 API 정상 |

전체 성공 후 브라우저에서 로그인·기존 대화 조회·질문 전송·TXT 내보내기를 다시 확인. 테스트 통과와 실제 기능 확인은 다른 단계임.

**SSM 단계에서 실패하면:** **Systems Manager → Run Command → 명령 기록**에서 해당 명령의 인스턴스·출력을 확인. 이전 EC2 ID를 변수에 넣지 않았는지 확인. 출력에 비밀 설정 파일을 추가로 표시하지 않음.

## 6. 화면 변경을 자동 배포

**내 PC 편집기**에서 `frontend/src/App.jsx`의 화면 안내 문구 하나를 수정. API 경로나 로그인 로직은 바꾸지 않음.

```bash
git add frontend/src/App.jsx
git diff --cached
git commit -m "Update chatbot page text"
git push origin main
```

**확인 결과:** Actions가 자동 시작되고, 성공 후 브라우저에 수정한 문구 표시. 새 대화와 기존 대화가 모두 정상. 프론트 변경도 이번 단순 워크플로에서는 전체 검사를 거치며 백엔드 이미지도 새 버전으로 배포됨.

운영 Compose·Nginx·배포 스크립트를 수정한 경우에는 **EC2의 파일도 별도로 반영**해야 함. 현재 워크플로는 앱 이미지·React 파일을 자동 배포하며, EC2의 운영 파일 자체를 매번 덮어쓰지 않음. 앞 수동 배포 가이드의 SCP로 변경 파일을 전달한 뒤 배포.

## 7. 이전 버전 복구

[배포 확인·복구·자원 정리](10_배포_확인_복구_정리.md)의 순서로 진행.

실패한 배포는 성공 기록을 갱신하지 않지만 컨테이너는 후보 이미지로 바뀌었을 수 있음. **실패 직후 마지막 성공 버전은 `deploy/release.env`, 성공한 배포의 한 단계 전은 `deploy/previous.env`**에서 확인. 자동 원복으로 간주하지 않음.

백엔드 이미지 복구와 프론트 S3 파일 복구는 별도 작업이며, DB 스키마·EC2 운영 파일까지 자동으로 되돌아가지 않음. 이번 복구 실습은 DB 스키마를 바꾸지 않는 화면 문구 수정으로 진행.
