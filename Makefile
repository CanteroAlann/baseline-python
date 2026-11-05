SHELL := /bin/bash
.DEFAULT_GOAL := up
BACKEND_COMPOSE = docker compose -f docker-compose.yaml
CLIENTS_COMPOSE = docker compose -f docker-compose.clients.yaml

IGNORE_RABBITMQ_LOGS ?= true
WORKER_LOGS ?= false
export WORKER_LOGS
SERVICES_TO_LOG = $(shell $(BACKEND_COMPOSE) config --services | grep -v "rabbitmq")

backend:
	$(BACKEND_COMPOSE) up --build --remove-orphans --detach --wait

clients:
	mkdir -p output
	$(CLIENTS_COMPOSE) up --build --remove-orphans --force-recreate

up: backend
	$(MAKE) clients

down:
	$(CLIENTS_COMPOSE) down --remove-orphans --timeout 5
	$(BACKEND_COMPOSE) down --remove-orphans --timeout 5

logs:
ifeq ($(IGNORE_RABBITMQ_LOGS),true)
	$(BACKEND_COMPOSE) logs $(SERVICES_TO_LOG)
else
	$(BACKEND_COMPOSE) logs
endif
	$(CLIENTS_COMPOSE) logs

logs-ignore:
	$(BACKEND_COMPOSE) logs --follow $(SERVICES_TO_LOG)

test:
	bash tests/run_all.sh

.PHONY: backend clients up down logs logs-ignore test
