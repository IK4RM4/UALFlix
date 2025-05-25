# UALFlix Makefile
.PHONY: help build up down restart logs clean status rebuild

help:
	@echo "UALFlix - Comandos Disponiveis:"
	@echo ""
	@echo "build     - Construir todos os containers"
	@echo "up        - Iniciar todos os servicos"
	@echo "down      - Parar todos os servicos"
	@echo "restart   - Reiniciar todos os servicos"
	@echo "rebuild   - Reconstruir e reiniciar"
	@echo "logs      - Ver logs de todos os servicos"
	@echo "status    - Ver status dos containers"
	@echo "clean     - Limpar containers e volumes"
	@echo ""

build:
	@echo "Construindo containers..."
	docker-compose build

up:
	@echo "Iniciando servicos..."
	docker-compose up -d
	@echo "Servicos iniciados!"
	@echo "Acesso: http://localhost:8080"

down:
	@echo "Parando servicos..."
	docker-compose down
	@echo "Servicos parados!"

restart: down up

rebuild:
	@echo "Reconstruindo sistema..."
	docker-compose down
	docker-compose build
	docker-compose up -d
	@echo "Sistema reconstruido!"
	@echo "Acesso: http://localhost:8080"

logs:
	@echo "Mostrando logs..."
	docker-compose logs -f

status:
	@echo "Status dos containers:"
	docker-compose ps

clean:
	@echo "Limpando containers e volumes..."
	docker-compose down -v
	docker system prune -f
	@echo "Limpeza concluida!"

rebuild-admin:
	@echo "Rebuilding Admin Service..."
	docker-compose build admin_service
	docker-compose restart admin_service

rebuild-frontend:
	@echo "Rebuilding Frontend..."
	docker-compose build frontend
	docker-compose restart frontend

quick-fix:
	@echo "Aplicando fixes rapidos..."
	docker-compose restart nginx
	docker-compose restart admin_service
	docker-compose restart frontend
	@echo "Fixes aplicados!"