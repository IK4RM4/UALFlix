#!/bin/bash
# Executar UALFlix no Kubernetes com 3 nós - Setup Completo

echo "🎬 UALFlix - Setup Kubernetes com 3 Nós"
echo "======================================"

# 1. Verificar pré-requisitos
echo "1️⃣ Verificando pré-requisitos..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker não encontrado. Instale: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl não encontrado. Instale: https://kubernetes.io/docs/tasks/tools/"
    exit 1
fi

if ! command -v minikube &> /dev/null; then
    echo "❌ Minikube não encontrado. Instale: https://minikube.sigs.k8s.io/docs/start/"
    exit 1
fi

echo "✅ Todos os pré-requisitos instalados!"

# 2. Iniciar cluster com 3 nós
echo "2️⃣ Iniciando cluster Minikube com 3 nós..."

# Parar qualquer instância existente
minikube delete 2>/dev/null || true

# Iniciar novo cluster
minikube start \
    --driver=docker \
    --nodes=3 

echo "✅ Cluster iniciado com 3 nós!"

# 3. Verificar nós
echo "3️⃣ Verificando nós do cluster..."
kubectl get nodes -o wide

# 4. Habilitar addons
echo "4️⃣ Habilitando addons necessários..."
minikube addons enable ingress
minikube addons enable dashboard
minikube addons enable metrics-server
minikube addons enable default-storageclass
minikube addons enable storage-provisioner

# 5. Configurar Docker environment
echo "5️⃣ Configurando Docker environment..."
eval $(minikube docker-env)

# 6. Build das imagens Docker
echo "6️⃣ Construindo imagens Docker..."
services=("frontend" "authentication_service" "catalog_service" "streaming_service" "admin_service" "video_processor")

for service in "${services[@]}"; do
    echo "Building $service..."
    docker build -t ${service}:latest ./${service}/
done

echo "✅ Todas as imagens construídas!"

# 7. Deploy da aplicação
echo "7️⃣ Fazendo deploy da aplicação UALFlix..."

# Namespace
kubectl apply -f k8s/namespace.yaml

# Secrets e ConfigMaps
kubectl apply -f k8s/secrets.yaml

# MongoDB (Base de dados com replicação)
echo "📊 Deploying MongoDB Replica Set..."
kubectl apply -f k8s/database/
kubectl wait --for=condition=ready pod -l app=mongodb -n ualflix --timeout=300s || true
sleep 10

# RabbitMQ
echo "🐰 Deploying RabbitMQ..."
kubectl apply -f k8s/messaging/
kubectl wait --for=condition=ready pod -l app=rabbitmq -n ualflix --timeout=300s || true
sleep 5

# Serviços da aplicação
echo "🔧 Deploying application services..."
kubectl apply -f k8s/services/auth/
kubectl apply -f k8s/services/catalog/
kubectl apply -f k8s/services/streaming/
kubectl apply -f k8s/services/admin/
kubectl apply -f k8s/services/processor/

sleep 20
kubectl wait --for=condition=available deployment --all -n ualflix --timeout=300s || true

# Frontend
echo "⚛️ Deploying React Frontend..."
kubectl apply -f k8s/frontend/
kubectl wait --for=condition=available deployment/frontend -n ualflix --timeout=300s || true

# NGINX Gateway (Load Balancer Principal)
echo "🌐 Deploying NGINX Gateway..."
kubectl apply -f k8s/ingress/nginx-configmap.yaml
kubectl apply -f k8s/ingress/nginx-deployment.yaml
kubectl apply -f k8s/ingress/nginx-service.yaml
kubectl wait --for=condition=available deployment/nginx-gateway -n ualflix --timeout=300s || true

# Monitoring
echo "📊 Deploying monitoring..."
kubectl apply -f k8s/monitoring/ || true

echo "✅ Deploy concluído!"

# 8. Verificar status
echo "8️⃣ Verificando status do sistema..."

echo ""
echo "📋 Nós do cluster:"
kubectl get nodes

