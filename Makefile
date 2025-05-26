<<<<<<< Updated upstream
# Makefile para gerir o projeto UALFlix

up:
	docker-compose up --build

down:
	docker-compose down

rebuild:
	docker-compose down --volumes --remove-orphans
	docker-compose up --build

logs:
	docker-compose logs -f

ps:
	docker-compose ps

restart:
	docker-compose restart

clean:
	docker system prune -f --volumes

build:
	docker-compose build
=======
# ================================================================
# UALFlix Makefile - Sistema com Replicação Master-Slave
# FUNCIONALIDADE 5: Estratégias de Replicação de Dados
# ================================================================

.PHONY: help build up down restart logs clean status deploy test-replication
.PHONY: build-master build-slave build-manager build-services
.PHONY: up-database up-services up-monitoring up-frontend
.PHONY: logs-master logs-slave logs-manager logs-services
.PHONY: backup restore clean-volumes clean-all
.PHONY: health check-replication test-performance scale-services

# ================================================================
# CONFIGURAÇÕES PRINCIPAIS
# ================================================================

PROJECT_NAME = ualflix
COMPOSE_FILE = docker-compose.yml
MASTER_CONTAINER = ualflix_db_master
SLAVE_CONTAINER = ualflix_db_slave
MANAGER_CONTAINER = ualflix_db_manager

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
	@echo "$(CYAN)🎬 UALFlix - Sistema de Streaming com Replicação Master-Slave$(NC)"
	@echo "$(CYAN)================================================================$(NC)"
	@echo ""
	@echo "$(GREEN)📋 COMANDOS PRINCIPAIS:$(NC)"
	@echo "  $(YELLOW)make help$(NC)              - Mostrar esta ajuda"
	@echo "  $(YELLOW)make deploy$(NC)            - Deploy completo do sistema"
	@echo "  $(YELLOW)make build$(NC)             - Construir todos os containers"
	@echo "  $(YELLOW)make up$(NC)                - Iniciar todos os serviços"
	@echo "  $(YELLOW)make down$(NC)              - Parar todos os serviços"
	@echo "  $(YELLOW)make restart$(NC)           - Reiniciar todos os serviços"
	@echo "  $(YELLOW)make status$(NC)            - Ver status dos containers"
	@echo ""
	@echo "$(GREEN)🗄️ COMANDOS DE DATABASE:$(NC)"
	@echo "  $(YELLOW)make up-database$(NC)       - Iniciar apenas Master + Slave"
	@echo "  $(YELLOW)make build-master$(NC)      - Build do Master Database"
	@echo "  $(YELLOW)make build-slave$(NC)       - Build do Slave Database"
	@echo "  $(YELLOW)make build-manager$(NC)     - Build do Database Manager"
	@echo "  $(YELLOW)make check-replication$(NC) - Verificar status de replicação"
	@echo "  $(YELLOW)make test-replication$(NC)  - Testar replicação de dados"
	@echo ""
	@echo "$(GREEN)📊 COMANDOS DE MONITORIZAÇÃO:$(NC)"
	@echo "  $(YELLOW)make health$(NC)            - Health check de todos os serviços"
	@echo "  $(YELLOW)make logs$(NC)              - Ver logs de todos os serviços"
	@echo "  $(YELLOW)make logs-master$(NC)       - Ver logs do Master DB"
	@echo "  $(YELLOW)make logs-slave$(NC)        - Ver logs do Slave DB"
	@echo "  $(YELLOW)make logs-manager$(NC)      - Ver logs do DB Manager"
	@echo "  $(YELLOW)make test-performance$(NC)  - Testar performance do sistema"
	@echo ""
	@echo "$(GREEN)🔧 COMANDOS DE MANUTENÇÃO:$(NC)"
	@echo "  $(YELLOW)make clean$(NC)             - Limpar containers e imagens"
	@echo "  $(YELLOW)make clean-volumes$(NC)     - Limpar volumes de dados"
	@echo "  $(YELLOW)make clean-all$(NC)         - Limpeza completa do sistema"
	@echo "  $(YELLOW)make backup$(NC)            - Fazer backup das bases de dados"
	@echo "  $(YELLOW)make restore$(NC)           - Restaurar backup das bases de dados"
	@echo ""
	@echo "$(GREEN)⚡ COMANDOS DE ESCALABILIDADE:$(NC)"
	@echo "  $(YELLOW)make scale-services$(NC)    - Escalar serviços (2 réplicas cada)"
	@echo "  $(YELLOW)make scale-down$(NC)        - Reduzir escala (1 réplica cada)"
	@echo ""
	@echo "$(GREEN)🌐 URLs DE ACESSO:$(NC)"
	@echo "  $(CYAN)Frontend:$(NC)        http://localhost:8080"
	@echo "  $(CYAN)Prometheus:$(NC)      http://localhost:9090"
	@echo "  $(CYAN)Grafana:$(NC)         http://localhost:4000 (admin/admin)"
	@echo "  $(CYAN)RabbitMQ:$(NC)        http://localhost:15672 (ualflix/ualflix_password)"
	@echo "  $(CYAN)DB Manager:$(NC)      http://localhost:5005"
	@echo "  $(CYAN)Master DB:$(NC)       localhost:5432"
	@echo "  $(CYAN)Slave DB:$(NC)        localhost:5433"
	@echo ""

