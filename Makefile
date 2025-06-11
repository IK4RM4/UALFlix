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
	@echo "UALFlix - Kubernetes com 3 Nós"
	@echo "Comandos disponíveis:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ========================================
# FUNCIONALIDADE 2: CLUSTER SETUP
# ========================================

cluster-start: ## Iniciar cluster Minikube com 3 nós
	@echo "🚀 Iniciando cluster Kubernetes com $(NODES) nós..."
	@minikube delete 2>/dev/null || true
	@minikube start \
		--driver=docker \
		--nodes=$(NODES) \
		--cpus=$(CPUS) \
		--memory=$(MEMORY) \
		--disk-size=20g \
		--kubernetes-version=v1.28.0
	@echo "✅ Cluster iniciado com sucesso!"
	@make addons-enable

addons-enable: ## Habilitar addons necessários
	@echo "🔧 Habilitando addons..."
	@minikube addons enable ingress
	@minikube addons enable dashboard
	@minikube addons enable metrics-server
	@minikube addons enable default-storageclass
	@minikube addons enable storage-provisioner
	@echo "✅ Addons habilitados!"

cluster-stop: ## Parar cluster Minikube
	@echo "🛑 Parando cluster..."
	@minikube stop

cluster-delete: ## Deletar cluster Minikube
	@echo "🗑️  Deletando cluster..."
	@minikube delete

cluster-info: ## Mostrar informações do cluster
	@echo "📊 Informações do Cluster:"
	@kubectl cluster-info
	@echo "\n📋 Nós do Cluster:"
	@kubectl get nodes -o wide

# ========================================
# FUNCIONALIDADE 3: VIRTUALIZAÇÃO
# ========================================

docker-env: ## Configurar ambiente Docker do Minikube
	@echo "🐳 Configurando Docker environment..."
	@eval $$(minikube docker-env)
	@echo "✅ Docker environment configurado!"

build: ## Build de todas as imagens Docker
	@echo "🏗️  Building Docker images..."
	@for service in frontend authentication_service catalog_service streaming_service admin_service video_processor; do \
		echo "Building $$service..."; \
		docker build -t localhost:5000/$$service:latest ./$$service/; \
		docker push localhost:5000/$$service:latest; \
	done
	@echo "✅ Todas as imagens foram construídas!"

images: ## Listar imagens Docker no Minikube
	@echo "📦 Imagens Docker disponíveis:"
	@eval $$(minikube docker-env) && docker images | grep -E "(frontend|authentication_service|catalog_service|streaming_service|admin_service|video_processor|mongo|rabbitmq|nginx)"

# ========================================
# FUNCIONALIDADE 4: IMPLEMENTAÇÃO NA CLOUD (Kubernetes)
# ========================================

deploy: ## Deploy completo da aplicação
	@echo "🚀 Iniciando deploy da aplicação UALFlix..."
	@make deploy-namespace
	@make deploy-secrets
	@make deploy-database
	@make deploy-messaging
	@make deploy-services
	@make deploy-frontend
	@make deploy-gateway
	@make deploy-monitoring
	@echo "✅ Deploy completo realizado!"
	@make status

deploy-namespace: ## Criar namespace
	@echo "📁 Criando namespace..."
	@kubectl apply -f k8s/namespace.yaml

deploy-secrets: ## Aplicar secrets e configmaps
	@echo "🔐 Aplicando secrets e configmaps..."
	@kubectl apply -f k8s/secrets.yaml

deploy-database: ## Deploy MongoDB
	@echo "🗄️  Deploying MongoDB..."
	@kubectl apply -f k8s/database/
	@echo "Aguardando MongoDB ficar pronto..."
	@kubectl wait --for=condition=ready pod -l app=mongodb -n $(NAMESPACE) --timeout=300s || true

deploy-messaging: ## Deploy RabbitMQ
	@echo "🐰 Deploying RabbitMQ..."
	@kubectl apply -f k8s/messaging/
	@echo "Aguardando RabbitMQ ficar pronto..."
	@kubectl wait --for=condition=ready pod -l app=rabbitmq -n $(NAMESPACE) --timeout=300s || true

