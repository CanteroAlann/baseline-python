SHELL := /bin/bash
PWD := $(shell pwd)

IGNORE_RABBITMQ_LOGS ?= true
SERVICES_TO_LOG = $(shell docker compose -f docker-compose.yaml config --services | grep -v "rabbitmq")

up:
	mkdir -p output
	COMPOSE_HTTP_TIMEOUT=300 docker compose -f docker-compose.yaml up --build --remove-orphans --detach
ifeq ($(IGNORE_RABBITMQ_LOGS),true)
	docker compose -f docker-compose.yaml logs --follow $(SERVICES_TO_LOG)
else
	docker compose -f docker-compose.yaml logs --follow
endif

down:
	docker compose -f docker-compose.yaml stop -t 5
	docker compose -f docker-compose.yaml down
.PHONY: down

logs:
	docker compose -f docker-compose.yaml logs
.PHONY: logs

logs-ignore:
	docker compose -f docker-compose.yaml logs --follow $(SERVICES_TO_LOG)
#	docker compose -f docker-compose.yaml logs | grep -ivE "pika.|rabbitmq"
# otra es ignorar todo lo que diga 'pika.' pero pierdo los colores en la consola
.PHONY: logs-ignore

test:
	bash tests/run_all.sh