# ================================================================
# COMANDOS DE BUILD
# ================================================================

build: ## 🏗️ Construir todos os containers
	@echo "$(BLUE)🏗️ Construindo todos os containers...$(NC)"
	docker-compose build --parallel
	@echo "$(GREEN)✅ Build concluído!$(NC)"

build-services: ## 🔧 Construir apenas serviços principais
	@echo "$(BLUE)🔧 Construindo serviços principais...$(NC)"
	docker-compose build authentication_service catalog_service streaming_service admin_service
	@echo "$(GREEN)✅ Serviços construídos!$(NC)"

build-manager: ## 🗄️ Construir Database Manager
	@echo "$(BLUE)🗄️ Construindo Database Manager...$(NC)"
	docker-compose build database_manager
	@echo "$(GREEN)✅ Database Manager construído!$(NC)"

build-master: ## 🔴 Preparar Master Database
	@echo "$(BLUE)🔴 Preparando Master Database...$(NC)"
	@if [ ! -f "database/init_master.sql" ]; then \
		echo "$(RED)❌ Arquivo database/init_master.sql não encontrado!$(NC)"; \
		echo "$(YELLOW)Execute: make deploy$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✅ Master Database preparado!$(NC)"

build-slave: ## 🟢 Preparar Slave Database
	@echo "$(BLUE)🟢 Preparando Slave Database...$(NC)"
	@if [ ! -f "database/postgresql_slave.conf" ]; then \
		echo "$(RED)❌ Configurações do Slave não encontradas!$(NC)"; \
		echo "$(YELLOW)Execute: make deploy$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✅ Slave Database preparado!$(NC)"

# ================================================================
# COMANDOS DE EXECUÇÃO
# ================================================================

deploy: ## 🚀 Deploy completo do sistema Master-Slave
	@echo "$(PURPLE)🚀 Iniciando deploy completo do UALFlix...$(NC)"
	@if [ ! -f "scripts/deploy_replication.sh" ]; then \
		echo "$(RED)❌ Script de deploy não encontrado!$(NC)"; \
		exit 1; \
	fi
	chmod +x scripts/deploy_replication.sh
	./scripts/deploy_replication.sh
	@echo "$(GREEN)✅ Deploy concluído!$(NC)"
	@echo ""
	@echo "$(CYAN)🌐 Sistema disponível em:$(NC)"
	@echo "  Frontend: http://localhost:8080"
	@echo "  DB Manager: http://localhost:5005"

up: up-database up-services up-monitoring up-frontend ## ⬆️ Iniciar todos os serviços

