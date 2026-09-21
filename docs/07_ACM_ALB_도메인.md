# ACM·ALB로 사용자 도메인과 원본 HTTPS 연결

## 1. 도메인과 인증서 위치 확인

앞 단계의 CloudFront HTTPS와 CI/CD가 정상인 상태에서 진행. 도메인이 없으면 6단계까지 사용 가능하며, 이 단계에는 **소유한 도메인과 DNS 레코드 편집 권한**이 필요함. 도메인 구매·기관 DNS 승인·인증서 검증은 수업 전에 준비.

이번 예시의 `example.com`을 본인 도메인으로 변경.

| 주소 | 연결 대상 | ACM 인증서 리전 |
| --- | --- | --- |
| `www.example.com` | 사용자가 접속하는 CloudFront | **버지니아 북부 `us-east-1`** |
| `origin.example.com` | CloudFront가 호출하는 ALB | **서울 `ap-northeast-2`** |

도메인을 두 개 구매하는 것이 아니라 같은 도메인의 서브도메인 두 개를 사용. 두 인증서는 연결 서비스의 리전에 맞춰 별도로 준비. [AWS 인증서 리전 안내](https://aws.amazon.com/certificate-manager/faqs/)

## 2. ACM 인증서 요청

먼저 콘솔 리전을 **버지니아 북부**로 변경하고 **Certificate Manager → 인증서 요청 → 퍼블릭 인증서 요청** 선택.

| 항목 | 입력값 |
| --- | --- |
| 완전히 정규화된 도메인 이름 | `www.example.com` |
| 내보내기 설정이 있는 경우 | 내보내기 비활성화. ACM 통합 서비스에서 사용 |
| 검증 방법 | DNS 검증 |
| 키 알고리즘 | RSA 2048 |

요청 후 인증서 상세 화면의 **도메인 → CNAME 이름·값**을 DNS 서비스에 등록. Route 53에서 관리한다면 **Route 53에서 레코드 생성** 버튼 사용. 외부 DNS에서는 CNAME 유형으로 이름·값을 복사. 서비스가 이름 뒤에 도메인을 자동으로 붙이면 도메인이 두 번 반복되지 않게 확인.

**확인 결과:** 인증서 상태 `발급됨(Issued)`. 검증 레코드는 자동 갱신에도 사용하므로 삭제하지 않음.

이어서 리전을 **서울**로 변경하고 같은 절차로 `origin.example.com` 인증서를 요청·DNS 검증. 두 인증서가 발급된 후 진행.

## 3. ALB 보안 그룹 생성

서울 리전의 **EC2 → 보안 그룹 → 보안 그룹 생성** 열기. 이름 `skn33-day3-alb-ALIAS`, VPC는 현재 EC2와 같은 VPC 선택.

| 방향 | 유형·포트 | 소스 또는 대상 |
| --- | --- | --- |
| 인바운드 | HTTPS 443 | `com.amazonaws.global.cloudfront.origin-facing` 접두사 목록 |
| 아웃바운드 | HTTP 80 | 현재 EC2 보안 그룹 ID |

아웃바운드를 위 한 개로 제한하려면 기본 전체 허용을 해당 규칙으로 교체. 이 그룹은 ALB 전용이며 EC2에 연결하지 않음.

**EC2 보안 그룹 → 인바운드 규칙 편집**에서 HTTP 80의 소스로 **새 ALB 보안 그룹 ID**를 추가. 기존 CloudFront 접두사 목록 소스는 전환 성공 후 제거. SSH 내 IP와 RDS·HTTPS 아웃바운드는 유지.

## 4. 대상 그룹 생성

**EC2 → 로드 밸런싱 → 대상 그룹 → 대상 그룹 생성** 선택.

| 항목 | 선택·입력값 |
| --- | --- |
| 대상 유형 | 인스턴스 |
| 대상 그룹 이름 | `skn33-api-ALIAS` |
| 프로토콜·포트 | HTTP · 80 |
| VPC | EC2와 같은 VPC |
| 프로토콜 버전 | HTTP1 |
| 상태 검사 프로토콜 | HTTP |
| 상태 검사 경로 | `/alb-health/` |
| 성공 코드 | 200 |

**다음 → 새 EC2 선택 → 아래에 보류 중인 것으로 포함 → 대상 그룹 생성**. 포트는 8000이 아니라 gateway가 제공하는 80 사용.

`/alb-health/`는 gateway의 네트워크 상태 검사이며 DB 정상 여부까지 보장하지 않음. 최종 기능 검증은 `/api/health/`와 로그인·채팅으로 별도 진행. ALB 상태 검사의 IP 기반 Host로 Django 오류가 나지 않게 gateway 전용 경로를 사용.

## 5. ALB 생성

**EC2 → 로드 밸런서 → 로드 밸런서 생성 → Application Load Balancer → 생성** 열기.

| 화면 구역 | 선택·입력값 |
| --- | --- |
| 이름 | `skn33-alb-ALIAS` |
| 체계 | 인터넷 경계(Internet-facing) |
| IP 주소 유형 | IPv4 |
| 네트워크 매핑 → VPC | EC2와 같은 VPC |
| 매핑 | **새 EC2가 속한 가용 영역의 퍼블릭 서브넷**과 다른 가용 영역의 퍼블릭 서브넷 하나 선택 |
| 보안 그룹 | 방금 만든 ALB 전용 그룹만 선택 |
| 리스너 | HTTPS · 443 |
| 기본 작업 | 앞에서 만든 대상 그룹으로 전달 |
| 기본 SSL/TLS 인증서 | ACM에서 선택 → **서울의 `origin.example.com` 인증서** |

처음 표시되는 HTTP 80 리스너를 HTTPS 443으로 변경하거나 제거 후 추가. 이번 원본은 CloudFront가 HTTPS로만 호출하므로 공개 HTTP 리스너는 필요 없음.

**로드 밸런서 생성** 후 상태 `활성(Active)` 대기. **대상 그룹 → 대상**에서 새 EC2의 상태가 `Healthy`인지 확인. 두 가용 영역을 선택해도 EC2가 두 대 생성되는 것은 아님. 단일 EC2 실습이므로 앱 자체가 다중 서버 고가용성 구성은 아님.

**비용:** ALB는 EC2와 별도 요금이 발생하고 EC2를 중지해도 ALB 비용이 없어지지 않음. 실습 완료 후 유지할지 삭제할지 결정. [AWS ALB 요금](https://aws.amazon.com/elasticloadbalancing/pricing/)

## 6. 원본 도메인을 ALB에 연결

**Route 53 → 호스팅 영역 → 본인 도메인 → 레코드 생성** 열기.

| 항목 | 입력값 |
| --- | --- |
| 레코드 이름 | `origin` |
| 유형 | A |
| 별칭 | 켬 |
| 트래픽 라우팅 대상 | Application and Classic Load Balancer에 대한 별칭 |
| 리전·로드 밸런서 | 서울·방금 만든 ALB |

외부 DNS를 사용하는 경우 `origin` CNAME의 대상으로 ALB의 DNS 이름을 입력. `https://`와 경로를 붙이지 않음. ACM 검증 CNAME과 서비스 연결 레코드는 서로 다른 레코드임.

**확인 결과:** `origin.example.com`이 ALB를 가리킴. ALB DNS 자체는 본인 인증서의 도메인이 아니므로 CloudFront 원본에 `...elb.amazonaws.com`을 그대로 넣고 인증서 이름을 무시하지 않음.

## 7. Django와 CloudFront 원본 변경

**EC2 터미널**에서 `.env` 열기.

```bash
cd /home/ubuntu/chatbot-aws
nano .env
```

전환 중에는 기존 값에 새 값을 **쉼표로 추가**. 아래는 해당 두 항목만 수정하는 예시.

```text
DJANGO_ALLOWED_HOSTS=EC2_PUBLIC_DNS,origin.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://CLOUDFRONT_DOMAIN,https://www.example.com
```

현재 이미지 태그는 비밀값이 없는 `deploy/release.env`에서 확인. 아래 `CURRENT_TAG`에 입력해 같은 이미지로 환경 설정 반영.

```bash
cat deploy/release.env
sudo bash deploy/deploy.sh CURRENT_TAG ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com skn33-chatbot-backend-ALIAS origin.example.com
```

**CloudFront → 배포 → 원본 → django-ec2 → 편집** 열기.

| 변경 항목 | 변경 후 |
| --- | --- |
| 원본 도메인 | `origin.example.com` |
| 프로토콜 | **HTTPS only** |
| HTTPS 포트 | 443 |
| 원본 SSL 프로토콜 | TLSv1.2 |

원본 이름은 기존 이름을 유지해도 됨. `/api/*`는 같은 원본을 계속 사용하며 `CachingDisabled`, `AllViewerExceptHostHeader` 유지. 저장 후 전파 대기.

**확인 결과:** 기존 CloudFront HTTPS 주소에서 `/api/health/`, 로그인·채팅 정상. 이때 원본 Host는 `origin.example.com`이므로 Django 허용 호스트와 일치해야 함.

## 8. 서비스 도메인을 CloudFront에 연결

**CloudFront → 배포 → 일반 → 설정 편집**에서 아래 값 입력.

| 항목 | 값 |
| --- | --- |
| 대체 도메인 이름(CNAME) | `www.example.com` |
| 사용자 지정 SSL 인증서 | **버지니아 북부의 `www.example.com` ACM 인증서** |

저장 후 Route 53에서 `www` A 별칭 레코드를 만들고 대상은 **CloudFront 배포** 선택. 외부 DNS는 `www` CNAME → CloudFront 배포 도메인으로 연결.

**내 PC 브라우저**에서 `https://www.example.com`을 열어 로그인·질문·대화 저장·TXT 다운로드 확인. 새 도메인에서는 기존 CloudFront 도메인과 쿠키가 다르므로 다시 로그인.

## 9. CI/CD 변수와 보안 그룹 마무리

**GitHub → Settings → Secrets and variables → Actions → Variables**에서 아래 두 변수 변경.

| 변수 | 변경 후 |
| --- | --- |
| `ORIGIN_HOST` | `origin.example.com` |
| `APP_URL` | `https://www.example.com` |

워크플로를 한 번 실행해 새 도메인으로 자동 배포 검사까지 성공하는지 확인.

**EC2 보안 그룹 인바운드**의 기존 HTTP 80 → CloudFront 접두사 목록 규칙 제거. HTTP 80 → ALB 보안 그룹만 유지. `.env`의 이전 EC2 DNS와 CloudFront CSRF 주소는 더 이상 사용하지 않기로 했다면 정리 후 재배포.

**최종 연결표**

| 구간 | 연결 |
| --- | --- |
| 브라우저 → CloudFront | HTTPS · www 도메인 인증서 |
| CloudFront → React S3 | OAC 서명·HTTPS |
| CloudFront → ALB | HTTPS · origin 도메인 인증서 |
| ALB → EC2 gateway | VPC 내부 HTTP 80 · ALB 보안 그룹만 허용 |
| EC2 → RDS | MySQL 3306 · TLS |
| EC2 → 대화 S3 | HTTPS · EC2 역할 |

ALB→EC2 구간은 HTTP이므로 모든 구간이 TLS라는 의미는 아님. EC2에서 인증서를 직접 관리하지 않고 ALB에서 인증서를 사용하는 구조임.

새 환경 검증이 끝나면 보관했던 **기존 EC2**의 필요한 데이터가 확보됐는지 확인하고 종료. 새 EC2·기존 대화 버킷을 잘못 선택하지 않음. 사용하지 않는 이전 EBS·탄력적 IP가 남아 있는지도 확인.

다음: [배포 확인·복구·자원 정리](10_배포_확인_복구_정리.md).
