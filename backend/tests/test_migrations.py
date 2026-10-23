import shutil, psycopg, pytest
from app import migrate

TABLES = {"restaurants", "users", "sessions", "auth_tokens", "rate_limits", "schema_migrations"}
def tables(url):
    with psycopg.connect(url) as c: return {r[0] for r in c.execute("select tablename from pg_tables where schemaname='public'")}

def test_applies_from_empty(clean_db):
    assert migrate.run(clean_db, say=lambda *_: None)
    assert TABLES <= tables(clean_db)

def test_second_run_is_noop(clean_db):
    migrate.run(clean_db, say=lambda *_: None)
    assert migrate.run(clean_db, say=lambda *_: None) == []

def test_edited_migration_is_rejected(clean_db, tmp_path):
    d = tmp_path / "m"; shutil.copytree(migrate.DIR, d)
    migrate.run(clean_db, d, say=lambda *_: None)
    (d / "0002_platform.sql").write_text((d / "0002_platform.sql").read_text() + "\n-- tampered\n")
    with pytest.raises(migrate.MigrationError): migrate.run(clean_db, d, say=lambda *_: None)

def test_superadmin_must_have_no_restaurant(clean_db):
    migrate.run(clean_db, say=lambda *_: None)
    with psycopg.connect(clean_db) as c:
        c.execute("insert into restaurants(name,slug) values('A','a')")
        with pytest.raises(psycopg.errors.CheckViolation):
            c.execute("insert into users(username,role,restaurant_id) select 'boss','superadmin',id from restaurants")
