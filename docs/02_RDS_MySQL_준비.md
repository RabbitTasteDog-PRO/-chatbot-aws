# RDS MySQL 생성과 앱 계정 준비

## 1. RDS 보안 그룹 생성

콘솔 **EC2 → 네트워크 및 보안 → 보안 그룹 → 보안 그룹 생성**을 열기.

| 항목 | 입력값 |
| --- | --- |
| 보안 그룹 이름 | `skn33-day3-rds-ALIAS` |
| 설명 | `MySQL from day3 EC2` |
| VPC | 새 EC2와 같은 VPC |
| 인바운드 유형 | MySQL/Aurora · TCP 3306 |
| 소스 유형 | 사용자 지정 |
| 소스 값 | **새 EC2에 실제 연결한 보안 그룹 ID** 검색·선택 |
| 아웃바운드 | 기본 규칙 유지 |

**보안 그룹 생성** 클릭. 소스에 내 IP·EC2 공인 IP·`0.0.0.0/0`을 넣지 않음. 제한형 EC2 아웃바운드를 사용하는 경우에만 **새 EC2 보안 그룹 → 아웃바운드 규칙 편집**에서 MySQL/Aurora 3306의 대상을 방금 만든 RDS 보안 그룹 ID로 추가.

**확인 결과:** EC2→RDS 방향이 양쪽에서 허용됨. EC2 인바운드나 RDS 아웃바운드에 같은 규칙을 뒤집어 추가하지 않음.

## 2. DB 서브넷 그룹 생성

1. **RDS → 서브넷 그룹 → DB 서브넷 그룹 생성** 열기.
2. 이름 `skn33-day3-subnets-ALIAS`, 설명 `Subnets for day3 RDS` 입력.
3. VPC는 새 EC2와 같은 VPC 선택.
4. **서브넷 추가 → 가용 영역**에서 서로 다른 두 곳 선택.
5. 아래 **서브넷**에서 각 가용 영역의 기존 서브넷을 하나씩 선택.
6. 목록에 서로 다른 가용 영역의 서브넷 두 개가 있는지 확인하고 **생성** 클릭.

기본 VPC의 기존 서브넷을 활용. 서브넷 그룹은 RDS를 배치할 수 있는 위치의 목록임. **서브넷을 두 개 선택하는 것만으로 DB 두 대가 생성되거나 Multi-AZ 요금이 생기는 것은 아님.** 아래 생성 화면에서 Single-AZ를 별도로 선택. [AWS DB 서브넷 그룹](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_VPC.WorkingWithRDSInstanceinaVPC.html)

## 3. 데이터베이스 생성

**RDS → 데이터베이스 → 데이터베이스 생성**을 열고 화면 위에서 아래로 입력. 콘솔에 `Aurora and RDS`로 표시될 수도 있음.

| 화면 구역 | 항목 | 선택·입력값 |
| --- | --- | --- |
| 생성 방식 | 데이터베이스 생성 방식 | **전체 구성**. 예전 콘솔의 `표준 생성`에 해당 |
| 엔진 옵션 | 엔진 유형 | **MySQL**. Aurora MySQL을 선택하지 않음 |
| 엔진 옵션 | 엔진 버전 | MySQL **8.4**의 제공되는 마이너 버전 |
| 템플릿 | 사용 목적 | 개발/테스트. 없는 경우 아래 항목을 직접 맞춤 |
| 가용성 및 내구성 | 배포 옵션 | **단일 DB 인스턴스 / Single-AZ** |
| 설정 | DB 인스턴스 식별자 | `skn33-day3-mysql-ALIAS` |
| 설정 | 마스터 사용자 이름 | `labadmin` |
| 자격 증명 관리 | 관리 방식 | **자체 관리**. 마스터 비밀번호 직접 설정·별도 보관 |
| 인스턴스 구성 | 클래스 | 버스터블 클래스 → `db.t4g.micro` |
| 스토리지 | 유형 / 할당 | 범용 SSD `gp3` / 20 GiB |
| 스토리지 | 자동 조정 | 이번 짧은 실습에서는 해제 |
| 연결 | EC2 컴퓨팅 리소스 | **연결하지 않음**. 아래 VPC·보안 그룹을 직접 지정 |
| 연결 | 네트워크 유형 | IPv4 |
| 연결 | VPC | 새 EC2와 같은 VPC |
| 연결 | DB 서브넷 그룹 | 방금 만든 `skn33-day3-subnets-ALIAS` |
| 연결 | 퍼블릭 액세스 | **아니요** |
| 연결 | VPC 보안 그룹 | **기존 항목 선택** → 방금 만든 RDS 그룹만 선택 |
| 연결 | 가용 영역 선택이 가능한 경우 | 새 EC2와 같은 가용 영역 선택 |
| 연결 → 추가 구성 | 데이터베이스 포트 | 3306 |
| 데이터베이스 인증 | 인증 옵션 | **암호 인증** |
| 모니터링 | Database Insights | **표준** |
| 모니터링 → 추가 모니터링 설정 | Enhanced monitoring 활성화 | **체크 해제** |
| 모니터링 → 로그 내보내기 | 로그 유형 | 이번 실습에서는 모두 미선택 |
| 추가 구성 → 데이터베이스 옵션 | 초기 데이터베이스 이름 | `chatbot` |
| 추가 구성 → 백업 | 자동 백업 보존 기간 | 실습 기준 1일. 추가 보존이 필요하면 별도 결정 |
| 추가 구성 → 유지 관리 | 마이너 버전 자동 업그레이드 | 기본값 유지 |
| 추가 구성 → 삭제 방지 | 삭제 방지 활성화 | 실습 종료 후 삭제 예정이면 해제 |