up-database: ## 🗄️ Iniciar apenas bases de dados
	@echo "$(BLUE)🗄️ Iniciando bases de dados...$(NC)"
	docker-compose up -d ualflix_db_master
	@echo "$(YELLOW)⏳ Aguardando Master estar pronto...$(NC)"
	@timeout=60; while [ $$timeout -gt 0 ]; do \
		if docker exec $(MASTER_CONTAINER) pg_isready -U postgres -d ualflix > /dev/null 2>&1; then \
			echo "$(GREEN)✅ Master está pronto!$(NC)"; \
			break; \
		fi; \
		echo "⏳ Aguardando Master... ($$timeout segundos restantes)"; \
		sleep 2; \
		timeout=$$((timeout - 2)); \
	done
	docker-compose up -d ualflix_db_slave
	@echo "$(YELLOW)⏳ Aguardando Slave estar pronto...$(NC)"
	@timeout=90; while [ $$timeout -gt 0 ]; do \
		if docker exec $(SLAVE_CONTAINER) pg_isready -U postgres > /dev/null 2>&1; then \
			echo "$(GREEN)✅ Slave está pronto!$(NC)"; \
			break; \
		fi; \
		echo "⏳ Aguardando Slave... ($$timeout segundos restantes)"; \
		sleep 3; \
		timeout=$$((timeout - 3)); \
	done
	docker-compose up -d database_manager
	@echo "$(GREEN)✅ Bases de dados iniciadas!$(NC)"

up-services: ## 🔧 Iniciar serviços principais
	@echo "$(BLUE)🔧 Iniciando serviços principais...$(NC)"
	docker-compose up -d queue_service
	sleep 3
	docker-compose up -d authentication_service catalog_service
	sleep 3
	docker-compose up -d streaming_service video_processor admin_service
	@echo "$(GREEN)✅ Serviços principais iniciados!$(NC)"

up-monitoring: ## 📊 Iniciar monitoring (Prometheus, Grafana)
	@echo "$(BLUE)📊 Iniciando serviços de monitoring...$(NC)"
	docker-compose up -d prometheus grafana
	@echo "$(GREEN)✅ Monitoring iniciado!$(NC)"

up-frontend: ## 🌐 Iniciar frontend e proxy
	@echo "$(BLUE)🌐 Iniciando frontend...$(NC)"
	docker-compose up -d frontend nginx
	@echo "$(GREEN)✅ Frontend iniciado!$(NC)"

down: ## ⬇️ Parar todos os serviços
	@echo "$(BLUE)⬇️ Parando todos os serviços...$(NC)"
	docker-compose down
	@echo "$(GREEN)✅ Todos os serviços parados!$(NC)"

restart: down up ## 🔄 Reiniciar todos os serviços

# ================================================================
# COMANDOS DE MONITORIZAÇÃO
# ================================================================

status: ## 📊 Ver status dos containers
	@echo "$(BLUE)📊 Status dos containers:$(NC)"
	@echo ""
	docker-compose ps
	@echo ""
	@echo "$(CYAN)🗄️ Status das bases de dados:$(NC)"
	@if docker exec $(MASTER_CONTAINER) pg_isready -U postgres -d ualflix > /dev/null 2>&1; then \
		echo "$(GREEN)✅ Master Database: ONLINE (porta 5432)$(NC)"; \
	else \
		echo "$(RED)❌ Master Database: OFFLINE$(NC)"; \
	fi
	@if docker exec $(SLAVE_CONTAINER) pg_isready -U postgres > /dev/null 2>&1; then \
		echo "$(GREEN)✅ Slave Database: ONLINE (porta 5433)$(NC)"; \
	else \
		echo "$(RED)❌ Slave Database: OFFLINE$(NC)"; \
	fi
	@if curl -s http://localhost:5005/health > /dev/null 2>&1; then \
		echo "$(GREEN)✅ Database Manager: ONLINE (porta 5005)$(NC)"; \
	else \
		echo "$(RED)❌ Database Manager: OFFLINE$(NC)"; \
	fi

