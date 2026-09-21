# ECR 저장소·EC2 이미지 접근 권한 준비

## 1. 백엔드 이미지 저장소 만들기
**ECR:** Docker 이미지를 저장하는 AWS 서비스임. 소스 코드를 보관하는 GitHub와 달리, 실행할 수 있도록 빌드한 이미지를 보관함.
이번 프로젝트는 Django 백엔드 이미지 하나만 ECR에 저장. React는 빌드 결과인 `dist/`를 별도 프론트 S3 버킷에 업로드함.
1. AWS 콘솔의 리전을 **아시아 태평양(서울)**로 선택.
2. 검색창에서 **Elastic Container Registry**를 검색해 열기.
3. **프라이빗 레지스트리 → 리포지토리 → 리포지토리 생성** 선택.
4. 다음 값으로 backend 저장소 생성.

| 항목 | 입력·선택 |
| --- | --- |
| 표시 여부 | 프라이빗 |
| 리포지토리 이름 | `skn33-chatbot-backend-ALIAS` |
| 이미지 태그 변경 가능성 | 변경 불가능 / Immutable |
| 태그 변경 제외 필터 | 추가하지 않음 |
| 암호화 | AES-256 기본 설정 |

`ALIAS`은 본인 또는 팀을 구분하는 소문자 영문·숫자로 변경. 예: `skn33-chatbot-backend-team01`.
생성한 저장소의 **URI**를 복사해 기록.
```text
ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com/skn33-chatbot-backend-ALIAS
```
`ACCOUNT_ID`는 AWS 콘솔 오른쪽 위 계정 메뉴에서 확인하는 12자리 계정 ID임. IAM 사용자 이름이 아님.
**확인 결과:** 백엔드 저장소 한 개가 보이며 이미지 목록은 비어 있음. Immutable은 같은 태그의 이미지를 덮어쓰지 못하게 하는 설정임. 재빌드할 때는 새로운 버전 태그를 사용.
> **AccessDenied가 나오면:** 학원 IAM 사용자에게 저장소 생성 권한이 없는 상태일 수 있음. 관리자에게 위 저장소 생성을 요청. 콘솔 사용 권한과 이후 EC2에 부여할 역할 권한은 서로 다름.
## 2. 내 PC에서 사용할 IAM 사용자 권한 준비
처음에는 **내 PC에서 백엔드 이미지를 ECR에, React 빌드 파일을 프론트 S3에 업로드**함. 이후 GitHub Actions가 같은 작업을 자동 수행하고, EC2는 백엔드 이미지를 내려받아 실행함.
로컬 AWS 로그인에는 학원에서 제공한 본인 IAM 사용자를 사용. 아래 권한은 **EC2 역할이 아니라 로컬 로그인에 사용할 IAM 사용자**에 필요함. 학원에서 그룹으로 권한을 관리하면 관리자에게 해당 그룹에 적용하도록 요청.
1. AWS 콘솔에서 **IAM → 사용자 → 본인 IAM 사용자 → 권한** 열기.
2. **권한 추가 → 권한 추가 → 직접 정책 연결**에서 `SignInLocalDevelopmentAccess` 검색·선택 후 추가. 이미 사용자 또는 소속 그룹에 연결되어 있으면 중복 추가하지 않음.
3. 내 PC 편집기에서 새 프로젝트의 `chatbot_aws/infra/local-publish-policy.json` 열기.
4. 아래 자리표시자를 실제 값으로 변경한 JSON 사본 준비. 실제 계정의 비밀번호나 액세스 키를 넣지 않음.

| 자리표시자 | 입력값 |
| --- | --- |
| `ACCOUNT_ID` | 12자리 AWS 계정 ID |
| `BACKEND_REPOSITORY` | `skn33-chatbot-backend-ALIAS` 전체 저장소 이름 |
| `FRONTEND_BUCKET` | 새로 만든 React 배포용 버킷 이름. 대화 TXT 버킷이 아님 |
| `DISTRIBUTION_ID` | CloudFront 생성 후 확인할 배포 ID `E...` |

