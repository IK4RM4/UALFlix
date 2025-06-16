#!/bin/sh

# Baixar imagens oficiais

echo "Baixando imagens oficiais..."
docker pull mongo:6.0
docker pull rabbitmq:3-management

echo "Construindo imagens customizadas..."
docker build -t ualflix/nginx:latest ./nginx
docker build -t ualflix/authentication_service:latest ./authentication_service
docker build -t ualflix/catalog_service:latest ./catalog_service
docker build -t ualflix/streaming_service:latest ./streaming_service
docker build -t ualflix/video_processor:latest ./video_processor
docker build -t ualflix/frontend:latest ./frontend
docker build -t ualflix/admin_service:latest ./admin_service

echo "Todas as imagens foram construídas com sucesso!" 