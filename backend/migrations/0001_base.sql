-- Base database privileges.
-- Application access to tables and sequences must be granted explicitly
-- by later migrations after the required security policies are defined.

CREATE EXTENSION IF NOT EXISTS citext;

GRANT USAGE ON SCHEMA public TO app_user;
