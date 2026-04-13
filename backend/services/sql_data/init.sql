CREATE TABLE IF NOT EXISTS issue_logs (
    code VARCHAR(50) NOT NULL,
    issue_id INTEGER,
    "user" INTEGER,
    status VARCHAR(100),
    process_level VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_issue_logs_code ON issue_logs (code);

COPY issue_logs(code, issue_id, "user", status, process_level)
FROM '/docker-entrypoint-initdb.d/dump.csv'
WITH (FORMAT csv, HEADER true);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
