#!/usr/bin/env bash
set -e

mkdir -p "${DJANGO_MEDIA_ROOT:-/tmp/smart-crop-ai-media}"

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn smart_crop_ai.wsgi:application \
  --bind "0.0.0.0:${PORT:-7860}" \
  --workers 1 \
  --timeout 300
