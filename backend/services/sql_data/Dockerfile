FROM postgres:16-alpine

COPY services/sql_data/init.sql /docker-entrypoint-initdb.d/10-init.sql
COPY services/sql_data/dump.csv /docker-entrypoint-initdb.d/dump.csv
