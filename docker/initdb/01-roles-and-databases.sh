#!/bin/sh
# Runs once, on first start of an empty data volume. The bootstrap superuser is never used by the app.
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
create role app_owner login password '${APP_OWNER_PASSWORD}';
create role app_user login password '${APP_USER_PASSWORD}' nosuperuser nobypassrls nocreatedb nocreaterole;
alter database restops owner to app_owner;
create database restops_test owner app_owner;
SQL
