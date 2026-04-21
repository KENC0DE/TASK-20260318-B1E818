# Offline Retail Checkout & Entrepreneurship Project Incubation Operation Middle Platform API

## Project Status
Module 1 (Auth & User), Module 2 (Product), and Module 3 (Cart & Promotion) are implemented and verified.

Completed in this module:
- JWT login
- User creation (admin only)
- User profile retrieval
- User role update (admin only)
- Password hashing
- Account lockout policy
- Field-level encryption for sensitive user fields
- Audit log writes for critical auth events
- Product create endpoint (`POST /products`)
- Product update endpoint (`PUT /products/{product_id}`)
- Product search endpoint (`GET /products/search`) by barcode, pinyin prefix, and internal code
- Promotion rule CRUD (`POST/GET/PUT/DELETE /promotions`)
- Cart session create (`POST /carts`)
- Cart item add/update/remove (`POST /carts/{cart_id}/items`, `PUT /carts/{cart_id}/items/{item_id}`, `DELETE /carts/{cart_id}/items/{item_id}`)
- Cart projection with promotion evaluation (`GET /carts/{cart_id}`)

## Tech Stack
- Backend: FastAPI
- ORM/Transactions: SQLAlchemy
- Database: PostgreSQL (runtime), SQLite (tests)
- Containerization: Docker + Docker Compose
- Testing: Pytest (unit + API tests)

## Repository Structure
- `app/` backend application package
  - `api/`
  - `core/`
  - `db/`
  - `models/`
  - `schemas/`
  - `services/`
  - `workers/`
- `unit_tests/` unit test suite
- `API_tests/` API test suite
- `docs/`
  - `design.md`
  - `api-spec.md`
- `docker-compose.yml`
- `run_tests.sh`
- `.env.example`
- `requirements.txt`

## Prerequisites
- Docker Engine (with Compose plugin)
- POSIX shell (`sh`)

## Environment Setup
1. Copy environment template:
```bash
cp .env.example .env
```
2. Adjust values in `.env` if needed.

## Start Services
```bash
docker compose up --build
```

Health check endpoint:
- `GET /health`

Stop services:
```bash
docker compose down
```

Stop and remove volumes:
```bash
docker compose down -v
```

## Run Tests (Docker-Only)
Use the project test script so all tests run inside containers:
```bash
TEARDOWN=1 sh run_tests.sh
```

Behavior:
- Builds and starts services
- Waits for DB health
- Runs `unit_tests/` in the `api` container
- Runs `API_tests/` in the `api` container

## Implemented API Endpoints
- `POST /auth/login`
- `POST /auth/users`
- `GET /auth/users/{user_id}`
- `PUT /auth/users/{user_id}/role`
- `GET /products/search`
- `POST /products`
- `PUT /products/{product_id}`
- `POST /promotions`
- `GET /promotions`
- `PUT /promotions/{rule_id}`
- `DELETE /promotions/{rule_id}`
- `POST /carts`
- `GET /carts/{cart_id}`
- `POST /carts/{cart_id}/items`
- `PUT /carts/{cart_id}/items/{item_id}`
- `DELETE /carts/{cart_id}/items/{item_id}`

Full contract details are in `docs/api-spec.md`.

## Notes
A deprecation warning from `python-jose` (`datetime.utcnow()`) may appear in test output on Python 3.12. This is a third-party warning and does not fail tests.