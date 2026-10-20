#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Prefer a secret configured by the hosting provider. If none is provided,
# generate one once and reuse the local file across restarts on the same disk.
if [ -z "${DJANGO_SECRET_KEY:-}" ]; then
    SECRET_FILE="${DJANGO_SECRET_KEY_FILE:-$SCRIPT_DIR/.django_secret_key}"
    if [ ! -s "$SECRET_FILE" ]; then
        umask 077
        PYTHON_BIN="${PYTHON_BIN:-python3}"
        if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
            PYTHON_BIN="python"
        fi
        "$PYTHON_BIN" -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" > "$SECRET_FILE"
    fi
    DJANGO_SECRET_KEY="$(cat "$SECRET_FILE")"
    export DJANGO_SECRET_KEY
fi

export DJANGO_DEBUG="${DJANGO_DEBUG:-false}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    PYTHON_BIN="python"
fi

"$PYTHON_BIN" manage.py migrate --noinput
exec "$PYTHON_BIN" run_tornado.py
