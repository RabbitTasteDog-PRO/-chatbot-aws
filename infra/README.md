# 권한 템플릿

대문자 자리표시자를 실제 값으로 바꾼 사본을 AWS에 적용한다. 이 파일은 리소스를 자동 생성하지 않는다.

| 파일 | 연결 대상 |
|---|---|
| `local-publish-policy.json` | 로컬 AWS CLI로 수동 배포하는 IAM 사용자·역할 |
| `ec2-app-policy.json` | EC2 인스턴스 역할. 별도로 `AmazonSSMManagedInstanceCore` 연결 |
| `github-trust-policy.json` | GitHub 배포 역할의 신뢰 정책. 저장소와 `main` 브랜치를 제한 |
| `github-deploy-policy.json` | 위 GitHub 배포 역할의 권한 정책 |
| `frontend-bucket-policy.json` | 프론트 S3 버킷 정책. CloudFront OAC 생성 후 배포 ID를 지정 |

`ACCOUNT_ID`, `BACKEND_REPOSITORY`, `FRONTEND_BUCKET`, `EXPORT_BUCKET`, `DISTRIBUTION_ID`, `INSTANCE_ID`, `EXACT_MAIN_SUB`를 치환한다. `EXPORT_BUCKET`과 `FRONTEND_BUCKET`은 다른 버킷이다. S3 버킷 퍼블릭 액세스 차단은 유지한다. 예제는 기본 SSE-S3 암호화를 사용한다. 사용자 지정 KMS 키를 선택했다면 별도의 KMS 권한이 필요하다.

`GetAuthorizationToken`과 `GetCommandInvocation`은 리소스 수준 제한을 지원하지 않아 `Resource: "*"`를 사용한다. ECR 이미지·S3 객체·SSM 대상 인스턴스는 실제 리소스로 제한한다. EC2 역할은 이미지를 읽고 대화 TXT만 읽고 쓸 수 있으며, 프론트 배포 권한이 없다.

로컬 CLI 로그인 권한과 인프라 생성·역할 연결 권한은 기관 관리자에게 별도로 확인한다. 배포 역할에 관리자 권한을 추가하지 않는다. GitHub에는 AWS 액세스 키를 저장하지 않는다.

# CloudFront 설정 계약

| 항목 | 기본 동작 | API 동작 |
|---|---|---|
| 경로 | Default `*` | `/api/*` |
| 원본 | 비공개 S3 REST 원본 + OAC | 초기 EC2 공개 DNS HTTP80 → 최종 ALB용 DNS HTTPS443 |
| Viewer protocol | Redirect HTTP to HTTPS | HTTPS only |
| 허용 메서드 | GET, HEAD | GET, HEAD, OPTIONS, PUT, POST, PATCH, DELETE |
| 캐시 정책 | CachingOptimized | CachingDisabled |
| Origin request policy | 없음 | AllViewerExceptHostHeader |

Default root object는 `index.html`로 설정한다. 원본 경로(Origin path)는 비워 둔다. API 원본 Host가 Django `ALLOWED_HOSTS`에 포함되어야 한다. Viewer 주소는 `CSRF_TRUSTED_ORIGINS`에 `https://`를 붙여 등록한다. API의 쿠키·쿼리·헤더 전달이 로그인과 CSRF 처리에 필요하다. 전체 배포의 403/404를 index.html로 바꾸는 오류 응답 설정은 하지 않는다. 현재 프론트는 클라이언트 URL 라우터를 사용하지 않아 SPA fallback이 필요하지 않다.

CloudFront viewer는 항상 HTTPS이다. `deploy/nginx.conf`는 이 전제에서 프록시 HTTPS 헤더를 고정한다. 초기 EC2 80 인바운드는 CloudFront origin-facing 관리형 접두사 목록으로, ALB 전환 후에는 ALB 보안 그룹만으로 제한한다. 관리형 접두사 목록은 자신의 CloudFront만 식별하는 장치는 아니며 운영 서비스는 별도 원본 접근 검증도 고려한다.

ALB 상태 확인 경로는 `/alb-health/`이다. 이 응답은 Nginx의 연결 상태만 확인하며, 앱·RDS 검증은 `/api/health/`로 수행한다. ALB 인증서는 서울, CloudFront 사용자 도메인 인증서는 버지니아 북부에서 발급한다.

공식 문서: [ECR push 권한](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-push-iam.html), [CloudFront 원본 요청 정책](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-managed-origin-request-policies.html), [S3 OAC](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html).
