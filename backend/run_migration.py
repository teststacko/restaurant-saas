import psycopg
from app.config import migration_url

print("1/3 Running database migration...")
with psycopg.connect(migration_url()) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS allowed_sections jsonb DEFAULT '["*"]'::jsonb;
        """)
        cur.execute("""
            UPDATE users SET allowed_sections = '["*"]'::jsonb WHERE role IN ('owner', 'superadmin');
        """)
        cur.execute("""
            UPDATE users SET allowed_sections = '["sales", "closings", "feedback"]'::jsonb WHERE role = 'cashier';
        """)
        conn.commit()
print("DATABASE UPDATED")
