FROM python:3.10

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Instala netcat-openbsd para o wait-for-it funcionar
RUN apt-get update && apt-get install -y netcat-openbsd curl && rm -rf /var/lib/apt/lists/*

COPY . .

# Tornar o script executável
RUN chmod +x wait-for-it.sh

# Expor porta
EXPOSE 8000

# CORRIGIDO: usar o nome correto do container da base de dados
CMD ["./wait-for-it.sh", "ualflix_db_master", "5432", "--", "python", "app.py"]