health: ## 🏥 Health check de todos os serviços
	@echo "$(BLUE)🏥 Verificando saúde dos serviços...$(NC)"
	@echo ""
	@services="authentication_service:8000 catalog_service:8000 streaming_service:8001 admin_service:8002 database_manager:5000"; \
	for service in $$services; do \
		name=$$(echo $$service | cut -d: -f1); \
		port=$$(echo $$service | cut -d: -f2); \
		if curl -s http://localhost:$$port/health > /dev/null 2>&1; then \
			echo "$(GREEN)✅ $$name: HEALTHY$(NC)"; \
		else \
			echo "$(RED)❌ $$name: UNHEALTHY$(NC)"; \
		fi; \
	done
	@echo ""
	@echo "$(CYAN)🌐 URLs de acesso:$(NC)"
	@echo "  Frontend: http://localhost:8080"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Grafana: http://localhost:4000"

logs: ## 📋 Ver logs de todos os serviços
	@echo "$(BLUE)📋 Logs de todos os serviços:$(NC)"
	docker-compose logs -f

logs-master: ## 🔴 Ver logs do Master Database
	@echo "$(BLUE)🔴 Logs do Master Database:$(NC)"
	docker-compose logs -f ualflix_db_master

logs-slave: ## 🟢 Ver logs do Slave Database
	@echo "$(BLUE)🟢 Logs do Slave Database:$(NC)"
	docker-compose logs -f ualflix_db_slave

logs-manager: ## 🗄️ Ver logs do Database Manager
	@echo "$(BLUE)🗄️ Logs do Database Manager:$(NC)"
	docker-compose logs -f database_manager

logs-services: ## 🔧 Ver logs dos serviços principais
	@echo "$(BLUE)🔧 Logs dos serviços principais:$(NC)"
	docker-compose logs -f authentication_service catalog_service streaming_service admin_service

# ================================================================
# COMANDOS DE REPLICAÇÃO
# ================================================================

check-replication: ## 🔍 Verificar status de replicação
	@echo "$(BLUE)🔍 Verificando status de replicação...$(NC)"
	@echo ""
	@echo "$(CYAN)📊 Status via Database Manager:$(NC)"
	@if curl -s http://localhost:5005/status > /dev/null 2>&1; then \
		curl -s http://localhost:5005/status | python3 -m json.tool; \
	else \
		echo "$(RED)❌ Database Manager não está acessível$(NC)"; \
	fi
	@echo ""
	@echo "$(CYAN)🔴 Status do Master:$(NC)"
	@docker exec $(MASTER_CONTAINER) psql -U postgres -d ualflix -c "\
		SELECT \
			application_name, \
			client_addr, \
			state, \
			sync_state \
		FROM pg_stat_replication;" 2>/dev/null || echo "$(RED)❌ Erro ao consultar Master$(NC)"
	@echo ""
	@echo "$(CYAN)🟢 Status do Slave:$(NC)"
	@docker exec $(SLAVE_CONTAINER) psql -U postgres -d ualflix -c "\
		SELECT \
			pg_is_in_recovery() as is_slave, \
			CASE WHEN pg_is_in_recovery() THEN 'Slave Mode' ELSE 'Master Mode' END as mode;" 2>/dev/null || echo "$(RED)❌ Erro ao consultar Slave$(NC)"

test-replication: ## 🧪 Testar replicação de dados
	@echo "$(BLUE)🧪 Testando replicação de dados...$(NC)"
	@if [ -f "scripts/test_replication.py" ]; then \
		python3 scripts/test_replication.py; \
	else \
		echo "$(RED)❌ Script de teste não encontrado$(NC)"; \
		echo "$(YELLOW)Executando teste simples...$(NC)"; \
		$(MAKE) test-replication-simple; \
	fi

