# Base da imagem
FROM python:3.11-slim

# Diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    netcat-openbsd \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Copiar ficheiros para dentro do container
COPY . .

# Permitir execução do wait-for-it.sh
RUN chmod +x wait-for-it.sh

# Instalar dependências Python
RUN pip install --upgrade pip && pip install -r requirements.mongodb.txt

# Expõe a porta da API Flask
EXPOSE 8000

# Comando default (vai ser substituído pelo entrypoint do docker-compose)
CMD ["python", "app.py"]
