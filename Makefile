# Makefile para UALFlix - Kubernetes com 3 Nós

up:
	docker-compose up -d

down:
	docker-compose down

ps:
	docker-compose ps

logs:
	docker-compose logs -f

restart:
	docker-compose restart

build:
	docker-compose build

stop:
	docker-compose stop

start:
	docker-compose start

pull:
	docker-compose pull

rm:
	docker-compose rm -f