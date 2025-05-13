FROM python:3.10

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libavcodec-extra \
    libavformat-dev \
    libavutil-dev \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Expor porta para métricas do Prometheus
EXPOSE 9102

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9102/health || exit 1

# Usa wait-for-it para garantir que o RabbitMQ esteja pronto
CMD ["./wait-for-it.sh", "queue_service", "5672", "--", "python", "processor.py"]