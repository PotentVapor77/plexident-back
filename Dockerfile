FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    python3-dev \
    shared-mime-info \
    netcat-traditional \
    pkg-config \
    libcairo2-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt 

COPY . .

RUN chmod +x start.sh \
    && sed -i 's/\r$//' start.sh

EXPOSE 8000

CMD ["./start.sh"]