deploy-services: ## Deploy serviços da aplicação
	@echo "🔧 Deploying application services..."
	@kubectl apply -f k8s/services/auth/
	@kubectl apply -f k8s/services/catalog/
	@kubectl apply -f k8s/services/streaming/
	@kubectl apply -f k8s/services/admin/
	@kubectl apply -f k8s/services/processor/
	@echo "Aguardando serviços ficarem prontos..."
	@kubectl wait --for=condition=available deployment --all -n $(NAMESPACE) --timeout=300s || true

deploy-frontend: ## Deploy React Frontend
	@echo "⚛️  Deploying React Frontend..."
	@kubectl apply -f k8s/frontend/
	@kubectl wait --for=condition=available deployment/frontend -n $(NAMESPACE) --timeout=300s || true

deploy-gateway: ## Deploy NGINX Gateway (Roteador Principal)
	@echo "🌐 Deploying NGINX Gateway..."
	@kubectl apply -f k8s/ingress/nginx-configmap.yaml
	@kubectl apply -f k8s/ingress/nginx-deployment.yaml
	@kubectl apply -f k8s/ingress/nginx-service.yaml
	@kubectl wait --for=condition=available deployment/nginx-gateway -n $(NAMESPACE) --timeout=300s || true

deploy-monitoring: ## Deploy Prometheus e Grafana
	@echo "📊 Deploying monitoring stack..."
	@kubectl apply -f k8s/monitoring/ || true
	@echo "Aguardando monitoring ficar pronto..."
	@kubectl wait --for=condition=available deployment/prometheus -n $(NAMESPACE) --timeout=300s || true
	@kubectl wait --for=condition=available deployment/grafana -n $(NAMESPACE) --timeout=300s || true

# ========================================
# FUNCIONALIDADE 7: AVALIAÇÃO DE DESEMPENHO
# ========================================

status: ## Verificar status do sistema
	@echo "📊 Status do Sistema UALFlix:"
	@echo "\n🏷️  Namespace:"
	@kubectl get namespace $(NAMESPACE)
	@echo "\n📦 Pods:"
	@kubectl get pods -n $(NAMESPACE) -o wide
	@echo "\n🔗 Services:"
	@kubectl get services -n $(NAMESPACE)
	@echo "\n🚀 Deployments:"
	@kubectl get deployments -n $(NAMESPACE)
	@echo "\n⚖️  HPA (Auto-scaling):"
	@kubectl get hpa -n $(NAMESPACE) || echo "Nenhum HPA configurado ainda"

pods: ## Listar pods com detalhes
	@kubectl get pods -n $(NAMESPACE) -o wide

services: ## Listar serviços
	@kubectl get services -n $(NAMESPACE) -o wide

logs: ## Ver logs dos serviços principais
	@echo "📋 Logs dos Serviços:"
	@echo "\n🌐 NGINX Gateway:"
	@kubectl logs -n $(NAMESPACE) deployment/nginx-gateway --tail=10 || true
	@echo "\n🔐 Authentication Service:"
	@kubectl logs -n $(NAMESPACE) deployment/auth-service --tail=10 || true
	@echo "\n📁 Catalog Service:"
	@kubectl logs -n $(NAMESPACE) deployment/catalog-service --tail=10 || true

logs-follow: ## Seguir logs em tempo real
	@echo "📋 Seguindo logs do NGINX Gateway..."
	@kubectl logs -f -n $(NAMESPACE) deployment/nginx-gateway

# ========================================
# FUNCIONALIDADE 6: REPLICAÇÃO DE SERVIÇOS
# ========================================

scale: ## Escalar serviços (uso: make scale SERVICE=catalog-service REPLICAS=5)
	@echo "⚖️  Escalando $(SERVICE) para $(REPLICAS) réplicas..."
	@kubectl scale deployment $(SERVICE) --replicas=$(REPLICAS) -n $(NAMESPACE)
	@kubectl get deployment $(SERVICE) -n $(NAMESPACE)

scale-all: ## Escalar todos os serviços principais
	@echo "⚖️  Escalando todos os serviços..."
	@kubectl scale deployment auth-service --replicas=3 -n $(NAMESPACE)
	@kubectl scale deployment catalog-service --replicas=4 -n $(NAMESPACE)
	@kubectl scale deployment streaming-service --replicas=4 -n $(NAMESPACE)
	@kubectl scale deployment admin-service --replicas=2 -n $(NAMESPACE)
	@kubectl scale deployment nginx-gateway --replicas=3 -n $(NAMESPACE)
	@echo "✅ Escalamento concluído!"

