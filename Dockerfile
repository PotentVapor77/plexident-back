FROM python:3.11-slim

# Prevenir archivos .pyc y asegurar logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/usr/local/bin:$PATH"

WORKDIR /app

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libffi-dev \
    libjpeg-dev \
    libopenjp2-7-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python directamente aquí
RUN pip install --upgrade pip
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el proyecto
COPY . /app/

# Dar permisos al script de inicio
RUN chmod +x /app/start.sh

EXPOSE 8000

# Usar bash para ejecutar el script que lanzará Gunicorn
CMD ["/bin/bash", "/app/start.sh"]