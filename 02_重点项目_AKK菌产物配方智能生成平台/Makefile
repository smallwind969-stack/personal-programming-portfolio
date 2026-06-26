.PHONY: dev test-api lint-web build-web check

dev:
	docker compose up --build

test-api:
	docker compose exec api pytest tests

lint-web:
	docker compose exec web npm run lint

build-web:
	docker compose exec web npm run build

check: test-api lint-web build-web
