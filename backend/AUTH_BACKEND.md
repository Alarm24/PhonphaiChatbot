# Auth User-Data Backend

The api-gateway stores authentication user accounts (username, password hash, role, staff_id) in a swappable backend. Pick the backend at deploy time via environment variables — no code changes needed.

The two supported backends today:
- **`mongo`** — default, used during development and for the demo. Lives in the same MongoDB instance as the rest of the stack (`rag_db.users`).
- **`postgres`** — recommended for company production deployments. The api-gateway creates and manages its own `auth_users` table.

> Other data stores in the system are unaffected by this setting. Tickets stay in their own Postgres (agent service), and file metadata for the knowledge base stays in MongoDB (retriever service). This document is only about the auth/user backend.

---

## Configuration

All configuration is via environment variables (read by `pydantic-settings` in `services/api-gateway/config.py`). Set them either in your shell, in `backend/.env`, or in the `api-gateway` block of `docker-compose.yml`.

| Variable | Required when | Default | Description |
|---|---|---|---|
| `USER_DB_BACKEND` | always | `mongo` | Which backend to use. One of `mongo`, `postgres`. |
| `MONGO_URI` | `USER_DB_BACKEND=mongo` | `mongodb://mongo:27017` | Connection URI for the Mongo instance. |
| `MONGO_DB` | `USER_DB_BACKEND=mongo` | `rag_db` | Database name; `users` collection is created inside it. |
| `POSTGRES_USER_DSN` | `USER_DB_BACKEND=postgres` | _(empty)_ | Postgres connection string, e.g. `postgresql://user:pass@host:5432/auth_db`. |
| `INITIAL_ADMIN_USERNAME` / `INITIAL_ADMIN_PASSWORD` | optional | _(empty)_ | If set and no admin exists yet, seed one on first boot. Works for either backend. |
| `INITIAL_USER_USERNAME` / `INITIAL_USER_PASSWORD` / `INITIAL_USER_STAFF_ID` | optional | _(empty / 0)_ | Seed a regular user on first boot. Works for either backend. |
| `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRES_HOURS` | always | see `config.py` | JWT signing — backend-agnostic. |

Selecting an unsupported backend (e.g. `USER_DB_BACKEND=mysql`) makes the api-gateway fail fast on startup with a clear `ValueError` from `db.make_user_store`.

---

## Option A — MongoDB (default)

Keeps the demo configuration working as-is. The Mongo container in `docker-compose.yml` already runs on the same network and the api-gateway connects on boot.

```env
USER_DB_BACKEND=mongo
MONGO_URI=mongodb://mongo:27017
MONGO_DB=rag_db
```

On first start, `MongoUserStore.__init__` creates a unique index on `username`. Nothing else to do.

---

## Option B — Postgres (recommended for company production)

### 1. Provision a database

Use whatever Postgres your company already runs (managed RDS / Cloud SQL / on-prem / a sidecar container). The api-gateway needs:
- A reachable Postgres **13 or newer** (required for `gen_random_uuid()` from the `pgcrypto` extension).
- A database the connecting role can write to.
- A role that can either install the `pgcrypto` extension or where `pgcrypto` is already installed.

### 2. Apply the schema

You have two choices.

**Self-managed (zero-touch):** the api-gateway runs the schema on boot via `PostgresUserStore.__init__`. Every statement is `IF NOT EXISTS`, so it's idempotent — restart-safe and re-run-safe. Your DBA only needs to grant the role permission to create extensions and tables. This is the simplest path.

**Manually managed (recommended for restricted environments):** if your DBA owns the schema, run the migration once before the api-gateway starts:

```bash
psql "$POSTGRES_USER_DSN" -f services/api-gateway/db/migrations/postgres_users.sql
```

The standalone migration file is in `services/api-gateway/db/migrations/postgres_users.sql`. Once the table exists, the `IF NOT EXISTS` calls inside the api-gateway become no-ops.

The schema (the same in both modes):

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS auth_users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username      TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role          TEXT NOT NULL CHECK (role IN ('admin', 'user')),
  staff_id      INTEGER,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS auth_users_username_uniq ON auth_users (username);
```

The table is named `auth_users` (not `users`) so it does not collide with whatever existing user tables your company already has in the same database.

### 3. Configure the api-gateway

In `backend/.env` (or your deployment's secret store):

```env
USER_DB_BACKEND=postgres
POSTGRES_USER_DSN=postgresql://app_user:strongpass@db.internal:5432/auth_db
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=change-me
```

Restart the api-gateway. On boot it will:
1. Open a connection pool against `POSTGRES_USER_DSN`.
2. Run the idempotent schema (no-op if you already migrated by hand).
3. Seed the initial admin if no admin row exists yet.
4. Begin serving `POST /api/v1/auth/login` etc. against Postgres.

### 4. Verify

```bash
# 1. Login should issue a JWT.
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"change-me"}'

# 2. The admin row should exist in Postgres, NOT in Mongo.
psql "$POSTGRES_USER_DSN" -c "SELECT username, role FROM auth_users;"
```

---

## Switching between backends

The two stores are independent — a user that exists in Mongo does **not** exist in Postgres and vice versa. There is no automatic data sync. If you need to migrate users from one backend to the other, dump from the source, transform, and `INSERT` into the target. Password hashes (bcrypt) are portable and do not need to be regenerated.

To roll back from Postgres to Mongo, set `USER_DB_BACKEND=mongo` and restart. The Postgres rows are untouched but unused.

---

## Adding a new backend

If your company uses a database that isn't supported (MSSQL, MySQL, an internal HTTP service, LDAP, etc.):

1. Implement `db.AbstractUserStore` (see `services/api-gateway/db/base.py`) — four methods: `find_by_username`, `find_by_id`, `admin_exists`, `create_user`.
2. Have it return `UserRecord` dicts keyed by `user_id` (string), not by your backend's native id.
3. Add a branch in `db.make_user_store` (`services/api-gateway/db/__init__.py`) that constructs your store when `USER_DB_BACKEND` matches your label.
4. Add any required env vars to `config.py`.
5. Add the same env vars to the `api-gateway` block of `docker-compose.yml`.

The rest of the api-gateway (login flow, JWT issuance, role checks, bootstrap) does not need to change — it only talks to `AbstractUserStore`.

---

## Files involved

| Path | Purpose |
|---|---|
| `services/api-gateway/db/base.py` | `AbstractUserStore` interface + `UserRecord` shape. |
| `services/api-gateway/db/mongo.py` | `MongoUserStore` implementation. |
| `services/api-gateway/db/postgres.py` | `PostgresUserStore` implementation. |
| `services/api-gateway/db/__init__.py` | `make_user_store(settings)` factory. |
| `services/api-gateway/db/migrations/postgres_users.sql` | Standalone Postgres migration script. |
| `services/api-gateway/config.py` | Settings — `USER_DB_BACKEND`, `POSTGRES_USER_DSN`, `MONGO_URI`, `MONGO_DB`. |
| `docker-compose.yml` (api-gateway block) | Maps env vars into the container. |
