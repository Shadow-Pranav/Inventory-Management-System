#!/usr/bin/env bash
set -euo pipefail

python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear

if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  python manage.py seed_demo || echo "seed_demo skipped (already seeded)"
fi

if [ "${DJANGO_ENV:-dev}" = "dev" ]; then
  exec python manage.py runserver 0.0.0.0:8000
else
  exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
fi
