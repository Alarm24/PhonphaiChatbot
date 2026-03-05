
# Phonphai Chatbot Backend

Python-based microservices that power retrieval-augmented responses for the Phonphai chatbot. Services are orchestrated with Docker Compose and share persistent data volumes.

## Service layout
- `mongo`: document store for chat history and metadata.
- `chroma`: vector store; persisted in `data/chroma_data`.
- `chroma-ui`: community Chroma admin panel on port `3001`.
- `services/retriever`: fetches and re-ranks context; exposes gRPC on port `50051`.
- `services/agent`: orchestrates model calls; depends on `retriever`; gRPC on port `50052`.
- `services/api-gateway`: public HTTP API on `http://localhost:8080`.

## Prerequisites
- Docker Engine 24+ and Docker Compose v2 (`docker compose` CLI).
- Python 3.10+ with `ruff` installed locally for linting/formatting (`pip install ruff`). Containers do not run lint.

## Setup
1) From `backend/`, copy the env template and add your OpenRouter key:
   ```bash
   cp .env.example .env
   # set OPENROUTER_API_KEY=<your key>
   # set LANGCHAIN_API_KEY=<your key>
   ```
2) Start the full stack (detached):
   ```bash
   docker compose up -d
   ```
   - API Gateway: http://localhost:8080
   - Chroma UI:   http://localhost:3001
3) View logs or stop:
   ```bash
   docker compose logs -f
   docker compose down
   ```

## Development
- Code style: enforced by `ruff` (see `pyproject.toml`).
- Lint only: `ruff check .`
- Format + lint-fix: `ruff format . && ruff check --fix .`
- Common workflows are wrapped in the `Makefile` (see below).

## Make targets (from `backend/`)
- `make up` / `make down` – start/stop all services.
- `make restart` – restart running services.
- `make logs [SERVICE=name]` – follow logs (default: all).
- `make ps` – show container status.
- `make lint` – run `ruff check .`.
- `make format` – run `ruff format .`.
- `make lint-fix` – format then fix lint issues.

## Data & persistence
- Mongo data: `data/mongo_data`
- Chroma data: `data/chroma_data`
Volumes are bind-mounted locally; they persist across container restarts. Remove directories to reset stored state.
# Phonphai Chatbot Backend

Python-based microservices that power retrieval-augmented responses for the Phonphai chatbot. Services are orchestrated with Docker Compose and share persistent data volumes.

## Service layout
- `mongo`: document store for chat history and metadata.
- `chroma`: vector store; persisted in `data/chroma_data`.
- `chroma-ui`: community Chroma admin panel on port `3001`.
- `services/retriever`: fetches and re-ranks context; exposes gRPC on port `50051`.
- `services/agent`: orchestrates model calls; depends on `retriever`; gRPC on port `50052`.
- `services/api-gateway`: public HTTP API on `http://localhost:8080`.

## Prerequisites
- Docker Engine 24+ and Docker Compose v2 (`docker compose` CLI).
- Python 3.10+ with `ruff` installed locally for linting/formatting (`pip install ruff`). Containers do not run lint.

## Setup
1) From `backend/`, copy the env template and add your OpenRouter key:
   ```bash
   cp .env.example .env
   # set OPENROUTER_API_KEY=<your key>
   # set LANGCHAIN_API_KEY=<your key>
   ```
2) Start the full stack (detached):
   ```bash
   docker compose up -d
   ```
   - API Gateway: http://localhost:8080
   - Chroma UI:   http://localhost:3001
3) View logs or stop:
   ```bash
   docker compose logs -f
   docker compose down
   ```

## Development
- Code style: enforced by `ruff` (see `pyproject.toml`).
- Lint only: `ruff check .`
- Format + lint-fix: `ruff format . && ruff check --fix .`
- Common workflows are wrapped in the `Makefile` (see below).

## Make targets (from `backend/`)
- `make up` / `make down` – start/stop all services.
- `make restart` – restart running services.
- `make logs [SERVICE=name]` – follow logs (default: all).
- `make ps` – show container status.
- `make lint` – run `ruff check .`.
- `make format` – run `ruff format .`.
- `make lint-fix` – format then fix lint issues.

## Data & persistence
- Mongo data: `data/mongo_data`
- Chroma data: `data/chroma_data`
Volumes are bind-mounted locally; they persist across container restarts. Remove directories to reset stored state.