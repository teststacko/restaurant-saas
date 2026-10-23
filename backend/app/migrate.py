import hashlib, re
from pathlib import Path
import psycopg
from . import config

DIR = Path(__file__).resolve().parents[1] / "migrations"
LOCK = 727274
NAME = re.compile(r"^\d{4}_[a-z0-9_]+\.sql$")
class MigrationError(RuntimeError): pass

def files(directory=DIR):
    fs = sorted(Path(directory).glob("*.sql"))
    bad = [p.name for p in fs if not NAME.match(p.name)]
    if bad: raise MigrationError(f"Bad migration file name(s): {bad}. Use NNNN_description.sql")
    return fs
def checksum(p): return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()  # same on Windows and Linux

def run(url=None, directory=DIR, say=print):
    url = url or config.migration_url(); applied = []
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("select pg_advisory_lock(%s)", (LOCK,))
        try:
            conn.execute("create table if not exists schema_migrations(version text primary key, checksum text not null, applied_at timestamptz not null default now())")
            done = dict(conn.execute("select version, checksum from schema_migrations").fetchall())
            for p in files(directory):
                c = checksum(p)
                if p.stem in done:
                    if done[p.stem] != c: raise MigrationError(f"{p.name} was edited after it was applied. Add a new migration instead.")
                    continue
                with conn.transaction():
                    conn.execute(p.read_text(encoding="utf-8"))
                    conn.execute("insert into schema_migrations(version, checksum) values (%s, %s)", (p.stem, c))
                say(f"applied {p.stem}"); applied.append(p.stem)
        finally:
            conn.execute("select pg_advisory_unlock(%s)", (LOCK,))
    return applied

def status(url=None, directory=DIR):
    url = url or config.migration_url()
    with psycopg.connect(url) as conn:
        ok = conn.execute("select to_regclass('schema_migrations') is not null").fetchone()[0]
        done = dict(conn.execute("select version, checksum from schema_migrations").fetchall()) if ok else {}
    return [(p.stem, "applied" if p.stem in done else "PENDING") for p in files(directory)]
