#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 3 ]]; then
  echo '사용법: frontend.sh FRONTEND_BUCKET CLOUDFRONT_DISTRIBUTION_ID DIST_DIRECTORY' >&2
  exit 2
fi
bucket=$1 distribution=$2 dist=$3
[[ $bucket =~ ^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$ ]] || exit 2
[[ $distribution =~ ^[A-Z0-9]+$ ]] || exit 2
test -s "$dist/index.html"
test -d "$dist/assets"
# 해시 파일은 먼저 업로드한다. 기존 해시 파일은 열린 브라우저와 롤백을 위해 유지한다.
aws s3 sync "$dist/assets/" "s3://$bucket/assets/" --cache-control 'public,max-age=31536000,immutable' --only-show-errors
aws s3 sync "$dist/" "s3://$bucket/" --exclude 'assets/*' --exclude 'index.html' --cache-control 'no-cache' --only-show-errors
# index는 매번 덮어쓴다. --delete는 사용하지 않는다.
aws s3 cp "$dist/index.html" "s3://$bucket/index.html" --content-type 'text/html; charset=utf-8' --cache-control 'no-cache,no-store,must-revalidate' --only-show-errors
invalidation=$(aws cloudfront create-invalidation --distribution-id "$distribution" --paths '/*' --query 'Invalidation.Id' --output text)
aws cloudfront wait invalidation-completed --distribution-id "$distribution" --id "$invalidation"
echo '프론트 업로드 및 CloudFront 캐시 갱신 완료'
