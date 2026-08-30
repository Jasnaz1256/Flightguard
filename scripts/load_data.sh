#!/usr/bin/env bash
set -e

DB="postgresql://postgres:postgres@localhost:5432/flightguard"

echo "Rebuilding tables..."
psql "$DB" -f sql/schema.sql

for csv in data/flights_jan2026.csv data/flights_feb2026.csv data/flights_mar2026.csv; do
    echo "Loading $csv ..."
    psql "$DB" -f sql/staging.sql
    psql "$DB" -c "\copy flights_staging FROM '$csv' WITH (FORMAT csv, HEADER true)"
    psql "$DB" -f sql/transform.sql
done

echo "Total flights:"
psql "$DB" -c "SELECT COUNT(*) FROM flights;"