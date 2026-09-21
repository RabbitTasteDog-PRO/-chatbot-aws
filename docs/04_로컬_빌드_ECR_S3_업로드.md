# 내 PC에서 백엔드 ECR 업로드와 React S3 배포

## 1. 새 프로젝트 열기

사전 준비에서 압축 해제한 `chatbot_aws` 폴더 사용. 기존 `_chatbot_fullstack`과 다른 폴더임. 아직 준비하지 않았다면 배포 자료의 `chatbot_aws.zip`을 압축 해제하고 [권한 준비](00_권한_준비.md)를 먼저 진행.

이 페이지의 명령은 **Mac 터미널 또는 Windows의 WSL Ubuntu 터미널**에서 실행. Windows는 Docker Desktop의 WSL 통합을 활성화. PowerShell에서는 아래 Bash 줄바꿈을 그대로 사용하지 않음.

터미널을 압축 해제한 `chatbot_aws` 폴더에서 열고 확인.

```bash
pwd
ls -a
docker version
node --version
aws --version
aws sts get-caller-identity --profile skn33
```

**확인 결과:** `backend`, `frontend`, `deploy`, `compose.prod.yaml`, `.env.example`, `.github`가 있고 Docker Client·Server가 동작. Node.js 24 LTS와 AWS CLI v2 사용. 로그인은 [권한 준비](00_권한_준비.md)의 `skn33` 프로필 사용.

| 배포 대상 | 만드는 결과 | 올리는 곳 |
| --- | --- | --- |
| Django | `linux/amd64` Docker 이미지 | ECR |
| React | `frontend/dist/`의 파일 | 프론트 전용 S3 |

## 2. ECR 저장소 생성

[접근 권한 가이드](08_ECR_접근권한.md)에서 저장소를 이미 만들었다면 이름·태그 변경 불가 설정·URI만 확인하고 생성은 생략. 저장소 이름을 미리 정해 IAM 정책에 지정하는 것도 가능함.

**AWS 콘솔 → ECR → 프라이빗 레지스트리 → 리포지토리 → 리포지토리 생성** 열기.

| 항목 | 선택·입력값 |
| --- | --- |
| 리전 | 서울 |
| 저장소 이름 | `skn33-chatbot-backend-ALIAS` |
| 이미지 태그 변경 가능성 | **Immutable / 변경 불가** |
| 암호화 | AES-256 기본값 |

생성 후 목록의 **URI** 복사. `ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com/skn33-chatbot-backend-ALIAS` 형태임. `ACCOUNT_ID`는 AWS 계정의 12자리 ID.

## 3. ECR 로그인과 백엔드 빌드

**내 PC의 `chatbot_aws` 폴더**에서 실행. 아래의 `ACCOUNT_ID`와 저장소 이름의 `ALIAS`를 실제 값으로 변경. 프로필 이름은 `skn33` 그대로 사용.

```bash
aws ecr get-login-password --region ap-northeast-2 --profile skn33 | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com
```

**확인 결과:** `Login Succeeded`. 이 명령은 내 PC Docker가 ECR에 접근하게 하는 로그인임.

```bash
docker buildx build --platform linux/amd64 --load -t chatbot-backend:manual-v1 ./backend
docker tag chatbot-backend:manual-v1 ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com/skn33-chatbot-backend-ALIAS:manual-v1
docker push ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com/skn33-chatbot-backend-ALIAS:manual-v1
```

Apple Silicon Mac에서도 `--platform linux/amd64` 유지. 이번 EC2는 x86이므로 이미지도 같은 아키텍처로 빌드. `.env`는 이미지에 넣지 않으며 서버에서 별도로 준비.

**확인 결과:** ECR 저장소의 **이미지** 탭에 `manual-v1`과 이미지 digest 표시. 다시 빌드해서 올릴 경우 `manual-v2`처럼 **세 명령의 태그를 함께 변경**. 변경 불가 저장소의 기존 태그를 덮어쓰지 않음.

## 4. React 빌드

같은 프로젝트에서 프론트 폴더로 이동.

```bash
cd frontend
npm ci
npm test
npm run build
cd ..
ls frontend/dist
```

**확인 결과:** 테스트 통과 후 `index.html`과 `assets` 표시. React는 `/api/` 상대 주소로 요청하므로 EC2 IP를 프론트 코드에 넣지 않음. 5단계에서 CloudFront가 API 요청을 백엔드로 연결.

## 5. 빌드 파일을 프론트 버킷에 업로드

`FRONTEND_BUCKET`을 새 React 버킷 이름으로 변경. **기존 대화 저장 버킷 이름을 넣지 않음.** 아래 세 명령 실행.

```bash
aws s3 sync frontend/dist/assets/ s3://FRONTEND_BUCKET/assets/ --cache-control 'public,max-age=31536000,immutable' --region ap-northeast-2 --profile skn33
aws s3 sync frontend/dist/ s3://FRONTEND_BUCKET/ --exclude 'assets/*' --exclude index.html --cache-control 'no-cache' --region ap-northeast-2 --profile skn33
aws s3 cp frontend/dist/index.html s3://FRONTEND_BUCKET/index.html --content-type text/html --cache-control 'no-cache,no-store,must-revalidate' --region ap-northeast-2 --profile skn33
```

해시가 포함된 JS·CSS는 오래 캐시하고, 새 파일 이름을 가리키는 `index.html`은 다시 확인하게 함. 이번 업로드에서는 이전 자산을 삭제하지 않아 이미 페이지를 연 브라우저의 파일 요청을 보호.

**확인 결과:** **S3 → 프론트 버킷 → 객체**에서 최상위 `index.html`, `assets/` 확인. `dist/index.html`처럼 한 단계 안쪽에 올라가지 않아야 함. 버킷의 객체 URL로 직접 열 때 AccessDenied가 나오는 것은 비공개 상태이므로 정상. 다음 페이지에서 CloudFront로 접속.

## 6. EC2에 운영 파일 전달

새 EC2의 폴더는 앞 RDS 단계에서 `/home/ubuntu/chatbot-aws`로 준비한 상태임. 아래 `KEY_FILE_PATH`를 내 PC의 `skn33-aws-key.pem` 경로, `EC2_PUBLIC_IPV4`를 새 EC2 주소로 변경.

```bash
scp -i "KEY_FILE_PATH" compose.prod.yaml .env.example ubuntu@EC2_PUBLIC_IPV4:/home/ubuntu/chatbot-aws/
scp -i "KEY_FILE_PATH" -r deploy ubuntu@EC2_PUBLIC_IPV4:/home/ubuntu/chatbot-aws/
```

EC2에는 빌드할 소스 전체 대신 운영 Compose·배포 스크립트·환경 예시를 전달. 백엔드 코드는 ECR 이미지로 받음. 실제 `.env`는 다음 페이지에서 EC2 안에 생성.
