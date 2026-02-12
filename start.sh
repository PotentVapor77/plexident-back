#!/bin/bash
set -e

echo "==> Aplicando migraciones..."
python3 manage.py migrate --noinput

echo "==> Recolectando estáticos..."
python3 manage.py collectstatic --noinput

echo "==> Iniciando Gunicorn..."
exec python3 -m gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3