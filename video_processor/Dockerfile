FROM python:3.10

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Install necessary utilities including dos2unix
RUN apt-get update && apt-get install -y netcat-openbsd curl dos2unix && rm -rf /var/lib/apt/lists/*

COPY . .

# Convert the file's line endings to Unix format (dos2unix is now installed)
RUN dos2unix ./wait-for-it.sh

# Ensure the script is executable
RUN chmod +x ./wait-for-it.sh

# Expose port
EXPOSE 8000

# CORRIGIDO: usar o nome correto do container da base de dados
CMD ["./wait-for-it.sh", "ualflix_db_master", "5432", "--", "python", "processor.py"]