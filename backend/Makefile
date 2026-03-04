# Command shims for local development
COMPOSE ?= docker compose
SERVICE ?= 
.PHONY: help up down restart logs ps lint format lint-fix
help:
	@echo "Available targets:"
	@echo "  make up         - start all services (detached)"
	@echo "  make down       - stop and remove services"
	@echo "  make restart    - restart running services"
	@echo "  make logs       - follow logs (SERVICE=name to filter)"
	@echo "  make ps         - show container status"
	@echo "  make lint       - ruff check"
	@echo "  make format     - ruff format"
	@echo "  make lint-fix   - format then lint --fix"
up:
	$(COMPOSE) up -d
down:
	$(COMPOSE) down
restart:
	$(COMPOSE) restart
logs:
	$(COMPOSE) logs -f $(SERVICE)
ps:
	$(COMPOSE) ps
lint:
	ruff check .
format:
	ruff format .
lint-fix:
	ruff format .
	ruff check --fix .