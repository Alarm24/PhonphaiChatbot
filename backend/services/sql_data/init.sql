CREATE TABLE IF NOT EXISTS issue_logs (
    code VARCHAR(50) NOT NULL,
    issue_id INTEGER,
    "user" INTEGER,
    status VARCHAR(100),
    process_level VARCHAR(100),
    updated_date TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_issue_logs_code ON issue_logs (code);

COPY issue_logs(code, issue_id, "user", status, process_level, updated_date)
FROM '/docker-entrypoint-initdb.d/dump.csv'
WITH (FORMAT csv, HEADER true);
