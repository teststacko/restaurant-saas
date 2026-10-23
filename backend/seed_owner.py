import hashlib, os, psycopg
from app.config import migration_url

def hash_pw(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, maxmem=0)
    return f"scrypt:{salt.hex()}:{dk.hex()}"

def seed():
    with psycopg.connect(migration_url()) as conn:
        with conn.cursor() as cur:
            row = cur.execute("SELECT id FROM restaurants WHERE slug = 'demo-dhaba'").fetchone()
            if not row:
                print("demo-dhaba restaurant not found!")
                return
            rid = row[0]

            username = "owner"
            password = "password123"
            pw_hash = hash_pw(password)

            cur.execute("""
                INSERT INTO users (restaurant_id, username, password_hash, role)
                VALUES (%s, %s, %s, 'owner')
                ON CONFLICT (username) DO UPDATE 
                SET password_hash = EXCLUDED.password_hash, role = 'owner', restaurant_id = EXCLUDED.restaurant_id
                RETURNING id;
            """, (rid, username, pw_hash))
            uid = cur.fetchone()[0]
            conn.commit()
            print(f"Created default owner account:\n  Username: {username}\n  Password: {password}\n  User ID: {uid}")

if __name__ == "__main__":
    seed()
