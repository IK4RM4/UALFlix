FROM python:3.10

WORKDIR /app

COPY requirements.mongodb.txt requirements.mongodb.txt
RUN pip install -r requirements.mongodb.txt

# Instala netcat-openbsd para health checks
RUN apt-get update && apt-get install -y netcat-openbsd curl && rm -rf /var/lib/apt/lists/*

COPY . .
COPY db_mongodb.py .

# Expor porta
EXPOSE 8002

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

CMD ["python", "app.py"]