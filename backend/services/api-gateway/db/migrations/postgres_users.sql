-- Auth users schema for the Postgres backend.
-- Safe to run repeatedly: every statement is idempotent.
-- The api-gateway also runs this on startup when USER_DB_BACKEND=postgres,
-- so this file only matters for deployers who manage migrations out-of-band.

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
