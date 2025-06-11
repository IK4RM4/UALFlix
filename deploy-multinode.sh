#!/bin/bash
# Deploy para cluster multi-nó

echo "� Deploy UALFlix em cluster multi-nó"

# Verificar se registry está ativo
if ! curl -s localhost:5000/v2/_catalog > /dev/null; then
    echo "❌ Registry não está ativo. Execute make setup-registry primeiro"
    exit 1
fi

# Deploy em ordem
echo "� Deploying namespace..."
kubectl apply -f k8s/namespace.yaml

echo "� Deploying secrets..."
kubectl apply -f k8s/secrets.yaml

echo "�️ Deploying MongoDB..."
kubectl apply -f k8s/database/
kubectl wait --for=condition=ready pod -l app=mongodb -n ualflix --timeout=300s || true

echo "� Deploying RabbitMQ..."
kubectl apply -f k8s/messaging/
kubectl wait --for=condition=ready pod -l app=rabbitmq -n ualflix --timeout=300s || true

echo "� Deploying services com registry local..."
# Usar manifests modificados
for service in authentication_service catalog_service streaming_service admin_service video_processor; do
    if [ -f "k8s-multinode/${service}-deployment.yaml" ]; then
        kubectl apply -f "k8s-multinode/${service}-deployment.yaml"
        kubectl apply -f "k8s/services/${service}/service.yaml"
    else
        kubectl apply -f "k8s/services/${service}/"
    fi
done

echo "⚛️ Deploying frontend..."
if [ -f "k8s-multinode/frontend-deployment.yaml" ]; then
    kubectl apply -f "k8s-multinode/frontend-deployment.yaml"
    kubectl apply -f "k8s/frontend/service.yaml"
else
    kubectl apply -f "k8s/frontend/"
fi

echo "� Deploying NGINX Gateway..."
kubectl apply -f k8s/ingress/

echo "� Deploying monitoring..."
kubectl apply -f k8s/monitoring/ || true

echo "✅ Deploy concluído!"
