# GitHub OIDC·SSM 자동 배포 권한 연결

## 1. 자동 배포에서 사용하는 두 역할
**OIDC:** GitHub Actions가 AWS에 자신을 증명하고 임시 자격 증명을 받는 방식임. AWS 액세스 키를 GitHub에 저장하지 않음.
**SSM Run Command:** EC2의 SSM Agent에 명령을 전달하는 기능임. 자동 배포용 SSH 키 없이 EC2에서 배포 스크립트를 실행할 수 있음.
| 역할 | 누가 사용 | 필요한 권한 |
| --- | --- | --- |
| 새 EC2에 연결한 역할 | EC2의 프로그램·SSM Agent | 기존 S3 접근, ECR 이미지 다운로드, SSM 연결 |
| 새 GitHub 배포 역할 | 지정한 저장소의 main 워크플로 | 백엔드 ECR 업로드, 프론트 S3 업로드, CloudFront 캐시 무효화, 지정 EC2 명령 실행·결과 조회 |
> IAM 역할·OIDC 공급자 변경 권한이 없는 학원 계정은 관리자가 먼저 구성해야 함. 이 경우 역할 ARN과 설정 완료 결과를 전달받아 확인 단계부터 진행.
## 2. EC2 역할의 SSM 권한 확인
앞의 ECR 권한 가이드에서 SSM 정책을 연결한 상태임.
1. AWS 콘솔 **IAM → 역할 → 새 EC2에 연결한 역할 → 권한** 열기.
2. `AmazonSSMManagedInstanceCore`와 `Day3Ec2App`이 보이면 다음 단계로 진행.
3. SSM 정책이 빠진 경우에만 **권한 추가 → 정책 연결**에서 `AmazonSSMManagedInstanceCore` 검색 → 체크 → **권한 추가** 선택.
EC2 역할의 신뢰 주체는 EC2를 유지. GitHub 신뢰 정책은 뒤에서 만드는 별도 역할에 적용. GitHub 역할에는 프론트 배포용 S3와 지정 CloudFront의 캐시 무효화 권한도 부여. CloudFront·ACM·ALB 리소스 생성 권한은 두 역할에 추가하지 않음.
## 3. SSM Agent 오류가 있을 때만 확인
새 EC2 준비 가이드에서 SSM Agent를 확인했다면 이 절은 건너뛰고 4번으로 이동. 관리 노드가 Online이 아니거나 Agent 오류가 있을 때만 **EC2 터미널**에서 아래 명령 실행.
```bash
sudo snap list amazon-ssm-agent
sudo snap services amazon-ssm-agent
```
Ubuntu 24.04의 AWS 제공 AMI에는 보통 Agent가 설치되어 있음. `Current`가 `active`이면 설치하지 않음.
패키지가 없다는 메시지가 나올 때만 다른 설치 방식이 있는지 확인.
```bash
systemctl status amazon-ssm-agent --no-pager
```
기존 서비스가 있으면 snap을 중복 설치하지 않고 기존 서비스 상태를 관리자와 확인. **snap 패키지와 기존 서비스가 모두 없을 때만** 설치.
```bash
sudo snap install amazon-ssm-agent --classic
```
snap Agent가 설치된 인스턴스에서 시작·확인.
```bash
sudo snap start --enable amazon-ssm-agent
sudo snap services amazon-ssm-agent
```
역할 권한 추가 전에 Agent가 실행 중이었다면 다시 시작.
```bash
sudo snap restart amazon-ssm-agent
```
**확인 결과:** `Startup`이 `enabled`, `Current`가 `active`임.
## 4. 관리 노드에서 명령 실행 확인
1. AWS 콘솔의 리전을 **서울**로 선택.
2. **Systems Manager → Fleet Manager**의 관리 노드 목록 열기.
3. 본인 인스턴스 ID와 연결 상태 **Online** 확인. 등록까지 몇 분 걸릴 수 있음.
4. **Systems Manager → Run Command → 명령 실행** 선택.
5. 명령 문서에서 `AWS-RunShellScript` 검색 → 선택.
6. **대상 → 인스턴스를 수동으로 선택**에서 본인 인스턴스만 체크.
7. **명령 파라미터 → Commands**에 아래 두 줄 입력.
```bash
whoami
test -d /home/ubuntu/chatbot-aws && echo APP_DIRECTORY_OK
```
1. 이 실습에서는 S3·CloudWatch로 명령 출력을 별도 저장하는 옵션을 선택하지 않고 **실행**.
2. 명령 ID → 대상 인스턴스 → 출력 열기.
**확인 결과:** 명령 상태 `Success`, 출력에 `root`와 `APP_DIRECTORY_OK`가 보임. SSM 명령은 기본적으로 root로 실행되므로 배포 스크립트에서도 사용자·작업 폴더를 명시해야 함.
> **관리 노드가 안 보이면:** EC2 역할, Agent 상태, 서울 리전, EC2의 인터넷 경로를 확인. Agent가 AWS SSM 서비스로 나가는 HTTPS 443 통신과 DNS가 가능해야 함. 기존 퍼블릭 서브넷·탄력적 IP를 유지하며 보안 그룹 아웃바운드를 임의로 차단하지 않음. SSM용 인바운드 443 규칙을 추가하는 것으로 해결되지 않음.
> **명령 실행 AccessDenied:** 콘솔을 사용하는 IAM 사용자의 Run Command 권한 문제일 수 있음. EC2의 `AmazonSSMManagedInstanceCore`는 명령을 받는 Agent의 권한이며, 사용자의 명령 전송 권한과 다름.
## 5. GitHub main의 OIDC 주체 확인
신뢰 정책은 **정확한 저장소의 main**만 허용하도록 작성. 저장소 생성 시점·설정에 따라 주체 문자열에 숫자 ID가 포함될 수 있으므로 이름만 보고 예상해서 입력하지 않음.
**내 PC 브라우저 → 배포할 GitHub 저장소**에서 진행. 이 수업은 GitHub Environment를 사용하지 않음.
1. `main` 브랜치에서 새 프로젝트의 `.github/workflows/oidc-claims.yml`이 있는지 확인.
2. 이 파일은 아래 내용으로 제공됨. 이미 있으면 동일한 워크플로를 중복 생성하지 않음. 없다면 **Add file → Create new file**에서 해당 경로로 생성 → **Commit changes**. 보호된 main이면 PR로 병합.
```yaml
name: Inspect OIDC claims
on:
  workflow_dispatch:
permissions:
  contents: read
  id-token: write
jobs:
  inspect:
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-24.04
    steps:
      - name: Print only aud and sub
        shell: python
        run: |
          import base64, json, os
          from urllib.request import Request, urlopen
          base = os.environ['ACTIONS_ID_TOKEN_REQUEST_URL']
          url = base + ('&' if '?' in base else '?') + 'audience=sts.amazonaws.com'
          request = Request(url, headers={'Authorization': 'Bearer ' + os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']})
          with urlopen(request, timeout=20) as response:
              token = json.load(response)['value']
          encoded = token.split('.')[1]
          claims = json.loads(base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)))
          print(json.dumps({key: claims[key] for key in ('aud', 'sub')}, indent=2))
```
1. **Actions → Inspect OIDC claims → Run workflow** 선택.
2. Branch가 `main`인지 확인 → **Run workflow**.
3. 실행 결과 → **inspect → Print only aud and sub**에서 JSON의 `sub` 문자열 값 전체 복사. 따옴표는 제외.
**확인 결과:** `aud`가 `sts.amazonaws.com`, `sub`가 본인 저장소와 `ref:refs/heads/main`을 가리킴. 전체 JWT나 요청 토큰은 출력하지 않음. 이 단계는 신뢰 정책에 사용할 값 확인이며 AWS 로그인 성공 검사가 아님.
## 6. GitHub OIDC 공급자·역할 생성
**AWS 콘솔 → IAM**에서 진행.
1. **자격 증명 공급자 / Identity providers**에서 `token.actions.githubusercontent.com` 확인.
2. 이미 있으면 재생성하지 않음. 없으면 **공급자 추가** 선택.
| 항목 | 입력 |
| --- | --- |
| 공급자 유형 | OpenID Connect |
| 공급자 URL | `https://token.actions.githubusercontent.com` |
| 대상 / Audience | `sts.amazonaws.com` |
1. **역할 → 역할 생성 → 사용자 지정 신뢰 정책** 선택.
2. 아래 JSON에서 `ACCOUNT_ID`를 실제 12자리 값으로, `EXACT_MAIN_SUB`를 앞 단계에서 복사한 값으로 변경해 붙여넣기.
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "EXACT_MAIN_SUB"
        }
      }
    }
  ]
}
```
1. **다음** → 관리형 정책 선택 없이 진행 → 역할 이름 `skn33-github-deploy-ALIAS` 입력 → 생성.
2. 생성한 역할의 **ARN** 복사.
`EXACT_MAIN_SUB`에 `*`를 넣지 않음. 다른 학생의 저장소나 모든 브랜치를 허용하지 않도록 실제 main 값을 그대로 사용.
## 7. GitHub 역할에 배포 권한 추가
내 PC 편집기에서 `chatbot_aws/infra/github-deploy-policy.json` 열기. 다음 자리표시자를 실제 값으로 변경한 JSON 사본 준비.
- `ACCOUNT_ID`: 12자리 AWS 계정 ID.
- `BACKEND_REPOSITORY`: `skn33-chatbot-backend-ALIAS` 전체 저장소 이름.
- `FRONTEND_BUCKET`: React 배포용 S3 버킷 이름. 대화 TXT 버킷이 아님.
- `DISTRIBUTION_ID`: CloudFront의 **배포 → ID**에서 복사한 `E...` 값. 도메인 주소가 아님.
- `INSTANCE_ID`: 새 EC2 콘솔에서 복사한 `i-...` 인스턴스 ID. 탄력적 IP가 아님.
1. 방금 만든 **GitHub 배포 역할 → 권한 → 권한 추가 → 인라인 정책 생성 → JSON** 열기.
2. 준비한 JSON 전체 붙여넣기 → **다음** → 정책 이름 `Day3GithubDeployment` → 생성.
이 정책은 백엔드 ECR 업로드, 프론트 S3 목록·읽기·업로드, 지정 CloudFront 캐시 무효화·완료 조회, 지정 EC2의 SSM 배포 명령 실행·결과 조회를 허용함. 파일 일괄 삭제 권한이나 대화 TXT 버킷 접근 권한은 포함하지 않음.
AWS 소유 명령 문서 ARN의 `ap-northeast-2::document`에는 계정 ID를 넣지 않음. 명령 전송은 본인 EC2 한 대와 지정 문서로 제한. `GetCommandInvocation`은 개별 리소스 ARN 제한을 지원하지 않아 `*` 사용.
**확인 결과:** 신뢰 관계는 정확한 GitHub main, 배포 권한은 본인 백엔드 저장소·프론트 버킷·CloudFront 배포·새 EC2를 가리킴. EC2 역할에 GitHub 신뢰 정책을 덮어쓰지 않음.
## 8. GitHub Actions 변수 등록
GitHub 저장소 **Settings → Secrets and variables → Actions → Variables → New repository variable**에서 아래 값을 하나씩 등록.
| Name | Value |
| --- | --- |
| `AWS_REGION` | `ap-northeast-2` |
| `AWS_ACCOUNT_ID` | 12자리 AWS 계정 ID |
| `ECR_BACKEND_REPOSITORY` | `skn33-chatbot-backend-ALIAS` |
| `EC2_INSTANCE_ID` | 본인 인스턴스 ID `i-...` |
| `ORIGIN_HOST` | 처음에는 EC2 퍼블릭 DNS, ALB 전환 후 `origin.example.com`. 프로토콜·경로·포트를 붙이지 않음 |
| `FRONTEND_BUCKET` | React 배포용 S3 버킷 이름 |
| `CLOUDFRONT_DISTRIBUTION_ID` | CloudFront 배포 ID `E...` |
| `APP_URL` | 접속 확인한 `https://xxxxx.cloudfront.net` — 본인 배포 주소 사용, 마지막 `/` 제외. EC2 IP·원본 DNS를 입력하지 않음. 사용자 도메인 연결 후 CloudFront에 연결한 서비스 HTTPS 주소 사용 |
위 8개 변수를 먼저 등록한 뒤 **마지막으로** `AWS_DEPLOY_ROLE_ARN`을 생성하고 앞에서 복사한 GitHub 배포 역할 ARN 입력. 이 값이 없으면 AWS 배포 작업을 건너뛰며 CI 테스트만 실행됨. 역할 ARN 등록 후 다음 가이드의 수동 실행 또는 이후 main push에서 자동 배포가 시작됨.
저장소 이름에는 전체 ECR URI를 넣지 않음. 위 값은 비밀키가 아닌 배포 대상 정보이므로 Variables에 등록. 실제 앱 `.env`는 새 EC2의 `/home/ubuntu/chatbot-aws/.env`에 유지. 총 9개 변수이며 프론트 ECR 저장소 변수는 사용하지 않음.
다음 자동 배포 가이드에서 OIDC 로그인·백엔드 ECR 업로드·SSM 명령·프론트 S3 업로드·CloudFront 캐시 갱신 완료까지 확인. 변수 등록만으로 EC2 배포가 시작되지는 않음.
**공식 문서:** [GitHub AWS OIDC](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws), [EC2 SSM 권한](https://docs.aws.amazon.com/systems-manager/latest/userguide/setup-instance-permissions.html), [Ubuntu SSM Agent](https://docs.aws.amazon.com/systems-manager/latest/userguide/agent-install-ubuntu-64-snap.html), [SSM Agent 통신](https://docs.aws.amazon.com/systems-manager/latest/userguide/ssm-agent-technical-details.html)
---
**실습 이동**
- 전체 순서: [노션 페이지](https://app.notion.com/p/3decd3dc5e948199bc9bdae31c5399b3)
- 이전: [노션 페이지](https://app.notion.com/p/3decd3dc5e948100bfdfdc811710c487)
- 다음: [노션 페이지](https://app.notion.com/p/3decd3dc5e9481fe8eaffc9579c8ac60)