**인증 구역**은 로그인 방법을, **추가 구성**은 초기 DB 이름·백업·유지 관리를 정하는 곳임. `labadmin`은 수업에서 정한 관리 계정 이름이며 AWS가 강제하는 이름이 아님.

월별 추정 요금을 확인하고 **데이터베이스 생성** 클릭. IAM 사용자라고 무료 요금제가 적용되는 것은 아님. 비용은 학원 AWS 계정에 청구되며, 표시 금액에는 일부 백업·전송·모니터링 등이 포함되지 않을 수 있음.

**확인 결과:** DB 상태가 `사용 가능`이 된 뒤 **연결 및 보안 → 엔드포인트** 복사. 주소에 `https://`나 `:3306`을 붙이지 않음. 삭제했던 DB를 새로 만든 경우 기존 회원·대화 데이터는 없음.

## 4. 접속용 인증서 준비

**새 EC2 터미널**에서 작업 폴더와 RDS 공개 CA 파일 준비.

```bash
mkdir -p /home/ubuntu/chatbot-aws/certs
cd /home/ubuntu/chatbot-aws
curl -fsSL --connect-timeout 10 --max-time 60 https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem -o certs/global-bundle.pem
ls -lh certs/global-bundle.pem
```

**확인 결과:** 파일 크기가 0이 아닌 `global-bundle.pem` 표시. `curl (28)`이면 새 EC2의 HTTPS 443 아웃바운드와 인터넷 경로를 확인. RDS 3306 인바운드를 바꾸는 문제와 구분.

## 5. 마스터 계정으로 접속

같은 EC2 폴더에서 아래 **블록 전체** 실행. `RDS_ENDPOINT`만 앞에서 복사한 실제 주소로 변경.

```bash
sudo docker run --rm -it \
  -v "$PWD/certs:/certs:ro" \
  mysql:8.4 mysql \
  --host=RDS_ENDPOINT \
  --port=3306 --user=labadmin --password \
  --ssl-ca=/certs/global-bundle.pem \
  --ssl-mode=VERIFY_IDENTITY
```

`Enter password:`가 나오면 **RDS 생성 시 정한 마스터 비밀번호** 입력. 입력 문자가 화면에 표시되지 않는 것이 정상임. `mysql>` 프롬프트가 나타나야 함.

| 오류 | 확인할 부분 |
| --- | --- |
| `ERROR 2003 ... (110)` | RDS 사용 가능 상태·주소, EC2→RDS 보안 그룹 양방향 설정·같은 VPC |
| `Access denied` | `labadmin` 이름·마스터 비밀번호 |
| 인증서 오류 | 파일 경로·CA 파일·RDS 엔드포인트. IP로 바꾸거나 TLS 검증을 끄지 않음 |
| 이미지 다운로드 실패 | EC2 HTTPS 아웃바운드·Docker Hub 접근 |

## 6. 앱 전용 계정 생성

아래는 **`mysql>` 안에서 실행하는 SQL**. `APP_DATABASE_PASSWORD`를 앱 전용 비밀번호로 변경. `.env`에 안전하게 입력할 수 있는 충분히 긴 영문·숫자 비밀번호를 새로 생성해 사용. 마스터 비밀번호와 구분.

```sql
CREATE DATABASE IF NOT EXISTS chatbot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'chatbot'@'%' IDENTIFIED BY 'APP_DATABASE_PASSWORD' REQUIRE SSL;
GRANT ALL PRIVILEGES ON chatbot.* TO 'chatbot'@'%';
SHOW GRANTS FOR 'chatbot'@'%';
EXIT;
```

Django 마이그레이션이 테이블을 만들고 변경하므로 **`chatbot` DB 범위 안에서** DDL·데이터 작업 권한 부여. 다른 DB나 서버 전체 관리 권한은 주지 않음. 사용자가 이미 있으면 `CREATE USER`를 반복하지 말고 기존 계정 설정 확인.

**확인 결과:** `SHOW GRANTS`에 `chatbot.*` 권한과 `REQUIRE SSL` 표시. 앱의 `DB_USER`는 `labadmin`이 아니라 `chatbot`, `DB_PASSWORD`는 방금 만든 앱 비밀번호 사용.
