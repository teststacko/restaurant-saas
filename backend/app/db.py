"""Connection layer. Every request runs in ONE transaction; the restaurant id is set with
set_config(..., is_local=true) so it cannot leak to another request through the pool (RLS reads it)."""
import contextlib, uuid
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from . import config

_pool = None
def pool():
    global _pool
    if _pool is None:
        _pool = ConnectionPool(config.database_url(), min_size=1, max_size=10, kwargs={"row_factory": dict_row}, open=True)
    return _pool
def close():
    global _pool
    if _pool: _pool.close(); _pool = None

@contextlib.contextmanager
def platform_tx(read_only=False):
    """Auth/platform tables (users, sessions, restaurants). No restaurant context."""
    with pool().connection() as conn:
        if read_only: conn.execute("SET TRANSACTION READ ONLY")   # must be the first statement
        yield conn

@contextlib.contextmanager
def tenant_tx(restaurant_id, read_only=False):
    """Business data for exactly one restaurant. read_only is enforced by PostgreSQL itself."""
    rid = str(uuid.UUID(str(restaurant_id)))                       # rejects anything that is not a UUID
    with pool().connection() as conn:
        if read_only: conn.execute("SET TRANSACTION READ ONLY")
        conn.execute("select set_config('app.restaurant_id', %s, true)", (rid,))
        yield conn