scale-down: ## Reduzir réplicas para economizar recursos
	@echo "⬇️  Reduzindo réplicas..."
	@kubectl scale deployment auth-service --replicas=1 -n $(NAMESPACE)
	@kubectl scale deployment catalog-service --replicas=2 -n $(NAMESPACE)
	@kubectl scale deployment streaming-service --replicas=2 -n $(NAMESPACE)
	@kubectl scale deployment admin-service --replicas=1 -n $(NAMESPACE)
	@kubectl scale deployment nginx-gateway --replicas=2 -n $(NAMESPACE)

# ========================================
# ACESSO À APLICAÇÃO
# ========================================

url: ## Obter URL da aplicação
	@echo "🌐 URLs de Acesso:"
	@echo "Aplicação Principal (NGINX Gateway):"
	@minikube service nginx-gateway --namespace $(NAMESPACE) --url
	@echo "\nPrometheus:"
	@minikube service prometheus-service --namespace $(NAMESPACE) --url || true
	@echo "\nGrafana:"
	@minikube service grafana-service --namespace $(NAMESPACE) --url || true

open: ## Abrir aplicação no browser
	@echo "🌐 Abrindo UALFlix no browser..."
	@minikube service nginx-gateway --namespace $(NAMESPACE)

dashboard: ## Abrir Kubernetes Dashboard
	@echo "📊 Abrindo Kubernetes Dashboard..."
	@minikube dashboard

tunnel: ## Iniciar tunnel para LoadBalancer (deixar rodando em terminal separado)
	@echo "🚇 Iniciando Minikube tunnel..."
	@echo "⚠️  Mantenha este comando rodando em um terminal separado"
	@minikube tunnel

port-forward: ## Port forward para desenvolvimento
	@echo "🔌 Iniciando port forwards..."
	@echo "NGINX Gateway: http://localhost:8080"
	@kubectl port-forward -n $(NAMESPACE) service/nginx-gateway 8080:8080 &
	@echo "Prometheus: http://localhost:9090"
	@kubectl port-forward -n $(NAMESPACE) service/prometheus-service 9090:9090 &
	@echo "Grafana: http://localhost:3001"
	@kubectl port-forward -n $(NAMESPACE) service/grafana-service 3001:3000 &
	@echo "✅ Port forwards iniciados em background"

# ========================================
# TESTES E DEBUG
# ========================================

test: ## Testar conectividade dos serviços
	@echo "🧪 Testando conectividade..."
	@echo "\nTestando NGINX Gateway:"
	@kubectl exec -n $(NAMESPACE) deployment/frontend -- curl -f http://nginx-gateway:8080/health || true
	@echo "\nTestando Auth Service:"
	@kubectl exec -n $(NAMESPACE) deployment/frontend -- curl -f http://auth-service:8000/health || true
	@echo "\nTestando Catalog Service:"
	@kubectl exec -n $(NAMESPACE) deployment/frontend -- curl -f http://catalog-service:8000/health || true

debug: ## Debug de um pod específico (uso: make debug POD=catalog-service)
	@echo "🐛 Entrando no pod $(POD)..."
	@kubectl exec -it -n $(NAMESPACE) deployment/$(POD) -- /bin/bash

describe: ## Descrever um recurso (uso: make describe RESOURCE=pod/nome-do-pod)
	@kubectl describe -n $(NAMESPACE) $(RESOURCE)

events: ## Ver eventos do cluster
	@echo "📅 Eventos do Cluster:"
	@kubectl get events -n $(NAMESPACE) --sort-by=.metadata.creationTimestamp

top: ## Ver utilização de recursos
	@echo "📊 Utilização de Recursos:"
	@echo "\nNós:"
	@kubectl top nodes || echo "Metrics server não disponível"
	@echo "\nPods:"
	@kubectl top pods -n $(NAMESPACE) || echo "Metrics server não disponível"

# ========================================
# LIMPEZA
# ========================================

clean: ## Remover toda a aplicação (manter cluster)
	@echo "🧹 Removendo aplicação UALFlix..."
	@kubectl delete namespace $(NAMESPACE) --ignore-not-found=true
	@echo "✅ Aplicação removida!"

