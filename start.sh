#!/bin/bash

# Esperar a que la base de datos esté disponible
echo "Esperando a la base de datos en $DB_HOST:$DB_PORT..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.5
done
echo "Base de datos detectada!"

# Aplicar migraciones automáticamente
echo "Aplicando migraciones..."
python manage.py migrate --noinput 

# Recolectar archivos estáticos para Whitenoise
echo "Recolectando archivos estáticos..."
python manage.py collectstatic --noinput 

# Iniciar el servidor con Gunicorn
echo "Iniciando Gunicorn..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 