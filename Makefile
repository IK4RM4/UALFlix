# ================================================================
# UALFlix Makefile - Sistema Simplificado e Funcional
# CORRIGIDO para funcionar com a configuracão atual
# ================================================================

.PHONY: help build up down restart logs clean status deploy test
.PHONY: build-services up-database up-services up-monitoring up-frontend
.PHONY: logs-master logs-services backup restore clean-volumes clean-all
.PHONY: health test-connectivity scale-services

# ================================================================
# CONFIGURAcÕES PRINCIPAIS
# ================================================================

PROJECT_NAME = ualflix
COMPOSE_FILE = docker-compose.yml
MASTER_CONTAINER = ualflix_db_master

# Cores para output
RED = \033[0;31m
GREEN = \033[0;32m
YELLOW = \033[1;33m
BLUE = \033[0;34m
PURPLE = \033[0;35m
CYAN = \033[0;36m
NC = \033[0m # No Color

# ================================================================
# COMANDOS PRINCIPAIS
# ================================================================

help: ## 📋 Mostrar todos os comandos disponíveis
	@echo ""
	@echo "🎬 UALFlix - Sistema de Streaming com Métricas Automaticas"
	@echo "================================================================"
	@echo ""
	@echo "📋 COMANDOS PRINCIPAIS:"
	@echo "  make help              - Mostrar esta ajuda"
	@echo "  make deploy            - Deploy completo do sistema"
	@echo "  make build             - Construir todos os containers"
	@echo "  make up                - Iniciar todos os servicos"
	@echo "  make down              - Parar todos os servicos"
	@echo "  make restart           - Reiniciar todos os servicos"
	@echo "  make status            - Ver status dos containers"
	@echo ""
	@echo "🗄️ COMANDOS DE DATABASE:"
	@echo "  make up-database       - Iniciar base de dados"
	@echo "  make logs-master       - Ver logs da base de dados"
	@echo "  make test-db           - Testar conexão à base de dados"
	@echo ""
	@echo "📊 COMANDOS DE MONITORIZAcÃO:"
	@echo "  make health            - Health check de todos os servicos"
	@echo "  make logs              - Ver logs de todos os servicos"
	@echo "  make logs-services     - Ver logs dos servicos principais"
	@echo "  make test-connectivity - Testar conectividade"
	@echo ""
	@echo "🔧 COMANDOS DE MANUTENcÃO:"
	@echo "  make clean             - Limpar containers e imagens"
	@echo "  make clean-volumes     - Limpar volumes de dados"
	@echo "  make clean-all         - Limpeza completa do sistema"
	@echo "  make backup            - Fazer backup da base de dados"
	@echo ""
	@echo "⚡ COMANDOS DE ESCALABILIDADE:"
	@echo "  make scale-services    - Escalar servicos (2 réplicas cada)"
	@echo "  make scale-down        - Reduzir escala (1 réplica cada)"
	@echo ""
	@echo "🌐 URLs DE ACESSO:"
	@echo "  Frontend:        http://localhost:8080"
	@echo "  Prometheus:      http://localhost:9090"
	@echo "  Grafana:         http://localhost:4000 (admin/admin)"
	@echo "  RabbitMQ:        http://localhost:15672 (ualflix/ualflix_password)"
	@echo "  Master DB:       localhost:5432"
	@echo ""

# ================================================================
# COMANDOS DE BUILD
# ================================================================

build: ## 🏗️ Construir todos os containers
	@echo "🏗️ Construindo todos os containers..."
	docker-compose build --parallel
	@echo "✅ Build concluído!"

build-services: ## 🔧 Construir apenas servicos principais
	@echo "🔧 Construindo servicos principais..."
	docker-compose build authentication_service catalog_service streaming_service admin_service
	@echo "✅ Servicos construídos!"

# ================================================================
# COMANDOS DE EXECUcÃO
# ================================================================

deploy: ## 🚀 Deploy completo do sistema
	@echo "🚀 Iniciando deploy completo do UALFlix..."
	@echo "📦 Fazendo build de todos os servicos..."
	$(MAKE) build
	@echo "🚀 Iniciando todos os servicos..."
	$(MAKE) up
	@echo "✅ Deploy concluído!"
	@echo ""
	@echo "🌐 Sistema disponível em:"
	@echo "  Frontend: http://localhost:8080"
	@echo "  Admin (login: admin/admin): http://localhost:8080"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Grafana: http://localhost:4000"

up: up-database up-services up-monitoring up-frontend ## ⬆️ Iniciar todos os servicos

up-database: ## 🗄️ Iniciar base de dados
	@echo "🗄️ Iniciando base de dados..."
	docker-compose up -d ualflix_db_master
	@echo "⏳ Aguardando Master estar pronto..."
	@timeout=60; while [ $$timeout -gt 0 ]; do \
		if docker exec $(MASTER_CONTAINER) pg_isready -U postgres -d ualflix > /dev/null 2>&1; then \
			echo "✅ Master esta pronto!"; \
			break; \
		fi; \
		echo "⏳ Aguardando Master... ($$timeout segundos restantes)"; \
		sleep 2; \
		timeout=$$((timeout - 2)); \
	done
	@echo "✅ Base de dados iniciada!"

up-services: ## 🔧 Iniciar servicos principais
	@echo "🔧 Iniciando servicos principais..."
	docker-compose up -d queue_service
	sleep 3
	docker-compose up -d authentication_service catalog_service
	sleep 3
	docker-compose up -d streaming_service video_processor admin_service
	@echo "✅ Servicos principais iniciados!"

up-monitoring: ## 📊 Iniciar monitoring (Prometheus, Grafana)
	@echo "📊 Iniciando servicos de monitoring..."
	docker-compose up -d prometheus grafana
	@echo "✅ Monitoring iniciado!"

up-frontend: ## 🌐 Iniciar frontend e proxy
	@echo "🌐 Iniciando frontend..."
	docker-compose up -d frontend nginx
	@echo "✅ Frontend iniciado!"

down: ## ⬇️ Parar todos os servicos
	@echo "⬇️ Parando todos os servicos..."
	docker-compose down
	@echo "✅ Todos os servicos parados!"

restart: down up ## 🔄 Reiniciar todos os servicos

# ================================================================
# COMANDOS DE MONITORIZAcÃO
# ================================================================

status: ## 📊 Ver status dos containers
	@echo "📊 Status dos containers:"
	@echo ""
	docker-compose ps
	@echo ""
	@echo "🗄️ Status da base de dados:"
	@if docker exec $(MASTER_CONTAINER) pg_isready -U postgres -d ualflix > /dev/null 2>&1; then \
		echo "✅ Master Database: ONLINE (porta 5432)"; \
	else \
		echo "❌ Master Database: OFFLINE"; \
	fi

health: ## 🏥 Health check de todos os servicos
	@echo "🏥 Verificando saúde dos servicos..."
	@echo ""
	@services="authentication_service:8000 catalog_service:8000 streaming_service:8001 admin_service:8002"; \
	for service in $$services; do \
		name=$$(echo $$service | cut -d: -f1); \
		port=$$(echo $$service | cut -d: -f2); \
		if curl -s http://localhost:$$port/health > /dev/null 2>&1; then \
			echo "✅ $$name: HEALTHY"; \
		else \
			echo "❌ $$name: UNHEALTHY"; \
		fi; \
	done
	@echo ""
	@echo "🌐 URLs de acesso:"
	@echo "  Frontend: http://localhost:8080"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Grafana: http://localhost:4000"

logs: ## 📋 Ver logs de todos os servicos
	@echo "📋 Logs de todos os servicos:"
	docker-compose logs -f

logs-master: ## 🔴 Ver logs da base de dados
	@echo "🔴 Logs da base de dados:"
	docker-compose logs -f ualflix_db_master

logs-services: ## 🔧 Ver logs dos servicos principais
	@echo "🔧 Logs dos servicos principais:"
	docker-compose logs -f --tail=50 authentication_service catalog_service streaming_service admin_service

# ================================================================
# COMANDOS DE TESTE
# ================================================================

test-db: ## 🧪 Testar conexão à base de dados
	@echo "🧪 Testando conexão à base de dados..."
	@if docker exec $(MASTER_CONTAINER) psql -U postgres -d ualflix -c "\dt" > /dev/null 2>&1; then \
		echo "✅ Conexão à base de dados OK"; \
		docker exec $(MASTER_CONTAINER) psql -U postgres -d ualflix -c "\dt"; \
	else \
		echo "❌ Erro na conexão à base de dados"; \
	fi

test-connectivity: ## 🌐 Testar conectividade dos servicos
	@echo "🌐 Testando conectividade..."
	@services="8080 9090 4000 5432"; \
	for port in $$services; do \
		if nc -z localhost $$port 2>/dev/null; then \
			echo "✅ Porta $$port: ACESSÍVEL"; \
		else \
			echo "❌ Porta $$port: INACESSÍVEL"; \
		fi; \
	done

# ================================================================
# COMANDOS DE ESCALABILIDADE
# ================================================================

scale-services: ## ⚡ Escalar servicos (2 réplicas cada)
	@echo "⚡ Escalando servicos para 2 réplicas..."
	docker-compose up -d --scale authentication_service=2 --scale catalog_service=2 --scale streaming_service=2
	@echo "✅ Servicos escalados!"
	docker-compose ps

scale-down: ## ⬇️ Reduzir escala (1 réplica cada)
	@echo "⬇️ Reduzindo escala para 1 réplica..."
	docker-compose up -d --scale authentication_service=1 --scale catalog_service=1 --scale streaming_service=1
	@echo "✅ Escala reduzida!"

# ================================================================
# COMANDOS DE MANUTENcÃO
# ================================================================

backup: ## 💾 Fazer backup da base de dados
	@echo "💾 Fazendo backup da base de dados..."
	@mkdir -p backups
	@timestamp=$$(date +%Y%m%d_%H%M%S); \
	echo "Backup Master Database..."; \
	docker exec $(MASTER_CONTAINER) pg_dump -U postgres ualflix > backups/master_backup_$$timestamp.sql; \
	echo "✅ Backup criado em backups/master_backup_$$timestamp.sql"
	@ls -la backups/

clean: ## 🧹 Limpar containers e imagens não utilizadas
	@echo "🧹 Limpando containers e imagens..."
	docker-compose down
	docker system prune -f
	docker image prune -f
	@echo "✅ Limpeza concluída!"

clean-volumes: ## 🗑️ Limpar volumes de dados
	@echo "⚠️ Esta operacão ira apagar todos os dados!"
	@echo "Pressione Ctrl+C para cancelar..."
	@sleep 5
	@echo "🗑️ Limpando volumes..."
	docker-compose down -v
	docker volume prune -f
	@echo "✅ Volumes limpos!"

clean-all: clean clean-volumes ## 💥 Limpeza completa do sistema

# ================================================================
# COMANDOS DE DESENVOLVIMENTO
# ================================================================

dev-setup: ## 🔧 Setup para desenvolvimento
	@echo "🔧 Configurando ambiente de desenvolvimento..."
	$(MAKE) deploy
	@echo "✅ Ambiente de desenvolvimento pronto!"
	@echo ""
	@echo "📝 Para desenvolvimento:"
	@echo "  1. Frontend: http://localhost:8080"
	@echo "  2. Admin (login admin/admin): http://localhost:8080"
	@echo "  3. Métricas: http://localhost:8080 → Tab 'Administracão'"
	@echo "  4. Logs: make logs-services"

dev-rebuild: ## 🔄 Rebuild rapido para desenvolvimento
	@echo "🔄 Rebuild rapido..."
	docker-compose build --no-cache authentication_service catalog_service admin_service
	docker-compose restart authentication_service catalog_service admin_service
	@echo "✅ Rebuild concluído!"

# ================================================================
# COMANDOS DE INFORMAcÃO
# ================================================================

info: ## ℹ️ Informacões do sistema
	@echo "ℹ️ Informacões do Sistema UALFlix"
	@echo "=================================="
	@echo ""
	@echo "📊 Containers:"
	@docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
	@echo ""
	@echo "💾 Volumes:"
	@docker volume ls | grep ualflix || echo "Nenhum volume encontrado"
	@echo ""
	@echo "🌐 Rede:"
	@docker network ls | grep ualflix || echo "Rede não encontrada"
	@echo ""
	@echo "🔗 URLs:"
	@echo "  Frontend:     http://localhost:8080"
	@echo "  Prometheus:   http://localhost:9090"
	@echo "  Grafana:      http://localhost:4000"
	@echo "  RabbitMQ:     http://localhost:15672"

# ================================================================
# COMANDOS RaPIDOS
# ================================================================

quick-start: up ## 🚀 Início rapido

quick-stop: down ## 🛑 Parada rapida

quick-restart: ## 🔄 Restart rapido dos servicos principais
	@echo "🔄 Restart rapido..."
	docker-compose restart authentication_service catalog_service streaming_service admin_service
	@echo "✅ Restart concluído!"

quick-logs: ## 📋 Logs dos servicos principais
	docker-compose logs -f --tail=50 authentication_service catalog_service streaming_service admin_service

# ================================================================
# DEFAULT TARGET
# ================================================================

.DEFAULT_GOAL := help