echo ""
echo "📦 Pods:"
kubectl get pods -n ualflix -o wide

echo ""
echo "🔗 Services:"
kubectl get services -n ualflix

# 9. Obter URLs de acesso
echo "9️⃣ Obtendo URLs de acesso..."

echo ""
echo "🌐 URLs de Acesso:"
echo "Aplicação Principal (NGINX Gateway):"
NGINX_URL=$(minikube service nginx-gateway --namespace ualflix --url)
echo "  $NGINX_URL"

echo ""
echo "Prometheus:"
PROMETHEUS_URL=$(minikube service prometheus-service --namespace ualflix --url 2>/dev/null || echo "  Não disponível")
echo "  $PROMETHEUS_URL"

echo ""
echo "Grafana:"
GRAFANA_URL=$(minikube service grafana-service --namespace ualflix --url 2>/dev/null || echo "  Não disponível")
echo "  $GRAFANA_URL"

# 10. Testes básicos
echo "🔟 Executando testes básicos..."

sleep 10

# Testar NGINX Gateway
if kubectl exec -n ualflix deployment/frontend -- curl -f http://nginx-gateway:8080/health --max-time 10 >/dev/null 2>&1; then
    echo "✅ NGINX Gateway respondendo"
else
    echo "⚠️ NGINX Gateway não respondendo"
fi

# Testar Auth Service
if kubectl exec -n ualflix deployment/frontend -- curl -f http://auth-service:8000/health --max-time 10 >/dev/null 2>&1; then
    echo "✅ Auth Service respondendo"
else
    echo "⚠️ Auth Service não respondendo"
fi

# 11. Verificar distribuição pelos nós
echo "1️⃣1️⃣ Verificando distribuição dos pods pelos nós..."
echo ""
echo "📊 Distribuição por Nó:"
kubectl get pods -n ualflix -o wide | awk '{print $1, $7}' | column -t

# 12. Funcionalidades implementadas
echo ""
echo "🎉 UALFlix configurado com SUCESSO!"
echo ""
echo "✅ Funcionalidades Implementadas:"
echo "FUNCIONALIDADE 1: Tecnologias de Sistemas Distribuídos"
echo "  → Microserviços comunicando via APIs REST"
echo "  → Processamento assíncrono com RabbitMQ"
echo ""
echo "FUNCIONALIDADE 2: Cluster de Computadores (3 nós)"
echo "  → Kubernetes com 3 nós"
echo "  → Coordenação de recursos compartilhados"
echo "  → Adição/remoção de nós sem interrupção"
echo ""
echo "FUNCIONALIDADE 3: Virtualização"
echo "  → Containers Docker para isolamento"
echo "  → Pods Kubernetes para orquestração"
echo ""
echo "FUNCIONALIDADE 4: Implementação na Cloud"
echo "  → Deploy em ambiente Kubernetes"
echo "  → Elasticidade automática (HPA)"
echo ""
echo "FUNCIONALIDADE 5: Replicação de Dados"
echo "  → MongoDB Replica Set com 3 instâncias"
echo "  → Estratégias síncrona e assíncrona"
echo ""
echo "FUNCIONALIDADE 6: Replicação de Serviços"
echo "  → Múltiplas réplicas com Load Balancing"
echo "  → NGINX como roteador principal"
echo "  → Detecção de falhas e recuperação automática"
echo ""
echo "FUNCIONALIDADE 7: Avaliação de Desempenho"
echo "  → Métricas com Prometheus"
echo "  → Dashboards com Grafana"
echo "  → Monitoramento de latência e throughput"

echo ""
echo "🌐 Aplicação disponível em: $NGINX_URL"
echo "📊 Para abrir no browser: minikube service nginx-gateway --namespace ualflix"
echo ""
echo "🔧 Comandos úteis:"
echo "  kubectl get pods -n ualflix -o wide"
echo "  kubectl logs -f -n ualflix deployment/nginx-gateway"
echo "  kubectl scale deployment catalog-service --replicas=5 -n ualflix"
echo "  minikube dashboard"