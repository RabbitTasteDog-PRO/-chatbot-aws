#!/usr/bin/env bash
set -euo pipefail
# EC2에서 sudo로 실행. 앱 비밀값은 읽어 출력하지 않는다.
if [[ $# -lt 4 || $# -gt 5 ]]; then
  echo '사용법: deploy.sh TAG ECR_REGISTRY BACKEND_REPOSITORY ORIGIN_HOST [https://VIEWER_DOMAIN]' >&2
  exit 2
fi
tag=$1 registry=$2 repository=$3 origin=$4 public_url=${5:-}
[[ $tag =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$ ]] || exit 2
[[ $registry =~ ^[0-9]{12}\.dkr\.ecr\.ap-northeast-2\.amazonaws\.com$ ]] || exit 2
[[ $repository =~ ^[a-z0-9][a-z0-9._/-]+$ ]] || exit 2
[[ $origin =~ ^[a-zA-Z0-9][a-zA-Z0-9.-]+$ ]] || exit 2
[[ -z $public_url || $public_url =~ ^https://[a-zA-Z0-9][a-zA-Z0-9.-]+$ ]] || exit 2
cd /home/ubuntu/chatbot-aws
exec 9>/run/lock/chatbot-aws-deploy.lock
flock -w 120 9
for path in .env certs/global-bundle.pem deploy/nginx.conf compose.prod.yaml; do test -f "$path"; done
candidate=$(mktemp deploy/.release.XXXXXX)
health=$(mktemp)
trap 'rm -f "$candidate" "$health"' EXIT
image="$registry/$repository:$tag"
printf 'BACKEND_IMAGE=%s\n' "$image" > "$candidate"
compose=(docker compose --project-name chatbot-aws --env-file .env --env-file "$candidate" -f compose.prod.yaml)
"${compose[@]}" config --quiet
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin "$registry"
timeout 300 "${compose[@]}" pull backend gateway
"${compose[@]}" up -d --wait --wait-timeout 240 backend gateway
"${compose[@]}" exec -T gateway nginx -t
check_health() {
  curl --silent --show-error --fail --connect-timeout 5 --max-time 15 "$@" > "$health" &&
    python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d.get("status")=="ok" and d.get("database")=="ok" else 1)' "$health"
}
ready=false
for attempt in {1..15}; do
  if check_health -H "Host: $origin" http://127.0.0.1/api/health/; then ready=true; break; fi
  sleep 2
done
[[ $ready == true ]] || { echo 'EC2 API·DB 확인 실패. 성공 버전을 갱신하지 않습니다.' >&2; exit 1; }
if [[ -n $public_url ]]; then
  ready=false
  for attempt in {1..12}; do
    if check_health "$public_url/api/health/"; then ready=true; break; fi
    sleep 5
  done
  [[ $ready == true ]] || { echo '공개 HTTPS API·DB 확인 실패' >&2; exit 1; }
fi
container=$("${compose[@]}" ps -q backend)
[[ $(docker inspect --format '{{.Config.Image}}' "$container") == "$image" ]]
if [[ -f deploy/release.env ]]; then cp deploy/release.env deploy/previous.env; fi
cp "$candidate" deploy/release.env
chmod 644 deploy/release.env
printf '백엔드 배포 성공: %s\n' "$tag"