test-replication-simple: ## 🧪 Teste simples de replicação
	@echo "$(YELLOW)🧪 Teste simples de replicação...$(NC)"
	@test_data="Test data $$(date +%s)"; \
	echo "Inserindo dados no Master: $$test_data"; \
	docker exec $(MASTER_CONTAINER) psql -U postgres -d ualflix -c "\
		INSERT INTO replication_test (test_data) VALUES ('$$test_data');" > /dev/null; \
	echo "$(YELLOW)⏳ Aguardando replicação (3 segundos)...$(NC)"; \
	sleep 3; \
	echo "Verificando no Slave:"; \
	if docker exec $(SLAVE_CONTAINER) psql -U postgres -d ualflix -c "\
		SELECT test_data FROM replication_test WHERE test_data = '$$test_data';" | grep -q "$$test_data"; then \
		echo "$(GREEN)✅ Replicação funcionando!$(NC)"; \
	else \
		echo "$(RED)❌ Replicação com problemas$(NC)"; \
	fi

test-performance: ## ⚡ Testar performance do sistema
	@echo "$(BLUE)⚡ Testando performance do sistema...$(NC)"
	@if [ -f "load_testing/run_load_tests.py" ]; then \
		echo "$(YELLOW)Executando testes de carga...$(NC)"; \
		cd load_testing && python3 run_load_tests.py -u 10 -d 30; \
	else \
		echo "$(YELLOW)Script de teste de carga não encontrado$(NC)"; \
		echo "$(CYAN)Executando teste básico de conectividade...$(NC)"; \
		$(MAKE) test-connectivity; \
	fi

test-connectivity: ## 🌐 Testar conectividade dos serviços
	@echo "$(BLUE)🌐 Testando conectividade...$(NC)"
	@services="8080 9090 4000 5005 5432 5433"; \
	for port in $$services; do \
		if nc -z localhost $$port 2>/dev/null; then \
			echo "$(GREEN)✅ Porta $$port: ACESSÍVEL$(NC)"; \
		else \
			echo "$(RED)❌ Porta $$port: INACESSÍVEL$(NC)"; \
		fi; \
	done

# ================================================================
# COMANDOS DE ESCALABILIDADE
# ================================================================

scale-services: ## ⚡ Escalar serviços (2 réplicas cada)
	@echo "$(BLUE)⚡ Escalando serviços para 2 réplicas...$(NC)"
	docker-compose up -d --scale authentication_service=2 --scale catalog_service=2 --scale streaming_service=2
	@echo "$(GREEN)✅ Serviços escalados!$(NC)"
	docker-compose ps

scale-down: ## ⬇️ Reduzir escala (1 réplica cada)
	@echo "$(BLUE)⬇️ Reduzindo escala para 1 réplica...$(NC)"
	docker-compose up -d --scale authentication_service=1 --scale catalog_service=1 --scale streaming_service=1
	@echo "$(GREEN)✅ Escala reduzida!$(NC)"

# ================================================================
# COMANDOS DE MANUTENÇÃO
# ================================================================

backup: ## 💾 Fazer backup das bases de dados
	@echo "$(BLUE)💾 Fazendo backup das bases de dados...$(NC)"
	@mkdir -p backups
	@timestamp=$$(date +%Y%m%d_%H%M%S); \
	echo "Backup Master Database..."; \
	docker exec $(MASTER_CONTAINER) pg_dump -U postgres ualflix > backups/master_backup_$$timestamp.sql; \
	echo "Backup Slave Database..."; \
	docker exec $(SLAVE_CONTAINER) pg_dump -U postgres ualflix > backups/slave_backup_$$timestamp.sql; \
	echo "$(GREEN)✅ Backups criados em backups/$(NC)"
	@ls -la backups/

restore: ## 🔄 Restaurar backup das bases de dados
	@echo "$(BLUE)🔄 Restaurar backup...$(NC)"
	@if [ ! -d "backups" ]; then \
		echo "$(RED)❌ Diretório backups/ não encontrado$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Backups disponíveis:$(NC)"
	@ls -la backups/
	@echo "$(RED)⚠️ Esta operação irá sobrescrever os dados atuais!$(NC)"
	@echo "$(YELLOW)Execute manualmente: docker exec $(MASTER_CONTAINER) psql -U postgres ualflix < backups/master_backup_YYYYMMDD_HHMMSS.sql$(NC)"

