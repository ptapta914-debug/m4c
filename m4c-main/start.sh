#!/bin/sh
set -eu

# Prefer a secret configured by the hosting provider. If none is provided,
# generate one once and reuse the local file across restarts on the same disk.
if [ -z "${DJANGO_SECRET_KEY:-}" ]; then
    SECRET_FILE="${DJANGO_SECRET_KEY_FILE:-.django_secret_key}"
    if [ ! -s "$SECRET_FILE" ]; then
        umask 077
        python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" > "$SECRET_FILE"
    fi
    DJANGO_SECRET_KEY="$(cat "$SECRET_FILE")"
    export DJANGO_SECRET_KEY
fi

export DJANGO_DEBUG="${DJANGO_DEBUG:-false}"

python manage.py migrate --noinput
exec python run_tornado.py