아직 CloudFront를 만들지 않았다면 JSON의 `cloudfront:CreateInvalidation`, `cloudfront:GetInvalidation`을 포함한 Statement만 사본에서 제외. CloudFront 생성 후 실제 배포 ID를 넣어 같은 정책에 추가. 미완성 자리표시자를 그대로 적용하지 않음.
1. 사용자 **권한 → 권한 추가 → 인라인 정책 생성 → JSON** 선택.
2. 준비한 JSON 전체 붙여넣기 → **다음** → 정책 이름 `Day3LocalPublish` → **정책 생성**.
`SignInLocalDevelopmentAccess`는 CLI 브라우저 로그인 권한임. `Day3LocalPublish`는 백엔드 ECR 업로드, 프론트 S3 목록·읽기·업로드, 지정 CloudFront 캐시 무효화 권한임. 인프라 생성 권한은 별도임. 이 배포는 파일을 일괄 삭제하지 않으므로 `s3:DeleteObject`를 부여하지 않음.
**확인 결과:** 로그인 권한과 본인 백엔드 저장소·프론트 버킷의 배포 권한이 적용됨. 기존 `Day3EcrPush`만 있다면 S3 업로드 권한까지 충족하는지 관리자와 확인.
> **권한 추가가 불가능하면:** 학원 관리자에게 정책 적용을 요청. 기관이 브라우저 로그인을 허용하지 않으면 기관에서 승인한 기존 AWS CLI 프로필·임시 자격 증명으로 진행. 임의로 새 장기 액세스 키를 만들지 않음.
## 3. 내 PC의 Docker·AWS CLI 준비
**Mac은 터미널, Windows는 WSL Ubuntu 터미널**에서 진행. SSH로 접속한 EC2 터미널이 아님. 이후 로컬 빌드·업로드도 같은 환경에서 실행하여 AWS 프로필을 함께 사용.
Docker Desktop을 실행한 상태에서 아래 명령을 한 줄씩 실행.
```bash
docker version
docker info --format '{{.OSType}}'
docker buildx version
```
**확인 결과:** Docker의 Client·Server 정보가 모두 나오고, 컨테이너 OS는 `linux`로 표시됨. Windows에서 연결 오류가 나면 Docker Desktop의 **Settings → Resources → WSL Integration**에서 사용할 Ubuntu 통합을 활성화.
이어서 같은 터미널에서 AWS CLI 버전 확인.
```bash
aws --version
```
`aws login`을 사용하려면 **AWS CLI v2.32.0 이상**이 필요함. 조건을 만족하면 설치 부분은 건너뛰고 아래 로그인 진행.
### Mac에서 설치·업데이트
[AWS CLI 공식 설치 안내](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)의 **macOS → PKG 설치 프로그램**을 내려받아 실행. 터미널을 새로 열고 `aws --version` 재확인.
### Windows의 WSL Ubuntu에서 설치·업데이트
Windows용 MSI 설치와 PowerShell 프로필은 이번 실습에서 사용하지 않음. **WSL Ubuntu 터미널**에서 Linux용 CLI를 설치.
먼저 CPU 확인.
```bash
uname -m
```
`x86_64`이면 아래 블록 실행. `aarch64`라면 다운로드 주소의 `x86_64`만 `aarch64`로 변경.
```bash
sudo apt-get update
sudo apt-get install -y curl unzip less
mkdir -p /tmp/aws-local-cli-install
cd /tmp/aws-local-cli-install
curl -fL --connect-timeout 10 --max-time 120 https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o awscliv2.zip
unzip -q -o awscliv2.zip
sudo ./aws/install
aws --version
```
기존 AWS CLI v2를 같은 기본 경로에 설치한 상태라면 설치 명령만 `sudo ./aws/install --update`로 변경.
**확인 결과:** WSL 안에서 `aws-cli/2...` 버전이 출력됨. 이후에도 같은 WSL Ubuntu에서 로그인·ECR·S3 업로드 실행.
### 같은 터미널에서 로그인
내 PC에 `skn33`이라는 이름의 AWS 설정을 만들고 서울 리전을 지정. 프로필 이름은 로컬 설정을 구분하는 이름이며 IAM 사용자 이름과 다름.
```bash
aws configure set region ap-northeast-2 --profile skn33
aws login --profile skn33
```
1. 열린 브라우저에서 **학원 AWS 계정과 본인 IAM 사용자**로 로그인.
2. 터미널과 브라우저의 안내에 따라 로그인 승인 완료.
WSL에서 브라우저가 열리지 않거나 로그인 후 터미널로 돌아오지 못하면 **Ctrl + C**로 현재 로그인을 끝내고 아래 명령 실행.
```bash
aws login --remote --profile skn33
```
터미널에 표시된 URL을 내 PC 브라우저에 붙여넣어 로그인. 브라우저가 표시한 승인 코드를 WSL 터미널의 요청란에 입력. 이 명령도 내 PC의 WSL에서 실행하며 EC2에서 실행하지 않음.
로그인 후 같은 터미널에서 계정 확인.
```bash
aws sts get-caller-identity --profile skn33
```
**확인 결과:** `Account`가 학원 계정 ID이고 `Arn`이 본인 인증 주체를 나타냄. 다른 계정이면 업로드를 진행하지 말고 로그인한 계정·프로필 확인. `aws login` 명령이 없으면 CLI 버전부터 확인.
로그인은 임시 자격 증명을 사용함. 세션 만료 후 같은 환경에서 다시 로그인. 기관에서 승인한 다른 프로필을 사용한다면 이후 명령의 `--profile skn33`을 그 이름으로 변경. 인증 정보는 EC2나 GitHub에 복사하지 않음. [AWS 로그인 및 --remote 안내](https://docs.aws.amazon.com/cli/latest/reference/login/)
## 4. EC2 역할 준비와 앱 권한 연결
역할은 **EC2 생성 전에 IAM에서 먼저 준비**할 수 있음. 실습 파일과 계정 권한 준비 가이드에서 `skn33-day3-ec2-role-ALIAS`를 이미 생성했다면 아래 역할 생성은 생략하고 앱 권한 연결로 이동. 관리자가 준비한 EC2 역할이 있는 경우에도 중복 생성하지 않음.
### EC2 생성 전에 역할 준비
1. AWS 콘솔 **IAM → 역할 → 역할 생성** 열기.
2. **신뢰할 수 있는 엔터티 유형 → AWS 서비스**, **서비스 또는 사용 사례 → EC2** 선택 → **다음**.
3. 권한 정책에서 `AmazonSSMManagedInstanceCore` 검색·선택 → **다음**.
4. 역할 이름 `skn33-day3-ec2-role-ALIAS` 입력 → **역할 생성**.
5. 역할 이름을 기록. 새 EC2 생성 가이드의 **고급 세부 정보 → IAM 인스턴스 프로파일**에서 이 역할을 선택.
**확인 결과:** 역할의 신뢰 관계는 EC2 서비스이며 SSM 정책이 연결되어 있음. 이 시점에는 ECR·S3 리소스가 아직 없어도 됨.
이미 새 EC2를 생성한 경우에는 **EC2 → 인스턴스 → 새 인스턴스 → 작업 → 보안 → IAM 역할 수정**에서 준비한 역할 연결. 기존 EC2의 역할이 새 인스턴스에 자동 연결되는 것은 아님.
> 역할 생성·전달 권한이 없으면 관리자에게 위 역할 준비와 EC2 연결을 요청. 역할을 여러 학생이 공유하면 권한도 함께 공유되므로 개인별 분리가 필요하면 개인별 역할을 사용.
### ECR·기존 대화 버킷 이름 확정 후 권한 연결
위 역할 생성까지 진행한 뒤 EC2·RDS·S3 준비로 이동할 수 있음. 백엔드 ECR 저장소와 대화 저장 버킷 이름이 확정되면 **이미지 다운로드 전에** 아래 정책 연결.
1. 내 PC 편집기에서 `chatbot_aws/infra/ec2-app-policy.json` 열기.
2. `ACCOUNT_ID`는 계정 ID, `BACKEND_REPOSITORY`는 `skn33-chatbot-backend-ALIAS` 전체 이름, `EXPORT_BUCKET`은 **기존 대화 TXT용 S3 버킷 이름**으로 바꾼 JSON 사본 준비.
3. **IAM → 역할 → 준비한 EC2 역할 → 권한 → 권한 추가 → 인라인 정책 생성 → JSON**에 붙여넣기.
4. **다음** → 정책 이름 `Day3Ec2App` 입력 → **정책 생성**.
5. 앞에서 연결한 `AmazonSSMManagedInstanceCore`가 함께 있는지 확인. 기존 역할에 없다면 **권한 추가 → 정책 연결**에서 추가.
**확인 결과:** EC2 역할에 백엔드 ECR 다운로드, 기존 버킷의 `day2/chat-exports/*` 읽기·쓰기, SSM Agent 연결 권한이 있음. ECR 업로드나 프론트 S3 배포 권한은 주지 않음.
기존 S3 정책을 무조건 삭제하지 않음. 다른 정책이 더 넓은 권한을 허용한다면 위 정책을 추가하는 것만으로 기존 권한이 줄어들지 않으므로 관리자와 확인.
## 5. EC2 AWS CLI 확인 — 설치하지 않은 경우만
새 EC2 준비 가이드에서 이미 설치했다면 이 절은 생략하고 6번의 역할 확인만 진행.
이후 명령은 **SSH로 접속한 EC2 터미널**에서 실행. AWS CLI는 터미널에서 AWS API를 호출하는 도구임.
```bash
uname -m
aws --version
```
`aws-cli/2...`가 나오면 설치 단계는 건너뛰고 다음 단계로 이동. `command not found`이면 아래 설치 진행.
`uname -m`은 EC2 CPU 종류를 확인하는 명령임.
수업의 t3 계열은 `x86_64`가 나옴. 아래 명령은 `x86_64`용임.
```bash
sudo apt-get update
sudo apt-get install -y curl unzip less
mkdir -p /tmp/aws-day3-cli-install
cd /tmp/aws-day3-cli-install
curl -fSL https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o awscliv2.zip
unzip -q -o awscliv2.zip
sudo ./aws/install
aws --version
```
`aarch64`라면 다운로드 주소의 `x86_64`를 `aarch64`로 바꿔 설치. 기존 v2 설치를 업데이트하는 경우에는 `sudo ./aws/install --update` 사용.
**확인 결과:** `aws-cli/2...` 버전이 출력됨. 설치 위치는 `/usr/local/bin/aws`임.
## 6. EC2 역할 사용 확인
```bash
aws sts get-caller-identity --region ap-northeast-2
```
**확인 결과:** `Arn`에 `assumed-role/EC2에_연결한_역할/...`이 보임. EC2에서는 인스턴스 역할을 사용하므로 로컬의 `aws login --profile skn33`을 실행하거나 IAM 사용자 액세스 키를 입력하지 않음.
`Unable to locate credentials`이면 EC2에 역할이 연결되어 있는지 확인. 역할 변경 직후에는 반영까지 잠시 걸릴 수 있음. 다른 IAM 사용자 ARN이 나오면 이전에 설정한 CLI 자격 증명이 역할보다 먼저 선택되는지 관리자와 확인.
이제 다음 가이드에서 새 프로젝트의 백엔드 이미지를 내 PC에서 빌드·업로드하고, EC2에서 내려받아 실행. 로컬 Docker 로그인과 EC2 Docker 로그인은 별개임. EC2의 ECR 로그인은 다음 가이드의 배포 스크립트가 인스턴스 역할로 수행함. CloudFront 설정 권한은 콘솔 사용자에게 필요한 권한이며, 앱 이미지만 실행하는 EC2 역할에는 추가하지 않음.
**공식 문서:** [AWS CLI 브라우저 로그인](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html), [ECR 이미지 업로드 권한](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-push-iam.html), [AWS CLI 설치](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
---
**실습 이동**
- 전체 순서: [노션 페이지](https://app.notion.com/p/3decd3dc5e948199bc9bdae31c5399b3)
- 이전: [노션 페이지](https://app.notion.com/p/3dfcd3dc5e94816eb5a5db3854249865)
- 다음: [노션 페이지](https://app.notion.com/p/3decd3dc5e948126bae5c1e6abc494ee)
