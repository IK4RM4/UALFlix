FROM python:3.10

WORKDIR /app

COPY requirements.mongodb.txt requirements.mongodb.txt
RUN pip install -r requirements.mongodb.txt

# Install necessary utilities including dos2unix
RUN apt-get update && apt-get install -y netcat-openbsd curl dos2unix && rm -rf /var/lib/apt/lists/*

COPY . .
COPY db_mongodb.py .

# Convert the file's line endings to Unix format
RUN dos2unix ./wait-for-it.sh

# Ensure the script is executable
RUN chmod +x ./wait-for-it.sh

# Expose port
EXPOSE 8000

CMD ["python", "processor.py"]