clean-all: clean cluster-delete ## Remover tudo (aplicação + cluster)
	@echo "🗑️  Limpeza completa realizada!"

restart: ## Reiniciar um deployment (uso: make restart SERVICE=catalog-service)
	@echo "🔄 Reiniciando $(SERVICE)..."
	@kubectl rollout restart deployment/$(SERVICE) -n $(NAMESPACE)
	@kubectl rollout status deployment/$(SERVICE) -n $(NAMESPACE)

restart-all: ## Reiniciar todos os deployments
	@echo "🔄 Reiniciando todos os serviços..."
	@kubectl rollout restart deployment --all -n $(NAMESPACE)

# Adicionar estas regras ao Makefile existente

# ========================================
# CORREÇÃO PARA MULTI-NODE
# ========================================

setup-registry: ## Configurar registry para multi-node
	@echo "📦 Configurando registry para cluster multi-nó..."
	@minikube addons enable registry
	@echo "Aguardando registry ficar pronto..."
	@kubectl wait --for=condition=ready pod -l app=registry -n kube-system --timeout=120s || true
	@echo "✅ Registry configurado!"

start-registry-forward: ## Iniciar port-forward para registry
	@echo "🔌 Iniciando port-forward para registry..."
	@kubectl port-forward -n kube-system service/registry 5000:80 &
	@sleep 3
	@echo "✅ Registry disponível em localhost:5000"

build-registry: setup-registry start-registry-forward ## Build para registry local (multi-node)
	@echo "🏗️ Building imagens para registry local..."
	@for service in frontend authentication_service catalog_service streaming_service admin_service video_processor; do \
		echo "Building $$service..."; \
		docker build -t $$service:latest ./$$service/; \
		docker tag $$service:latest localhost:5000/$$service:latest; \
		docker push localhost:5000/$$service:latest; \
		echo "✅ $$service enviado para registry"; \
	done
	@echo "✅ Todas as imagens no registry local!"

# Override do build original para detectar multi-node
build: ## Build de todas as imagens Docker (detecta multi-node)
	@NODE_COUNT=$$(kubectl get nodes --no-headers | wc -l); \
	if [ $$NODE_COUNT -gt 1 ]; then \
		echo "⚠️ Cluster multi-nó detectado ($$NODE_COUNT nós)"; \
		echo "Usando registry local..."; \
		$(MAKE) build-registry; \
	else \
		echo "Cluster single-nó, usando docker-env..."; \
		$(MAKE) docker-env; \
		$(MAKE) build-local; \
	fi

build-local: docker-env ## Build local (apenas single-node)
	@echo "🏗️ Building Docker images localmente..."
	@eval $$(minikube docker-env) && \
	for service in frontend authentication_service catalog_service streaming_service admin_service video_processor; do \
		echo "Building $$service..."; \
		docker build -t $$service:latest ./$$service/; \
	done
	@echo "✅ Todas as imagens foram construídas!"

# Deploy com detecção automática
deploy: ## Deploy automático (detecta single/multi-node)
	@NODE_COUNT=$$(kubectl get nodes --no-headers | wc -l); \
	if [ $$NODE_COUNT -gt 1 ]; then \
		echo "Deploy para cluster multi-nó ($$NODE_COUNT nós)"; \
		$(MAKE) deploy-multinode; \
	else \
		echo "Deploy para cluster single-nó"; \
		$(MAKE) deploy-standard; \
	fi

deploy-multinode: ## Deploy para multi-node com registry
	@echo "🚀 Deploy para cluster multi-nó..."
	@$(MAKE) deploy-namespace
	@$(MAKE) deploy-secrets
	@$(MAKE) deploy-database
	@$(MAKE) deploy-messaging
	@$(MAKE) deploy-services-registry
	@$(MAKE) deploy-frontend-registry
	@$(MAKE) deploy-gateway
	@$(MAKE) deploy-monitoring
	@echo "✅ Deploy multi-nó concluído!"

deploy-services-registry: ## Deploy serviços usando registry
	@echo "🔧 Deploying services com registry local..."
	@# Criar manifests temporários com registry
	@mkdir -p tmp-manifests
	@for service in auth catalog streaming admin processor; do \
		if [ -f "k8s/services/$$service/deployment.yaml" ]; then \
			sed 's|image: \([^:]*\):latest|image: localhost:5000/\1:latest|g' k8s/services/$$service/deployment.yaml > tmp-manifests/$$service-deployment.yaml; \
			kubectl apply -f tmp-manifests/$$service-deployment.yaml; \
			kubectl apply -f k8s/services/$$service/service.yaml; \
		fi \
	done
	@rm -rf tmp-manifests

