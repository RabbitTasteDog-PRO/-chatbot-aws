#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

python manage.py check
# 이번 실습은 각 학생의 새 MySQL이다. 기존 공용 DB에는 연결하지 않는다.
# backend 한 개를 실행하는 수업 예제이며, 이미 적용된 migration은 건너뛴다.
python manage.py migrate --noinput

exec python -m gunicorn _chatbot.wsgi:application \
  --bind 0.0.0.0:8000 \
  --worker-class gthread \
  --workers 2 \
  --threads 2 \
  --timeout 90 \
  --access-logfile - \
  --error-logfile -