clean: ## 🧹 Limpar containers e imagens não utilizadas
	@echo "$(BLUE)🧹 Limpando containers e imagens...$(NC)"
	docker-compose down
	docker system prune -f
	docker image prune -f
	@echo "$(GREEN)✅ Limpeza concluída!$(NC)"

clean-volumes: ## 🗑️ Limpar volumes de dados
	@echo "$(RED)⚠️ Esta operação irá apagar todos os dados!$(NC)"
	@echo "$(YELLOW)Pressione Ctrl+C para cancelar...$(NC)"
	@sleep 5
	@echo "$(BLUE)🗑️ Limpando volumes...$(NC)"
	docker-compose down -v
	docker volume prune -f
	@echo "$(GREEN)✅ Volumes limpos!$(NC)"

clean-all: clean clean-volumes ## 💥 Limpeza completa do sistema

# ================================================================
# COMANDOS DE DESENVOLVIMENTO
# ================================================================

dev-setup: ## 🔧 Setup para desenvolvimento
	@echo "$(BLUE)🔧 Configurando ambiente de desenvolvimento...$(NC)"
	$(MAKE) deploy
	@echo "$(GREEN)✅ Ambiente de desenvolvimento pronto!$(NC)"
	@echo ""
	@echo "$(CYAN)📝 Para desenvolvimento:$(NC)"
	@echo "  1. Frontend: http://localhost:8080"
	@echo "  2. Admin (login admin/admin): http://localhost:8080"
	@echo "  3. Métricas: http://localhost:5005/status"
	@echo "  4. Logs: make logs-services"

dev-rebuild: ## 🔄 Rebuild rápido para desenvolvimento
	@echo "$(BLUE)🔄 Rebuild rápido...$(NC)"
	docker-compose build --no-cache authentication_service catalog_service admin_service
	docker-compose restart authentication_service catalog_service admin_service
	@echo "$(GREEN)✅ Rebuild concluído!$(NC)"

# ================================================================
# COMANDOS DE INFORMAÇÃO
# ================================================================

info: ## ℹ️ Informações do sistema
	@echo "$(CYAN)ℹ️ Informações do Sistema UALFlix$(NC)"
	@echo "=================================="
	@echo ""
	@echo "$(GREEN)📊 Containers:$(NC)"
	@docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
	@echo ""
	@echo "$(GREEN)💾 Volumes:$(NC)"
	@docker volume ls | grep ualflix || echo "Nenhum volume encontrado"
	@echo ""
	@echo "$(GREEN)🌐 Rede:$(NC)"
	@docker network ls | grep ualflix || echo "Rede não encontrada"
	@echo ""
	@echo "$(GREEN)🔗 URLs:$(NC)"
	@echo "  Frontend:     http://localhost:8080"
	@echo "  DB Manager:   http://localhost:5005"
	@echo "  Prometheus:   http://localhost:9090"
	@echo "  Grafana:      http://localhost:4000"
	@echo "  RabbitMQ:     http://localhost:15672"

# ================================================================
# COMANDOS RÁPIDOS
# ================================================================

quick-start: deploy ## 🚀 Início rápido (alias para deploy)

quick-stop: down ## 🛑 Parada rápida (alias para down)

quick-restart: ## 🔄 Restart rápido dos serviços principais
	@echo "$(BLUE)🔄 Restart rápido...$(NC)"
	docker-compose restart authentication_service catalog_service streaming_service admin_service
	@echo "$(GREEN)✅ Restart concluído!$(NC)"

quick-logs: ## 📋 Logs dos serviços principais
	docker-compose logs -f --tail=50 authentication_service catalog_service streaming_service admin_service

# ================================================================
# DEFAULT TARGET
# ================================================================

.DEFAULT_GOAL := help
>>>>>>> Stashed changes
