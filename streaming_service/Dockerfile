FROM python:3.10

WORKDIR /app

COPY requirements.mongodb.txt .
RUN pip install -r requirements.mongodb.txt

RUN apt-get update && apt-get install -y \
    ffmpeg \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# Expor porta para API e Prometheus metrics
EXPOSE 8001
EXPOSE 9101

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["python", "app.py"]
