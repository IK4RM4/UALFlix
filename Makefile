# Makefile para UALFlix - Kubernetes com 3 Nós
# FUNCIONALIDADE 2: IMPLEMENTAÇÃO DE CLUSTER DE COMPUTADORES

NAMESPACE=ualflix
NODES=3
MEMORY=4096
CPUS=2

# Cores para output
RED=\033[0;31m
GREEN=\033[0;32m
YELLOW=\033[1;33m
BLUE=\033[0;34m
NC=\033[0m # No Color

.PHONY: help cluster-start cluster-stop build deploy clean status logs test scale

help: ## Mostrar ajuda
	@echo "${BLUE}UALFlix - Kubernetes com 3 Nós${NC}"
	@echo "${YELLOW}Comandos disponíveis:${NC}"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  ${GREEN}%-15s${NC} %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ========================================
# FUNCIONALIDADE 2: CLUSTER SETUP
# ========================================

cluster-start: ## Iniciar cluster Minikube com 3 nós
	@echo "${BLUE}🚀 Iniciando cluster Kubernetes com $(NODES) nós...${NC}"
	@minikube delete 2>/dev/null || true
	@minikube start \
		--driver=docker \
		--nodes=$(NODES) \
		--cpus=$(CPUS) \
		--memory=$(MEMORY) \
		--disk-size=20g \
		--kubernetes-version=v1.28.0
	@echo "${GREEN}✅ Cluster iniciado com sucesso!${NC}"
	@make addons-enable

addons-enable: ## Habilitar addons necessários
	@echo "${BLUE}🔧 Habilitando addons...${NC}"
	@minikube addons enable ingress
	@minikube addons enable dashboard
	@minikube addons enable metrics-server
	@minikube addons enable default-storageclass
	@minikube addons enable storage-provisioner
	@echo "${GREEN}✅ Addons habilitados!${NC}"

cluster-stop: ## Parar cluster Minikube
	@echo "${RED}🛑 Parando cluster...${NC}"
	@minikube stop

cluster-delete: ## Deletar cluster Minikube
	@echo "${RED}🗑️  Deletando cluster...${NC}"
	@minikube delete

cluster-info: ## Mostrar informações do cluster
	@echo "${BLUE}📊 Informações do Cluster:${NC}"
	@kubectl cluster-info
	@echo "\n${BLUE}📋 Nós do Cluster:${NC}"
	@kubectl get nodes -o wide

# ========================================
# FUNCIONALIDADE 3: VIRTUALIZAÇÃO
# ========================================

docker-env: ## Configurar ambiente Docker do Minikube
	@echo "${BLUE}🐳 Configurando Docker environment...${NC}"
	@eval $$(minikube docker-env)
	@echo "${GREEN}✅ Docker environment configurado!${NC}"

build: docker-env ## Build de todas as imagens Docker
	@echo "${BLUE}🏗️  Building Docker images...${NC}"
	@eval $$(minikube docker-env) && \
	docker build -t frontend:latest ./frontend/ && \
	docker build -t authentication_service:latest ./authentication_service/ && \
	docker build -t catalog_service:latest ./catalog_service/ && \
	docker build -t streaming_service:latest ./streaming_service/ && \
	docker build -t admin_service:latest ./admin_service/ && \
	docker build -t video_processor:latest ./video_processor/
	@echo "${GREEN}✅ Todas as imagens foram construídas!${NC}"

images: ## Listar imagens Docker no Minikube
	@echo "${BLUE}📦 Imagens Docker disponíveis:${NC}"
	@eval $$(minikube docker-env) && docker images | grep -E "(frontend|authentication_service|catalog_service|streaming_service|admin_service|video_processor|mongo|rabbitmq|nginx)"

# ========================================
# FUNCIONALIDADE 4: IMPLEMENTAÇÃO NA CLOUD (Kubernetes)
# ========================================

deploy: build ## Deploy completo da aplicação
	@echo "${BLUE}🚀 Iniciando deploy da aplicação UALFlix...${NC}"
	@make deploy-namespace
	@make deploy-secrets
	@make deploy-database
	@make deploy-messaging
	@make deploy-services
	@make deploy-frontend
	@make deploy-gateway
	@make deploy-monitoring
	@echo "${GREEN}✅ Deploy completo realizado!${NC}"
	@make status

deploy-namespace: ## Criar namespace
	@echo "${YELLOW}📁 Criando namespace...${NC}"
	@kubectl apply -f k8s/namespace.yaml

deploy-secrets: ## Aplicar secrets e configmaps
	@echo "${YELLOW}🔐 Aplicando secrets e configmaps...${NC}"
	@kubectl apply -f k8s/secrets.yaml

deploy-database: ## Deploy MongoDB
	@echo "${YELLOW}🗄️  Deploying MongoDB...${NC}"
	@kubectl apply -f k8s/database/
	@echo "Aguardando MongoDB ficar pronto..."
	@kubectl wait --for=condition=ready pod -l app=mongodb -n $(NAMESPACE) --timeout=300s || true

deploy-messaging: ## Deploy RabbitMQ
	@echo "${YELLOW}🐰 Deploying RabbitMQ...${NC}"
	@kubectl apply -f k8s/messaging/
	@echo "Aguardando RabbitMQ ficar pronto..."
	@kubectl wait --for=condition=ready pod -l app=rabbitmq -n $(NAMESPACE) --timeout=300s || true

deploy-services: ## Deploy serviços da aplicação
	@echo "${YELLOW}🔧 Deploying application services...${NC}"
	@kubectl apply -f k8s/services/auth/
	@kubectl apply -f k8s/services/catalog/
	@kubectl apply -f k8s/services/streaming/
	@kubectl apply -f k8s/services/admin/
	@kubectl apply -f k8s/services/processor/
	@echo "Aguardando serviços ficarem prontos..."
	@kubectl wait --for=condition=available deployment --all -n $(NAMESPACE) --timeout=300s || true

deploy-frontend: ## Deploy React Frontend
	@echo "${YELLOW}⚛️  Deploying React Frontend...${NC}"
	@kubectl apply -f k8s/frontend/
	@kubectl wait --for=condition=available deployment/frontend -n $(NAMESPACE) --timeout=300s || true

deploy-gateway: ## Deploy NGINX Gateway (Roteador Principal)
	@echo "${YELLOW}🌐 Deploying NGINX Gateway...${NC}"
	@kubectl apply -f k8s/ingress/nginx-configmap.yaml
	@kubectl apply -f k8s/ingress/nginx-deployment.yaml
	@kubectl apply -f k8s/ingress/nginx-service.yaml
	@kubectl wait --for=condition=available deployment/nginx-gateway -n $(NAMESPACE) --timeout=300s || true

deploy-monitoring: ## Deploy Prometheus e Grafana
	@echo "${YELLOW}📊 Deploying monitoring stack...${NC}"
	@kubectl apply -f k8s/monitoring/ || true
	@echo "Aguardando monitoring ficar pronto..."
	@kubectl wait --for=condition=available deployment/prometheus -n $(NAMESPACE) --timeout=300s || true
	@kubectl wait --for=condition=available deployment/grafana -n $(NAMESPACE) --timeout=300s || true

# ========================================
# FUNCIONALIDADE 7: AVALIAÇÃO DE DESEMPENHO
# ========================================

status: ## Verificar status do sistema
	@echo "${BLUE}📊 Status do Sistema UALFlix:${NC}"
	@echo "\n${YELLOW}🏷️  Namespace:${NC}"
	@kubectl get namespace $(NAMESPACE)
	@echo "\n${YELLOW}📦 Pods:${NC}"
	@kubectl get pods -n $(NAMESPACE) -o wide
	@echo "\n${YELLOW}🔗 Services:${NC}"
	@kubectl get services -n $(NAMESPACE)
	@echo "\n${YELLOW}🚀 Deployments:${NC}"
	@kubectl get deployments -n $(NAMESPACE)
	@echo "\n${YELLOW}⚖️  HPA (Auto-scaling):${NC}"
	@kubectl get hpa -n $(NAMESPACE) || echo "Nenhum HPA configurado ainda"

pods: ## Listar pods com detalhes
	@kubectl get pods -n $(NAMESPACE) -o wide

services: ## Listar serviços
	@kubectl get services -n $(NAMESPACE) -o wide

logs: ## Ver logs dos serviços principais
	@echo "${BLUE}📋 Logs dos Serviços:${NC}"
	@echo "\n${YELLOW}🌐 NGINX Gateway:${NC}"
	@kubectl logs -n $(NAMESPACE) deployment/nginx-gateway --tail=10 || true
	@echo "\n${YELLOW}🔐 Authentication Service:${NC}"
	@kubectl logs -n $(NAMESPACE) deployment/auth-service --tail=10 || true
	@echo "\n${YELLOW}📁 Catalog Service:${NC}"
	@kubectl logs -n $(NAMESPACE) deployment/catalog-service --tail=10 || true

logs-follow: ## Seguir logs em tempo real
	@echo "${BLUE}📋 Seguindo logs do NGINX Gateway...${NC}"
	@kubectl logs -f -n $(NAMESPACE) deployment/nginx-gateway

# ========================================
# FUNCIONALIDADE 6: REPLICAÇÃO DE SERVIÇOS
# ========================================

scale: ## Escalar serviços (uso: make scale SERVICE=catalog-service REPLICAS=5)
	@echo "${BLUE}⚖️  Escalando $(SERVICE) para $(REPLICAS) réplicas...${NC}"
	@kubectl scale deployment $(SERVICE) --replicas=$(REPLICAS) -n $(NAMESPACE)
	@kubectl get deployment $(SERVICE) -n $(NAMESPACE)

scale-all: ## Escalar todos os serviços principais
	@echo "${BLUE}⚖️  Escalando todos os serviços...${NC}"
	@kubectl scale deployment auth-service --replicas=3 -n $(NAMESPACE)
	@kubectl scale deployment catalog-service --replicas=4 -n $(NAMESPACE)
	@kubectl scale deployment streaming-service --replicas=4 -n $(NAMESPACE)
	@kubectl scale deployment admin-service --replicas=2 -n $(NAMESPACE)
	@kubectl scale deployment nginx-gateway --replicas=3 -n $(NAMESPACE)
	@echo "${GREEN}✅ Escalamento concluído!${NC}"

scale-down: ## Reduzir réplicas para economizar recursos
	@echo "${YELLOW}⬇️  Reduzindo réplicas...${NC}"
	@kubectl scale deployment auth-service --replicas=1 -n $(NAMESPACE)
	@kubectl scale deployment catalog-service --replicas=2 -n $(NAMESPACE)
	@kubectl scale deployment streaming-service --replicas=2 -n $(NAMESPACE)
	@kubectl scale deployment admin-service --replicas=1 -n $(NAMESPACE)
	@kubectl scale deployment nginx-gateway --replicas=2 -n $(NAMESPACE)

# ========================================
# ACESSO À APLICAÇÃO
# ========================================

url: ## Obter URL da aplicação
	@echo "${BLUE}🌐 URLs de Acesso:${NC}"
	@echo "${GREEN}Aplicação Principal (NGINX Gateway):${NC}"
	@minikube service nginx-gateway --namespace $(NAMESPACE) --url
	@echo "\n${GREEN}Prometheus:${NC}"
	@minikube service prometheus-service --namespace $(NAMESPACE) --url || true
	@echo "\n${GREEN}Grafana:${NC}"
	@minikube service grafana-service --namespace $(NAMESPACE) --url || true

open: ## Abrir aplicação no browser
	@echo "${BLUE}🌐 Abrindo UALFlix no browser...${NC}"
	@minikube service nginx-gateway --namespace $(NAMESPACE)

dashboard: ## Abrir Kubernetes Dashboard
	@echo "${BLUE}📊 Abrindo Kubernetes Dashboard...${NC}"
	@minikube dashboard

tunnel: ## Iniciar tunnel para LoadBalancer (deixar rodando em terminal separado)
	@echo "${BLUE}🚇 Iniciando Minikube tunnel...${NC}"
	@echo "${YELLOW}⚠️  Mantenha este comando rodando em um terminal separado${NC}"
	@minikube tunnel

port-forward: ## Port forward para desenvolvimento
	@echo "${BLUE}🔌 Iniciando port forwards...${NC}"
	@echo "${YELLOW}NGINX Gateway: http://localhost:8080${NC}"
	@kubectl port-forward -n $(NAMESPACE) service/nginx-gateway 8080:8080 &
	@echo "${YELLOW}Prometheus: http://localhost:9090${NC}"
	@kubectl port-forward -n $(NAMESPACE) service/prometheus-service 9090:9090 &
	@echo "${YELLOW}Grafana: http://localhost:3001${NC}"
	@kubectl port-forward -n $(NAMESPACE) service/grafana-service 3001:3000 &
	@echo "${GREEN}✅ Port forwards iniciados em background${NC}"

# ========================================
# TESTES E DEBUG
# ========================================

test: ## Testar conectividade dos serviços
	@echo "${BLUE}🧪 Testando conectividade...${NC}"
	@echo "\n${YELLOW}Testando NGINX Gateway:${NC}"
	@kubectl exec -n $(NAMESPACE) deployment/frontend -- curl -f http://nginx-gateway:8080/health || true
	@echo "\n${YELLOW}Testando Auth Service:${NC}"
	@kubectl exec -n $(NAMESPACE) deployment/frontend -- curl -f http://auth-service:8000/health || true
	@echo "\n${YELLOW}Testando Catalog Service:${NC}"
	@kubectl exec -n $(NAMESPACE) deployment/frontend -- curl -f http://catalog-service:8000/health || true

debug: ## Debug de um pod específico (uso: make debug POD=catalog-service)
	@echo "${BLUE}🐛 Entrando no pod $(POD)...${NC}"
	@kubectl exec -it -n $(NAMESPACE) deployment/$(POD) -- /bin/bash

describe: ## Descrever um recurso (uso: make describe RESOURCE=pod/nome-do-pod)
	@kubectl describe -n $(NAMESPACE) $(RESOURCE)

events: ## Ver eventos do cluster
	@echo "${BLUE}📅 Eventos do Cluster:${NC}"
	@kubectl get events -n $(NAMESPACE) --sort-by=.metadata.creationTimestamp

top: ## Ver utilização de recursos
	@echo "${BLUE}📊 Utilização de Recursos:${NC}"
	@echo "\n${YELLOW}Nós:${NC}"
	@kubectl top nodes || echo "Metrics server não disponível"
	@echo "\n${YELLOW}Pods:${NC}"
	@kubectl top pods -n $(NAMESPACE) || echo "Metrics server não disponível"

# ========================================
# LIMPEZA
# ========================================

clean: ## Remover toda a aplicação (manter cluster)
	@echo "${RED}🧹 Removendo aplicação UALFlix...${NC}"
	@kubectl delete namespace $(NAMESPACE) --ignore-not-found=true
	@echo "${GREEN}✅ Aplicação removida!${NC}"

clean-all: clean cluster-delete ## Remover tudo (aplicação + cluster)
	@echo "${RED}🗑️  Limpeza completa realizada!${NC}"

restart: ## Reiniciar um deployment (uso: make restart SERVICE=catalog-service)
	@echo "${BLUE}🔄 Reiniciando $(SERVICE)...${NC}"
	@kubectl rollout restart deployment/$(SERVICE) -n $(NAMESPACE)
	@kubectl rollout status deployment/$(SERVICE) -n $(NAMESPACE)

restart-all: ## Reiniciar todos os deployments
	@echo "${BLUE}🔄 Reiniciando todos os serviços...${NC}"
	@kubectl rollout restart deployment --all -n $(NAMESPACE)

# ========================================
# FUNCIONALIDADES COMPLETAS
# ========================================

demo: cluster-start deploy url ## Setup completo para demonstração
	@echo "${GREEN}🎉 UALFlix está pronto para demonstração!${NC}"
	@echo "${BLUE}Funcionalidades implementadas:${NC}"
	@echo "✅ FUNCIONALIDADE 1: Tecnologias de Sistemas Distribuídos"
	@echo "✅ FUNCIONALIDADE 2: Cluster de Computadores (3 nós)"
	@echo "✅ FUNCIONALIDADE 3: Virtualização (Docker + Kubernetes)"
	@echo "✅ FUNCIONALIDADE 4: Implementação na Cloud (Kubernetes)"
	@echo "✅ FUNCIONALIDADE 5: Replicação de Dados (MongoDB)"
	@echo "✅ FUNCIONALIDADE 6: Replicação de Serviços (Load Balancing)"
	@echo "✅ FUNCIONALIDADE 7: Avaliação de Desempenho (Métricas)"

verify: ## Verificar se tudo está funcionando
	@echo "${BLUE}✅ Verificação Final do Sistema:${NC}"
	@echo "\n${YELLOW}1. Nós do cluster:${NC}"
	@kubectl get nodes
	@echo "\n${YELLOW}2. Pods em execução:${NC}"
	@kubectl get pods -n $(NAMESPACE)
	@echo "\n${YELLOW}3. Serviços disponíveis:${NC}"
	@kubectl get services -n $(NAMESPACE)
	@echo "\n${YELLOW}4. Testando aplicação:${NC}"
	@curl -f $$(minikube service nginx-gateway --namespace $(NAMESPACE) --url)/health 2>/dev/null && echo "✅ Aplicação respondendo" || echo "❌ Aplicação não responde"