deploy-frontend-registry: ## Deploy frontend usando registry
	@echo "⚛️ Deploying frontend com registry..."
	@mkdir -p tmp-manifests
	@sed 's|image: frontend:latest|image: localhost:5000/frontend:latest|g' k8s/frontend/deployment.yaml > tmp-manifests/frontend-deployment.yaml
	@kubectl apply -f tmp-manifests/frontend-deployment.yaml
	@kubectl apply -f k8s/frontend/service.yaml
	@rm -rf tmp-manifests

deploy-standard: deploy-namespace deploy-secrets deploy-database deploy-messaging deploy-services deploy-frontend deploy-gateway deploy-monitoring ## Deploy padrão

# Converter cluster para single-node (se necessário)
cluster-single: ## Converter para cluster single-node
	@echo "🔄 Convertendo para cluster single-node..."
	@minikube delete
	@minikube start \
		--driver=docker \
		--nodes=1 \
		--cpus=$(CPUS) \
		--memory=$(MEMORY) \
		--disk-size=20g \
		--kubernetes-version=v1.28.0
	@$(MAKE) addons-enable
	@echo "✅ Cluster single-node criado!"

# Build usando Docker Hub (alternativa)
build-dockerhub: ## Build e push para Docker Hub
	@echo "🐳 Building e enviando para Docker Hub..."
	@read -p "Docker Hub username: " username; \
	for service in frontend authentication_service catalog_service streaming_service admin_service video_processor; do \
		echo "Building $$service..."; \
		docker build -t $$username/ualflix-$$service:latest ./$$service/; \
		docker push $$username/ualflix-$$service:latest; \
	done
	@echo "✅ Imagens enviadas para Docker Hub!"

# Verificar tipo de cluster
cluster-info-extended: ## Informações detalhadas do cluster
	@echo "📊 Informações do Cluster:"
	@kubectl cluster-info
	@echo "\n📋 Nós do Cluster:"
	@kubectl get nodes -o wide
	@NODE_COUNT=$$(kubectl get nodes --no-headers | wc -l); \
	echo "\nTipo de cluster:"; \
	if [ $$NODE_COUNT -eq 1 ]; then \
		echo "  🔸 Single-node ($$NODE_COUNT nó) - Use 'make build' normal"; \
	else \
		echo "  🔹 Multi-node ($$NODE_COUNT nós) - Use 'make build-registry'"; \
	fi
	
# ========================================
# FUNCIONALIDADES COMPLETAS
# ========================================

demo: cluster-start deploy url ## Setup completo para demonstração
	@echo "🎉 UALFlix está pronto para demonstração!"
	@echo "Funcionalidades implementadas:"
	@echo "✅ FUNCIONALIDADE 1: Tecnologias de Sistemas Distribuídos"
	@echo "✅ FUNCIONALIDADE 2: Cluster de Computadores (3 nós)"
	@echo "✅ FUNCIONALIDADE 3: Virtualização (Docker + Kubernetes)"
	@echo "✅ FUNCIONALIDADE 4: Implementação na Cloud (Kubernetes)"
	@echo "✅ FUNCIONALIDADE 5: Replicação de Dados (MongoDB)"
	@echo "✅ FUNCIONALIDADE 6: Replicação de Serviços (Load Balancing)"
	@echo "✅ FUNCIONALIDADE 7: Avaliação de Desempenho (Métricas)"

verify: ## Verificar se tudo está funcionando
	@echo "✅ Verificação Final do Sistema:"
	@echo "\n1. Nós do cluster:"
	@kubectl get nodes
	@echo "\n2. Pods em execução:"
	@kubectl get pods -n $(NAMESPACE)
	@echo "\n3. Serviços disponíveis:"
	@kubectl get services -n $(NAMESPACE)
	@echo "\n4. Testando aplicação:"
	@curl -f $$(minikube service nginx-gateway --namespace $(NAMESPACE) --url)/health 2>/dev/null && echo "✅ Aplicação respondendo" || echo "❌ Aplicação não responde"