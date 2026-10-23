import os
import psycopg
from app import config

config.load_dotenv()

with psycopg.connect(os.environ["TEST_DATABASE_URL"]) as conn:
    print("Database:", conn.execute("SELECT current_database()").fetchone()[0])
    print(
        "Public tables:",
        conn.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = %s",
            ("public",),
        ).fetchone()[0],
    )
