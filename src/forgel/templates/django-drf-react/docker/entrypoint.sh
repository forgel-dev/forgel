#!/bin/sh
# Container entrypoint: wait for Postgres, apply migrations, create the S3
# bucket when object storage is configured, then serve the API.
set -e

attempts=0
until python manage.py migrate --noinput; do
  attempts=$((attempts + 1))
  if [ "$attempts" -ge 30 ]; then
    echo "database not ready after $attempts attempts" >&2
    exit 1
  fi
  echo "waiting for database (attempt $attempts)..." >&2
  sleep 2
done

python -m config.bucket

exec python manage.py runserver 0.0.0.0:8000
