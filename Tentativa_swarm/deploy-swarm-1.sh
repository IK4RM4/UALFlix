#!/bin/bash

# Verificar imagens oficiais
echo "Verificando imagens oficiais..."
docker pull mongo:6.0
docker pull rabbitmq:3-management

# Construir imagens para cada serviço
echo "Construindo imagens dos serviços..."
docker build -t ualflix/nginx:latest ./nginx
docker build -t ualflix/authentication_service:latest ./authentication_service
docker build -t ualflix/catalog_service:latest ./catalog_service
docker build -t ualflix/streaming_service:latest ./streaming_service
docker build -t ualflix/video_processor:latest ./video_processor
docker build -t ualflix/frontend:latest ./frontend
docker build -t ualflix/admin_service:latest ./admin_service

echo "Todas as imagens foram construídas/verificadas com sucesso!" 

# Verifica se o Docker Swarm está inicializado
if ! docker info | grep -q "Swarm: active"; then
    echo "Docker Swarm não está inicializado. Executando init-swarm.sh..."
    ./init-swarm.sh
fi

# Implanta a stack
docker stack deploy -c docker-compose.swarm.yml ualflix

echo "Stack ualflix implantada com sucesso!"
echo "Para verificar o status dos serviços, execute: docker service ls" 