import argparse, sys
from app import config, migrate

def main():
    ap = argparse.ArgumentParser(prog="manage.py")
    ap.add_argument("cmd", choices=["migrate", "status"])
    a = ap.parse_args()
    try:
        if a.cmd == "migrate":
            done = migrate.run(); print("Nothing to apply." if not done else f"Applied {len(done)} migration(s).")
        else:
            for v, s in migrate.status(): print(f"{s:8} {v}")
    except (config.ConfigError, migrate.MigrationError) as e:
        print("ERROR:", e); sys.exit(1)
main()
