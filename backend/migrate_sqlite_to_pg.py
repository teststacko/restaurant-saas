import sqlite3
import psycopg
from app.config import migration_url

SQLITE_PATH = "app.db"

def run_migration():
    pg_url = migration_url()
    
    print("Connecting to SQLite and PostgreSQL...")
    s_conn = sqlite3.connect(SQLITE_PATH)
    s_conn.row_factory = sqlite3.Row
    s_cur = s_conn.cursor()

    with psycopg.connect(pg_url, autocommit=False) as pg_conn:
        with pg_conn.cursor() as pg_cur:
            print("1. Ensuring restaurant 'demo-dhaba' exists...")
            pg_cur.execute("""
                INSERT INTO restaurants (name, slug, currency, timezone)
                VALUES ('Demo Dhaba', 'demo-dhaba', 'INR', 'Asia/Kolkata')
                ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
                RETURNING id;
            """)
            restaurant_id = pg_cur.fetchone()[0]
            print(f"   Restaurant ID: {restaurant_id}")

            # Clear any partial runs for this restaurant
            for tbl in ['sales', 'purchases', 'inventory', 'expenses', 'closings', 'staff', 'wastage', 'feedback', 'audit_logs']:
                pg_cur.execute(f"DELETE FROM {tbl} WHERE restaurant_id = %s;", (restaurant_id,))

            # 2. Sales (684 records)
            sales = s_cur.execute("SELECT * FROM sales WHERE tenant='demo-dhaba'").fetchall()
            for r in sales:
                pg_cur.execute("""
                    INSERT INTO sales (restaurant_id, deleted, created_at, day, item, qty, amount, method, channel, ref)
                    VALUES (%s, %s, %s::timestamptz, %s::date, %s, %s, %s, %s, %s, %s);
                """, (restaurant_id, bool(r["deleted"]), r["created"], r["day"], r["item"], r["qty"] or 1, r["amount"] or 0.0, r["method"] or 'cash', r["channel"] or 'dine-in', r["ref"]))
            print(f"   Migrated {len(sales)} sales records.")

            # 3. Purchases (45 records)
            purchases = s_cur.execute("SELECT * FROM purchases WHERE tenant='demo-dhaba'").fetchall()
            for r in purchases:
                pg_cur.execute("""
                    INSERT INTO purchases (restaurant_id, deleted, created_at, day, supplier, item, unit, qty, unit_price, paid, bill)
                    VALUES (%s, %s, %s::timestamptz, %s::date, %s, %s, %s, %s, %s, %s, %s);
                """, (restaurant_id, bool(r["deleted"]), r["created"], r["day"], r["supplier"], r["item"], r["unit"] or 'kg', r["qty"] or 1, r["unit_price"] or 0.0, r["paid"], r["bill"]))
            print(f"   Migrated {len(purchases)} purchases records.")

            # 4. Inventory (6 records)
            inventory = s_cur.execute("SELECT * FROM inventory WHERE tenant='demo-dhaba'").fetchall()
            for r in inventory:
                pg_cur.execute("""
                    INSERT INTO inventory (restaurant_id, deleted, created_at, name, unit, on_hand, low_at)
                    VALUES (%s, %s, %s::timestamptz, %s, %s, %s, %s);
                """, (restaurant_id, bool(r["deleted"]), r["created"], r["name"], r["unit"] or 'kg', r["on_hand"] or 0.0, r["low_at"] or 0.0))
            print(f"   Migrated {len(inventory)} inventory records.")

            # 5. Expenses (35 records)
            expenses = s_cur.execute("SELECT * FROM expenses WHERE tenant='demo-dhaba'").fetchall()
            for r in expenses:
                pg_cur.execute("""
                    INSERT INTO expenses (restaurant_id, deleted, created_at, day, category, amount, note, bill)
                    VALUES (%s, %s, %s::timestamptz, %s::date, %s, %s, %s, %s);
                """, (restaurant_id, bool(r["deleted"]), r["created"], r["day"], r["category"], r["amount"] or 0.0, r["note"], r["bill"]))
            print(f"   Migrated {len(expenses)} expenses records.")

            # 6. Closings (30 records)
            closings = s_cur.execute("SELECT * FROM closings WHERE tenant='demo-dhaba'").fetchall()
            for r in closings:
                pg_cur.execute("""
                    INSERT INTO closings (restaurant_id, deleted, created_at, day, expected, actual, note)
                    VALUES (%s, %s, %s::timestamptz, %s::date, %s, %s, %s);
                """, (restaurant_id, bool(r["deleted"]), r["created"], r["day"], r["expected"] or 0.0, r["actual"] or 0.0, r["note"]))
            print(f"   Migrated {len(closings)} closings records.")

            # 7. Staff (4 records)
            staff = s_cur.execute("SELECT * FROM staff WHERE tenant='demo-dhaba'").fetchall()
            for r in staff:
                pg_cur.execute("""
                    INSERT INTO staff (restaurant_id, deleted, created_at, name, role, salary, phone)
                    VALUES (%s, %s, %s::timestamptz, %s, %s, %s, %s);
                """, (restaurant_id, bool(r["deleted"]), r["created"], r["name"], r["role"], r["salary"] or 0.0, r["phone"]))
            print(f"   Migrated {len(staff)} staff records.")

            # 8. Wastage (10 records)
            wastage = s_cur.execute("SELECT * FROM wastage WHERE tenant='demo-dhaba'").fetchall()
            for r in wastage:
                pg_cur.execute("""
                    INSERT INTO wastage (restaurant_id, deleted, created_at, day, item, qty, unit_cost, reason)
                    VALUES (%s, %s, %s::timestamptz, %s::date, %s, %s, %s, %s);
                """, (restaurant_id, bool(r["deleted"]), r["created"], r["day"], r["item"], r["qty"] or 1, r["unit_cost"] or 0.0, r["reason"]))
            print(f"   Migrated {len(wastage)} wastage records.")

            # 9. Feedback (8 records)
            feedback = s_cur.execute("SELECT * FROM feedback WHERE tenant='demo-dhaba'").fetchall()
            for r in feedback:
                pg_cur.execute("""
                    INSERT INTO feedback (restaurant_id, deleted, created_at, day, rating, comment, status)
                    VALUES (%s, %s, %s::timestamptz, %s::date, %s, %s, %s);
                """, (restaurant_id, bool(r["deleted"]), r["created"], r["day"], r["rating"] or 5.0, r["comment"], r["status"] or 'new'))
            print(f"   Migrated {len(feedback)} feedback records.")

            # 10. Audit Logs (822 records)
            audit = s_cur.execute("SELECT * FROM audit WHERE tenant='demo-dhaba'").fetchall()
            for r in audit:
                pg_cur.execute("""
                    INSERT INTO audit_logs (restaurant_id, created_at, action)
                    VALUES (%s, %s::timestamptz, %s);
                """, (restaurant_id, r["at"], r["what"]))
            print(f"   Migrated {len(audit)} audit records.")

            pg_conn.commit()
            print("Migration transaction committed successfully.")

if __name__ == "__main__":
    run_migration()
