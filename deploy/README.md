# 배포 명령 계약

이 저장소의 루트에 `backend/`, `frontend/`, `.github/`가 위치하도록 GitHub에 올린다. EC2에는 프로젝트의 운영 파일을 `/home/ubuntu/chatbot-aws`에 준비한다. `.env`와 `certs/global-bundle.pem`은 EC2에서 별도로 생성한다. 최초 실행 전 `release.env`를 만들 필요는 없다.

## 수동 백엔드 배포

EC2에서 다음 형식으로 실행한다. `ORIGIN_HOST`는 CloudFront API 원본 DNS와 같으며, `DJANGO_ALLOWED_HOSTS`에도 있어야 한다.

```bash
sudo bash deploy/deploy.sh TAG ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com BACKEND_REPOSITORY ORIGIN_HOST
```

최초에는 EC2 내부 API·RDS 연결을 확인한다. CloudFront 구성이 끝난 뒤에는 마지막 인자로 `https://VIEWER_DOMAIN`을 추가하여 공개 API까지 검사한다.

검증이 성공하면 `deploy/release.env`에 실행한 이미지가 기록되고, 직전 성공 이미지는 `deploy/previous.env`로 보관된다. 실패 시 실행 중인 컨테이너가 후보 버전으로 변경되어 있을 수 있다. 성공 기록을 읽기만 하고 자동 롤백은 수행하지 않는다.

## 백엔드 롤백

실패한 배포 직후에는 `cat deploy/release.env`의 마지막 성공 태그로 복구한다. 새 배포가 성공했지만 그 이전으로 돌아가려면 `cat deploy/previous.env`에서 태그를 확인한다. 위 명령의 `TAG`를 선택한 태그로 바꾸어 다시 실행한다. 이미지 태그는 덮어쓰지 않도록 ECR 저장소를 Immutable로 설정한다. DB 마이그레이션은 자동으로 되돌리지 않으므로 이전 코드와 스키마가 호환될 때만 이미지 롤백을 수행한다.

프론트 롤백은 이전 Git 커밋을 로컬의 별도 작업 디렉터리에서 빌드하고 `frontend.sh`로 다시 업로드한다. 이전 해시 자산은 삭제하지 않으므로 기존 열린 화면에 필요한 파일도 유지된다. GitHub `main`의 변경 취소 커밋으로 프론트·백엔드를 함께 다시 배포할 수도 있다.

## 프론트 배포

로컬에서 `frontend/`의 `npm ci`, `npm run build`를 완료한 뒤 프로젝트 루트에서 실행한다.

```bash
AWS_PROFILE=skn33 bash deploy/frontend.sh FRONTEND_BUCKET DISTRIBUTION_ID frontend/dist
```

GitHub Actions는 OIDC 자격 증명을 사용하므로 `AWS_PROFILE`을 지정하지 않는다. `assets/` 해시 파일 업로드 → 나머지 정적 파일 → `index.html` → CloudFront 캐시 무효화 완료 순서이다. 별도 프론트 버킷에만 실행한다. 대화 TXT 버킷을 지정하지 않는다.

## GitHub Actions

Repository Variables: `AWS_REGION=ap-northeast-2`, `AWS_ACCOUNT_ID`, `ECR_BACKEND_REPOSITORY`, `EC2_INSTANCE_ID`, `ORIGIN_HOST`, `APP_URL=https://VIEWER_DOMAIN`, `FRONTEND_BUCKET`, `CLOUDFRONT_DISTRIBUTION_ID`, `AWS_DEPLOY_ROLE_ARN`.

`Test chatbot`은 AWS 없이 최초 push부터 테스트한다. 자동 배포는 `AWS_DEPLOY_ROLE_ARN`이 비어 있으면 건너뛴다. 나머지 Variables와 IAM 신뢰 정책을 모두 준비한 후 **`AWS_DEPLOY_ROLE_ARN`을 마지막에 등록**하고 Deploy 워크플로를 수동 실행한다.

`Inspect OIDC claims`를 `main`에서 먼저 실행해 `aud`, `sub`를 확인하고 IAM 신뢰 정책을 완성한다. `Deploy React and Django`는 테스트 → backend image push → SSM API 검증 → frontend upload → 공개 화면/API 검증 순서로 실행한다. 완료 기록은 모든 단계가 성공한 경우에만 GitHub Step Summary에 남는다. 백엔드 성공 기록은 백엔드 검증 완료 시점에 별도로 기록된다.

워크플로는 앱 이미지와 프론트 파일만 배포한다. `compose.prod.yaml`, `deploy/nginx.conf`, EC2 배포 스크립트를 변경한 경우 EC2 운영 파일을 별도로 동기화해야 한다. `.env`를 Git이나 SSM 명령에 넣지 않는다.

## 로컬 검증

```bash
python3 -m unittest discover -s deploy -p 'test_*.py'
bash -n deploy/deploy.sh
bash -n deploy/frontend.sh
```

테스트는 AWS 호출을 모의 처리한다. 실제 IAM 권한·CloudFront 로그인·RDS 연결·S3 내보내기는 AWS 실습에서 별도로 확인한다.
