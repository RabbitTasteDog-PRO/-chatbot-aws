# 3일차 실습 순서·준비

## 1. 오늘 바뀌는 배포 방식

1·2일차에서 사용한 챗봇의 회원가입·로그인·대화를 이어서 사용. 새 프로젝트 `chatbot_aws`에는 **대화 TXT를 S3에 저장하고 임시 URL로 다운로드하는 기능**도 포함됨.

React는 별도 S3 버킷에서 제공하고, Django는 ECR 이미지로 새 EC2에서 실행. 데이터는 RDS에 저장. 먼저 수동 배포를 확인하고 같은 프로젝트를 GitHub Actions로 자동 배포함.

```text
사용자 → CloudFront HTTPS ┬→ React 전용 S3
                         └→ /api/* → EC2 gateway → Django → RDS
                                                        └→ 기존 대화 TXT S3

수동 배포: 내 PC → backend 이미지 ECR / React dist S3
자동 배포: GitHub Actions → backend ECR·SSM / React S3·CloudFront 갱신
마지막 확장: 서비스 도메인 → CloudFront → HTTPS ALB → EC2
```

EC2의 gateway는 API만 전달하는 Nginx임. React 컨테이너를 운영 EC2에서 실행하지 않음. 프론트 ECR 저장소도 만들지 않음.

## 2. 시작 상태와 실습 파일

[실습 파일과 계정 권한 준비](00_권한_준비.md)부터 진행. 새 프로젝트 ZIP을 별도 폴더에 풀고 기존 소스와 구분. 실제 `.env`·키·인증서는 배포 파일에 포함하지 않음.

기존 EC2는 필요한 파일을 확보한 뒤 중지하고 새 배포 검증 후 삭제. 기존 S3 버킷은 TXT 저장용으로 유지. 삭제한 RDS는 새로 만들며 기존 회원·대화가 자동 복원되지는 않음.

**내 PC:** Mac 터미널 또는 Windows WSL Ubuntu에서 Docker·Node.js 24 LTS·Git·AWS CLI 준비. AWS 로그인도 같은 터미널 환경에서 진행. 기관 계정의 IAM 생성·연결 권한은 수업 전에 확인.

**새 EC2:** Ubuntu 24.04 x86, 작업 폴더 `/home/ubuntu/chatbot-aws`. 기존 `~/aws-day1/app`에서 명령을 이어 실행하지 않음. 새 운영 파일은 `compose.prod.yaml`, 마지막 성공 이미지 기록은 `deploy/release.env` 사용.

## 3. 실습 순서

| 단계 | 가이드 | 확인 결과 |
| --- | --- | --- |
| 사전 준비 | [실습 파일과 계정 권한 준비](00_권한_준비.md) | 배포 자료·도구·EC2 역할·기관 권한 준비 |
| 1 | [새 EC2 준비와 기존 환경 보관](01_새_EC2_준비.md) | 새 EC2의 SSH·Docker·SSM·역할 접근 확인 |
| 2 | [RDS MySQL 생성과 앱 계정 준비](02_RDS_MySQL_준비.md) | 같은 VPC의 비공개 MySQL과 TLS 앱 계정 |
| 3 | [대화 저장 버킷 유지와 React 버킷 생성](03_S3_버킷_준비.md) | 기존 TXT 버킷과 새 React 버킷 구분 |
| 4 | [ECR 접근 권한](08_ECR_접근권한.md) → [로컬 빌드·업로드](04_로컬_빌드_ECR_S3_업로드.md) | backend 이미지 하나는 ECR, React dist는 S3 |
| 5 | [EC2 백엔드 실행과 CloudFront 연결](05_EC2_실행_CloudFront_연결.md) | HTTPS 주소에서 로그인·채팅·TXT 저장과 다운로드 성공 |
| 6 | [GitHub CI 준비](06_GitHub_Actions_CICD.md) → [OIDC·SSM](09_GitHub_OIDC_SSM.md) → [자동 배포 실행](https://app.notion.com/p/3decd3dc5e9481fe8eaffc9579c8ac60) | main 변경 후 프론트·백엔드 갱신 |
| 7 | [ACM·ALB·사용자 도메인](07_ACM_ALB_도메인.md) | 서비스 도메인 HTTPS와 CloudFront→ALB HTTPS |
| 마무리 | [배포 확인·복구·정리](10_배포_확인_복구_정리.md) | 이전 버전 복구·데이터 보존·불필요한 자원 정리 |

3일차는 **6교시**임. 1~3단계의 자원 생성·대기와 기관 권한·도메인 준비를 사전에 완료한 상태에서 4~6단계를 중심으로 진행. 7단계까지의 가이드는 제공하며 수업 진행 속도와 도메인 준비에 따라 마지막 실습 또는 후속 실습으로 진행. 아직 수동 배포가 확인되지 않으면 자동화부터 진행하지 않음.

별도 도메인이 없어도 5~6단계는 CloudFront 기본 HTTPS 주소로 진행 가능. 7단계는 도메인과 DNS 편집 권한 필요. CloudFront 기본 인증서·EC2 HTTP 구간과, 사용자 도메인의 ACM·ALB HTTPS 구간을 구분.

[참고: Django만 사용하는 AWS 배포 가이드](https://app.notion.com/p/3decd3dc5e9481afaf1ecc15d7ef1494)는 수업 마지막에 제공하는 참고 자료이며, 이번 실습에서 Django 템플릿 구조로 변경하지 않음.

## 4. 입력값 기록

| 값 | 찾는 위치와 사용하는 곳 |
| --- | --- |
| `ALIAS` | 본인·팀을 구분할 영문 소문자·숫자 별칭. 리소스 이름에 일관되게 사용 |
| 계정 ID | AWS 우측 상단 계정 메뉴의 12자리 숫자 |
| 새 인스턴스 ID·VPC·보안 그룹 | 새 EC2 세부 정보·보안 탭. GitHub·RDS에는 이전 EC2 값 입력하지 않음 |
| `EC2_PUBLIC_DNS` | 탄력적 IP 연결 후 EC2 퍼블릭 DNS. 초기 API 원본과 Django 허용 호스트 |
| `RDS_ENDPOINT` | RDS 연결 및 보안. DB 접속용 주소 |
| `EXPORT_BUCKET` | 기존 대화 TXT 버킷 이름 |
| `FRONTEND_BUCKET` | 새 React 버킷 이름 |
| CloudFront ID·도메인 | CloudFront 일반 탭. 배포 ID와 브라우저 주소를 구분 |
| `ORIGIN_HOST` | 초기 EC2 DNS → ALB 전환 후 `origin.example.com` |
| `APP_URL` | 초기 `https://d....cloudfront.net` → 도메인 연결 후 `https://www.example.com` |
| GitHub 저장소 | `backend/`, `frontend/`, `.github/`가 저장소 최상위에 보이는 새 수업 저장소 |

비밀번호·Django 키·LLM 키는 위 기록표나 GitHub에 적지 않음. 실제 값은 EC2에서 `.env.example`을 복사한 `.env`에 입력.
