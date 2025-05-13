# Makefile para gerir o projeto UALFlix
# Iniciar todos os serviços
up:
	docker-compose up -d

# Iniciar todos os serviços no primeiro plano
upf:
	docker-compose up

# Parar todos os serviços
down:
	docker-compose down

# Reconstruir e reiniciar todos os serviços
rebuild:
	docker-compose down --volumes --remove-orphans
	docker-compose build
	docker-compose up -d

# Ver logs de todos os serviços
logs:
	docker-compose logs -f

# Ver logs de um serviço específico
log-%:
	docker-compose logs -f $*

# Ver status dos containers
ps:
	docker-compose ps

# Reiniciar todos os serviços
restart:
	docker-compose restart

# Reiniciar um serviço específico
restart-%:
	docker-compose restart $*

# Escalar um serviço
scale:
	@read -p "Serviço para escalar: " service; \
	read -p "Número de instâncias: " instances; \
	docker-compose up -d --scale $$service=$$instances

# Limpar recursos Docker não utilizados
clean:
	docker system prune -f --volumes

# Construir todos os serviços
build:
	docker-compose build

# Construir um serviço específico
build-%:
	docker-compose build $*

# Executar testes de carga
load-test:
	cd load_testing && python run_load_tests.py

# Fazer backup do banco de dados
backup:
	@timestamp=$$(date +%Y%m%d%H%M%S); \
	mkdir -p backups; \
	docker-compose exec ualflix_db_master pg_dump -U postgres ualflix > backups/ualflix_$$timestamp.sql; \
	echo "Backup criado em backups/ualflix_$$timestamp.sql"

# Restaurar backup do banco de dados
restore-backup:
	@read -p "Arquivo de backup: " backup_file; \
	if [ -f "$$backup_file" ]; then \
		docker-compose exec -T ualflix_db_master psql -U postgres ualflix < $$backup_file; \
		echo "Backup restaurado com sucesso!"; \
	else \
		echo "Arquivo de backup não encontrado!"; \
	fi

# Monitorar métricas do sistema (abre o Grafana no navegador)
monitor:
	@echo "Abrindo dashboard Grafana..."
	@if command -v xdg-open > /dev/null; then \
		xdg-open http://localhost:3000; \
	elif command -v open > /dev/null; then \
		open http://localhost:3000; \
	elif command -v start > /dev/null; then \
		start http://localhost:3000; \
	else \
		echo "Acesse manualmente: http://localhost:3000"; \
# Escalar serviços para alta disponibilidade
scale:
	docker-compose up -d --scale frontend=2 --scale catalog_service=2 --scale streaming_service=2

# Acessar o Prometheus
prometheus:
	@echo "Abrindo Prometheus no navegador..."
	@if command -v xdg-open > /dev/null; then \
		xdg-open http://localhost:9090; \
	elif command -v open > /dev/null; then \
		open http://localhost:9090; \
	else \
		echo "Acesse manualmente: http://localhost:9090"; \
	fi

# Acessar o Grafana
grafana:
	@echo "Abrindo Grafana no navegador..."
	@if command -v xdg-open > /dev/null; then \
		xdg-open http://localhost:3000; \
	elif command -v open > /dev/null; then \
		open http://localhost:3000; \
	else \
		echo "Acesse manualmente: http://localhost:3000"; \
	fi

# Escalar para teste de carga
scale-test:
	docker-compose up -d --scale frontend=3 --scale catalog_service=3 --scale streaming_service=5

# Retornar ao modo normal
scale-down:
	docker-compose up -d --scale frontend=1 --scale catalog_service=1 --scale streaming_service=1
	fi

# Preparar para deploy na cloud
deploy-prep:
	mkdir -p deploy
	cp docker-compose.yml deploy/
	cp -r nginx deploy/
	cp -r monitoring deploy/
	cp db_init.sql deploy/
	cp db_init_replica.sh deploy/
	tar -czvf deploy.tar.gz deploy/
	rm -rf deploy/
	echo "Pacote de deploy criado: deploy.tar.gz"

# Deploy no AWS ECS (simulado)
deploy-aws:
	./scripts/deploy_to_aws.sh

# Deploy no Google Cloud Run (simulado)
deploy-gcp:
	./scripts/deploy_to_gcp.sh

# Deploy no Azure Container Service (simulado)
deploy-azure:
	./scripts/deploy_to_azure.sh

# Inicializar cluster Kubernetes (simulado)
k8s-init:
	./scripts/k8s_init.sh

# Deploy no Kubernetes (simulado)
k8s-deploy:
	kubectl apply -f k8s/

# Verificar status de replicação do banco de dados
db-replication-status:
	docker-compose exec ualflix_db_master psql -U postgres -c "SELECT * FROM pg_stat_replication;"

# Simular falha no servidor master
simulate-master-failure:
	docker-compose stop ualflix_db_master
	echo "Servidor Master parado. O sistema deve continuar funcionando com o replica."

# Restaurar servidor master após simulação
restore-master:
	docker-compose start ualflix_db_master
	echo "Servidor Master restaurado."

# Exibir ajuda
help:
	@echo "Makefile do UALFlix - Comandos disponíveis:"
	@echo ""
	@echo "up                     - Iniciar todos os serviços em background"
	@echo "upf                    - Iniciar todos os serviços em foreground"
	@echo "down                   - Parar todos os serviços"
	@echo "rebuild                - Reconstruir e reiniciar todos os serviços"
	@echo "logs                   - Ver logs de todos os serviços"
	@echo "log-<serviço>          - Ver logs de um serviço específico"
	@echo "ps                     - Ver status dos containers"
	@echo "restart                - Reiniciar todos os serviços"
	@echo "restart-<serviço>      - Reiniciar um serviço específico"
	@echo "scale                  - Escalar um serviço (interativo)"
	@echo "clean                  - Limpar recursos Docker não utilizados"
	@echo "build                  - Construir todos os serviços"
	@echo "build-<serviço>        - Construir um serviço específico"
	@echo "load-test              - Executar testes de carga"
	@echo "backup                 - Fazer backup do banco de dados"
	@echo "restore-backup         - Restaurar backup do banco de dados"
	@echo "monitor                - Abrir dashboard de monitoramento"
	@echo "deploy-prep            - Preparar pacote para deploy na cloud"
	@echo "deploy-aws             - Deploy no AWS ECS (simulado)"
	@echo "deploy-gcp             - Deploy no Google Cloud Run (simulado)"
	@echo "deploy-azure           - Deploy no Azure Container Service (simulado)"
	@echo "k8s-init               - Inicializar cluster Kubernetes (simulado)"
	@echo "k8s-deploy             - Deploy no Kubernetes (simulado)"
	@echo "db-replication-status  - Verificar status de replicação do banco de dados"
	@echo "simulate-master-failure - Simular falha no servidor master"
	@echo "restore-master          - Restaurar servidor master após simulação"
	@echo "help                   - Exibir esta ajuda"

.PHONY: up upf down rebuild logs ps restart clean build load-test backup restore-backup monitor deploy-prep deploy-aws deploy-gcp deploy-azure k8s-init k8s-deploy db-replication-status simulate-master-failure restore-master help