import csv, io, re, uuid, json, random, os, contextlib, hashlib, hmac, secrets, datetime as dt
from fastapi import FastAPI, Header, Cookie, HTTPException, UploadFile, Response, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
import os, shutil
from fastapi import UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.db import platform_tx, tenant_tx, close as close_db_pool

BASE = os.path.dirname(os.path.abspath(__file__))
UP = os.path.join(BASE, "uploads")
FE = os.path.join(BASE, "..", "frontend")
os.makedirs(UP, exist_ok=True)

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    close_db_pool()

app = FastAPI(title="Amber Fort Hotel Operation", lifespan=lifespan)

# CORS configuration for local testing and Vercel production frontend
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app|http://localhost:.*|http://127\.0\.0\.1:.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory and mount static route
os.makedirs("uploads/bills", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Create uploads directory and mount static route
os.makedirs("uploads/bills", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
@app.get("/api/health")
def health():
    return {"status": "ok"}
@app.post("/api/upload")
def upload_file(file: UploadFile = File(...), session_id: str = Cookie(None)):
    require_auth(session_id)
    ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    if ext not in ['jpg', 'jpeg', 'png', 'pdf', 'csv', 'txt']:
        raise HTTPException(400, "Invalid file format. Allowed: jpg, jpeg, png, pdf, csv, txt")
    fname = f"{uuid.uuid4().hex}.{ext}"
    dest_path = os.path.join("uploads", "bills", fname)
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"url": f"/uploads/bills/{fname}"}

def hash_pw(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, maxmem=0)
    return f"scrypt:{salt.hex()}:{dk.hex()}"

def verify_pw(password: str, hashed: str) -> bool:
    try:
        algo, salt_hex, hash_hex = hashed.split(":")
        if algo != "scrypt":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        dk = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, maxmem=0)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False

def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def F(n, l, t="text", o=None, r=False): return {"n": n, "l": l, "t": t, "o": o, "r": r}
SCHEMA = {
 "sales": {"title": "Sales", "icon": "sales", "f": [F("day","Date","date",r=1), F("item","Item"), F("qty","Qty","number"), F("amount","Amount (INR)","number",r=1),
     F("method","Payment","select",["cash","upi","card","delivery"]), F("channel","Channel","select",["dine-in","takeaway","delivery"]), F("ref","Bill no")]},
 "purchases": {"title": "Purchases", "icon": "purchases", "f": [F("day","Date","date",r=1), F("supplier","Supplier",r=1), F("item","Item",r=1), F("unit","Unit","select",["kg","g","l","ml","pcs","pack"]),
     F("qty","Quantity","number",r=1), F("unit_price","Unit price (INR)","number",r=1), F("paid","Paid so far (INR)","number"), F("bill","Bill photo","image")]},
 "expenses": {"title": "Expenses", "icon": "expenses", "f": [F("day","Date","date",r=1), F("category","Category","select",["Gas","Electricity","Water","Rent","Salary","Repairs","Packaging","Cleaning","Other"],r=1),
     F("amount","Amount (INR)","number",r=1), F("note","Note"), F("bill","Bill photo","image")]},
 "wastage": {"title": "Wastage", "icon": "wastage", "f": [F("day","Date","date",r=1), F("item","Ingredient / dish",r=1), F("qty","Quantity","number",r=1), F("unit_cost","Cost per unit (INR)","number"),
     F("reason","Reason","select",["Spoiled","Spilled / damaged","Over-prepared","Returned","Expired"],r=1)]},
 "inventory": {"title": "Inventory", "icon": "inventory", "f": [F("name","Ingredient",r=1), F("unit","Unit","select",["kg","g","l","ml","pcs","pack"]), F("on_hand","On hand","number",r=1), F("low_at","Low-stock alert at","number")]},
 "staff": {"title": "Staff", "icon": "staff", "f": [F("name","Name",r=1), F("role","Role","select",["Owner","Manager","Cashier","Chef","Waiter","Helper"],r=1), F("salary","Monthly salary (INR)","number"), F("phone","Phone")]},
 "feedback": {"title": "Feedback", "icon": "feedback", "f": [F("day","Date","date",r=1), F("rating","Rating (1-5)","number",r=1), F("comment","Comment"), F("status","Status","select",["new","resolved"])]},
 "closings": {"title": "Cash Closing", "icon": "closings", "f": [F("day","Date","date",r=1), F("expected","Expected cash (INR), auto if blank","number"), F("actual","Cash counted (INR)","number",r=1), F("note","Note")]},
}




def chk(t: str):
    if t not in SCHEMA:
        raise HTTPException(404, "Unknown section")

def clean(t: str, d: dict, partial: bool = False):
    out = {}
    fields_to_check = [f for f in SCHEMA[t]["f"] if f["n"] in d] if partial else SCHEMA[t]["f"]
    for f in fields_to_check:
        v = d.get(f["n"])
        if v in ("", None):
            if f["r"] and not partial:
                raise HTTPException(422, f"{f['l']} is required")
            out[f["n"]] = None
        else:
            try:
                out[f["n"]] = float(v) if f["t"] == "number" else str(v)
            except ValueError:
                raise HTTPException(422, f"{f['l']} must be a number")
    return out


@app.post("/api/auth/logout")
def logout(response: Response, session_id: str = Cookie(None)):
    if session_id:
        token_hash = hash_session_token(session_id)
        with platform_tx() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = %s", (token_hash,))
    
    # Explicitly clear the cookie
    response.delete_cookie(
        key="session_id",
        path="/",
        httponly=True,
        samesite="lax"
    )
    return {"ok": True}







@app.get("/api/schema")
def get_schema():
    return SCHEMA





@app.get("/api/report/{t}")
def report(t: str, session_id: str = Cookie(None)):
    chk(t)
    u = require_auth(session_id)
    check_permission(u, t)
    rid = str(u["restaurant_id"])
    with tenant_tx(rid, read_only=True) as conn:
        rows = [dict(r) for r in conn.execute(f"SELECT * FROM {t} WHERE deleted = false ORDER BY created_at DESC").fetchall()]
    s = io.StringIO()
    if rows:
        w = csv.DictWriter(s, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return StreamingResponse(iter([s.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={t}.csv"})


# ===================== Team, roles, dashboard tiles, audit, pagination (v3) =====================
BUILTIN_ROLES = ["manager", "cashier", "chef"]
OWNERS = ("owner", "superadmin")
SECTIONS = [("dashboard", "Dashboard"), ("sales", "Sales (POS & Orders)"), ("purchases", "Purchases (Supplier Bills)"), ("expenses", "Expenses (Overheads)"),
            ("closings", "Cash Closing (Shifts)"), ("inventory", "Inventory (Stock Counts)"), ("wastage", "Wastage (Kitchen Waste)"),
            ("staff", "Staff & Salaries"), ("feedback", "Customer Feedback")]
SECTION_KEYS = {k for k, _ in SECTIONS}
TILES = [("kpi_sales", "Net sales & orders"), ("kpi_aov", "Average order value"), ("kpi_purchases", "Purchases & amount owed"), ("kpi_expenses", "Expenses"),
         ("kpi_profit", "Estimated profit"), ("kpi_wastage", "Wastage cost"), ("kpi_rating", "Average rating"), ("chart_sales_spend", "Sales vs spend chart"),
         ("chart_payments", "Payment methods chart"), ("chart_top_dishes", "Top dishes chart"), ("chart_weekday", "Sales by weekday chart"),
         ("low_stock", "Low-stock alerts"), ("cash_diffs", "Cash mismatches")]
TILE_KEYS = {k for k, _ in TILES}
ROLE_RE = re.compile(r"^[a-z0-9][a-z0-9 &/\-]{1,29}$")
PW_CHARS = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"

def jl(v): return json.loads(v) if isinstance(v, str) else v
def norm_role(r):
    r = (r or "").strip().lower()
    if not ROLE_RE.match(r) or r in OWNERS: raise HTTPException(422, "Role names use 2-30 letters, numbers or spaces and cannot be 'owner' or 'superadmin'")
    return r
def owner_only(u, msg="Only the owner can manage the team"):
    if u.get("role") not in OWNERS: raise HTTPException(403, msg)
def scope(conn, rid): conn.execute("select set_config('app.restaurant_id', %s, true)", (str(rid),))
def audit(conn, rid, u, kind, section, summary, entity_id=None, details=None):
    scope(conn, rid)
    conn.execute("INSERT INTO audit_logs (restaurant_id, actor_user_id, actor_username, kind, section, entity_id, action, details) VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)",
                 (rid, u["id"], u["username"], kind, section, entity_id, summary, json.dumps(details, default=str) if details else None))
def brief(r):
    name = next((r.get(k) for k in ("item", "name", "supplier", "category", "comment", "day") if r.get(k)), "")
    amt = next((r.get(k) for k in ("amount", "qty", "on_hand", "actual", "rating") if r.get(k) is not None), None)
    return str(name) + (f" ({amt})" if amt is not None else "")
def norm(v, is_num):
    if v is None: return None
    return round(float(v), 2) if is_num else str(v)

def effective_tiles(u):
    if u.get("role") in OWNERS: return set(TILE_KEYS)
    if u.get("allowed_tiles") is not None: return TILE_KEYS & set(u["allowed_tiles"])
    a = u.get("allowed_sections") or []; has = lambda s: "*" in a or s in a
    out = {"kpi_rating"}
    if has("sales"): out |= {"kpi_sales", "kpi_aov", "chart_sales_spend", "chart_payments", "chart_top_dishes", "chart_weekday"}
    if has("purchases"): out.add("kpi_purchases")
    if has("expenses"): out.add("kpi_expenses")
    if has("wastage"): out.add("kpi_wastage")
    if has("sales") and has("purchases") and has("expenses"): out.add("kpi_profit")
    if has("inventory"): out.add("low_stock")
    return out

def require_auth(session_id=None, allow_pending=False):
    if not session_id: raise HTTPException(401, "Session required. Please sign in.")
    with platform_tx(read_only=True) as conn:
        user = conn.execute("""SELECT u.id, u.username, u.role, u.restaurant_id, coalesce(u.allowed_sections, '["*"]'::jsonb) AS allowed_sections, u.allowed_tiles,
                   u.must_set_password, r.name AS restaurant_name, r.slug
            FROM sessions s JOIN users u ON s.user_id = u.id LEFT JOIN restaurants r ON u.restaurant_id = r.id
            WHERE s.token_hash = %s AND s.expires_at > now() AND s.revoked_at IS NULL AND u.is_active AND (r.status IS NULL OR r.status = 'active')""",
            (hash_session_token(session_id),)).fetchone()
    if not user: raise HTTPException(401, "Session expired. Please sign in again.")
    res = dict(user); res["allowed_sections"] = jl(res["allowed_sections"]); res["allowed_tiles"] = jl(res["allowed_tiles"])
    if res["must_set_password"] and not allow_pending: raise HTTPException(403, "Please set a new password before continuing.")
    return res

def check_permission(user, section):
    if user.get("role") in OWNERS: return True
    allowed = user.get("allowed_sections", [])
    if "*" in allowed or section in allowed: return True
    raise HTTPException(403, f"Access Denied: '{section}' is not enabled for your account. Contact the owner.")

def clean_access(d):
    secs, tiles = d.get("allowed_sections", []), d.get("allowed_tiles", [])
    if not isinstance(secs, list) or not set(secs) <= SECTION_KEYS: raise HTTPException(422, "Unknown section in allowed_sections")
    if not isinstance(tiles, list) or not set(tiles) <= TILE_KEYS: raise HTTPException(422, "Unknown dashboard tile")
    return secs, (tiles if "dashboard" in secs else [])

def get_member(conn, u, user_id):
    try: uuid.UUID(str(user_id))
    except ValueError: raise HTTPException(404, "User not found")
    t = conn.execute("SELECT id, username, role FROM users WHERE id = %s::uuid AND restaurant_id = %s::uuid", (user_id, u["restaurant_id"])).fetchone()
    if not t: raise HTTPException(404, "User not found")
    if t["role"] in OWNERS: raise HTTPException(400, "Owner accounts cannot be changed here")
    return t

@app.post("/api/auth/login")
def login(d: dict, response: Response):
    username, password = (d.get("username") or "").strip(), (d.get("password") or "").strip()
    if not username or not password: raise HTTPException(422, "Username and password required")
    with platform_tx(read_only=False) as conn:
        user = conn.execute("""SELECT id, username, password_hash, role, restaurant_id, is_active, must_set_password,
                coalesce(allowed_sections, '["*"]'::jsonb) AS allowed_sections, allowed_tiles FROM users WHERE username = %s""", (username,)).fetchone()
        if not user or not user["password_hash"] or not verify_pw(password, user["password_hash"]): raise HTTPException(401, "Invalid username or password")
        if not user["is_active"]: raise HTTPException(403, "This account is deactivated. Please contact the owner.")
        raw = secrets.token_urlsafe(32)
        conn.execute("INSERT INTO sessions (user_id, token_hash, expires_at) VALUES (%s, %s, %s)", (user["id"], hash_session_token(raw), dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=7)))
        conn.execute("UPDATE users SET last_login_at = now() WHERE id = %s", (user["id"],))
        if user["restaurant_id"]: audit(conn, user["restaurant_id"], user, "login", None, "signed in")
        response.set_cookie("session_id", raw, httponly=True, samesite="lax", secure=os.environ.get("COOKIE_SECURE", "").lower() == "true", max_age=7 * 86400)
        return {"ok": True, "user": {"id": str(user["id"]), "username": user["username"], "role": user["role"], "restaurant_id": str(user["restaurant_id"]) if user["restaurant_id"] else None,
                "allowed_sections": jl(user["allowed_sections"]), "allowed_tiles": jl(user["allowed_tiles"]), "must_set_password": user["must_set_password"]}}

@app.get("/api/auth/me")
def me(session_id: str = Cookie(None)):
    if not session_id: return {"authenticated": False, "user": None}
    try: return {"authenticated": True, "user": require_auth(session_id, allow_pending=True)}
    except HTTPException: return {"authenticated": False, "user": None}

@app.post("/api/auth/change-password")
def change_password(d: dict, session_id: str = Cookie(None)):
    u = require_auth(session_id, allow_pending=True)
    cur, new = (d.get("current") or "").strip(), (d.get("new") or "").strip()
    if len(new) < 8: raise HTTPException(422, "New password must be at least 8 characters")
    if new == cur: raise HTTPException(422, "New password must be different from the current one")
    with platform_tx() as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE id = %s", (u["id"],)).fetchone()
        if not verify_pw(cur, row["password_hash"]): raise HTTPException(403, "Current password is incorrect")
        conn.execute("UPDATE users SET password_hash = %s, must_set_password = false, password_changed_at = now() WHERE id = %s", (hash_pw(new), u["id"]))
        conn.execute("DELETE FROM sessions WHERE user_id = %s AND token_hash <> %s", (u["id"], hash_session_token(session_id)))
        if u["restaurant_id"]: audit(conn, u["restaurant_id"], u, "password", None, "changed their own password")
    return {"ok": True}

@app.get("/api/meta")
def meta(session_id: str = Cookie(None)):
    u = require_auth(session_id); roles = list(BUILTIN_ROLES)
    if u["role"] in OWNERS:
        with tenant_tx(u["restaurant_id"], read_only=True) as c:
            roles += [r["name"] for r in c.execute("SELECT name FROM team_roles ORDER BY name").fetchall() if r["name"] not in roles]
    return {"sections": [{"key": k, "label": l} for k, l in SECTIONS], "tiles": [{"key": k, "label": l} for k, l in TILES], "roles": roles, "builtin_roles": BUILTIN_ROLES}

@app.get("/api/users")
def list_users(session_id: str = Cookie(None)):
    u = require_auth(session_id); owner_only(u)
    with platform_tx(read_only=True) as conn:
        rows = conn.execute("""SELECT id, username, role, is_active, last_login_at, password_changed_at, created_at,
                coalesce(allowed_sections, '[]'::jsonb) AS allowed_sections, allowed_tiles FROM users WHERE restaurant_id = %s::uuid ORDER BY created_at DESC""", (u["restaurant_id"],)).fetchall()
    out = []
    for r in rows:
        d = dict(r); d["allowed_sections"] = jl(d["allowed_sections"]); d["allowed_tiles"] = jl(d["allowed_tiles"]); d["effective_tiles"] = sorted(effective_tiles(d)); out.append(d)
    return out

@app.post("/api/users")
def create_user(d: dict, session_id: str = Cookie(None)):
    u = require_auth(session_id); owner_only(u)
    username, password, role = (d.get("username") or "").strip(), (d.get("password") or "").strip(), norm_role(d.get("role") or "cashier")
    if len(username) < 3: raise HTTPException(422, "Username must be at least 3 characters")
    if len(password) < 8: raise HTTPException(422, "Temporary password must be at least 8 characters")
    secs, tiles = clean_access(d)
    with platform_tx(read_only=False) as conn:
        if conn.execute("SELECT 1 FROM users WHERE username = %s", (username,)).fetchone(): raise HTTPException(409, "Username already taken")
        scope(conn, u["restaurant_id"])
        if role not in BUILTIN_ROLES: conn.execute("INSERT INTO team_roles (restaurant_id, name) VALUES (%s, %s) ON CONFLICT DO NOTHING", (u["restaurant_id"], role))
        row = conn.execute("""INSERT INTO users (restaurant_id, username, password_hash, role, allowed_sections, allowed_tiles, must_set_password, created_by, password_changed_at)
                VALUES (%s::uuid, %s, %s, %s, %s::jsonb, %s::jsonb, true, %s, now()) RETURNING id""", (u["restaurant_id"], username, hash_pw(password), role, json.dumps(secs), json.dumps(tiles), u["id"])).fetchone()
        audit(conn, u["restaurant_id"], u, "user", None, f"created team member {username} ({role})", str(row["id"]), {"sections": secs, "tiles": tiles})
    return {"id": str(row["id"]), "username": username, "role": role}

@app.put("/api/users/{user_id}/permissions")
def update_permissions(user_id: str, d: dict, session_id: str = Cookie(None)):
    u = require_auth(session_id); owner_only(u); secs, tiles = clean_access(d)
    with platform_tx(read_only=False) as conn:
        t = get_member(conn, u, user_id)
        conn.execute("UPDATE users SET allowed_sections = %s::jsonb, allowed_tiles = %s::jsonb WHERE id = %s::uuid", (json.dumps(secs), json.dumps(tiles), user_id))
        audit(conn, u["restaurant_id"], u, "user", None, f"changed access for {t['username']}", user_id, {"sections": secs, "tiles": tiles})
    return {"ok": True, "allowed_sections": secs, "allowed_tiles": tiles}

@app.post("/api/users/{user_id}/reset-password")
def reset_password(user_id: str, session_id: str = Cookie(None)):
    u = require_auth(session_id); owner_only(u); pw = "".join(secrets.choice(PW_CHARS) for _ in range(10))
    with platform_tx(read_only=False) as conn:
        t = get_member(conn, u, user_id)
        conn.execute("UPDATE users SET password_hash = %s, must_set_password = true, password_changed_at = now() WHERE id = %s::uuid", (hash_pw(pw), user_id))
        conn.execute("DELETE FROM sessions WHERE user_id = %s::uuid", (user_id,))
        audit(conn, u["restaurant_id"], u, "password", None, f"reset password for {t['username']}", user_id)
    return {"password": pw}   # returned once; only the hash is stored

@app.put("/api/users/{user_id}/active")
def set_active(user_id: str, d: dict, session_id: str = Cookie(None)):
    u = require_auth(session_id); owner_only(u); on = bool(d.get("active"))
    with platform_tx(read_only=False) as conn:
        t = get_member(conn, u, user_id)
        conn.execute("UPDATE users SET is_active = %s WHERE id = %s::uuid", (on, user_id))
        if not on: conn.execute("DELETE FROM sessions WHERE user_id = %s::uuid", (user_id,))
        audit(conn, u["restaurant_id"], u, "user", None, f"{'activated' if on else 'deactivated'} {t['username']}", user_id)
    return {"ok": True}

@app.post("/api/roles")
def add_role(d: dict, session_id: str = Cookie(None)):
    u = require_auth(session_id); owner_only(u); name = norm_role(d.get("name"))
    with tenant_tx(u["restaurant_id"]) as c:
        if name not in BUILTIN_ROLES: c.execute("INSERT INTO team_roles (restaurant_id, name) VALUES (%s, %s) ON CONFLICT DO NOTHING", (str(u["restaurant_id"]), name))
        audit(c, u["restaurant_id"], u, "role", None, f"added role '{name}'")
    return {"name": name}

@app.delete("/api/roles/{name}")
def del_role(name: str, session_id: str = Cookie(None)):
    u = require_auth(session_id); owner_only(u); name = norm_role(name)
    if name in BUILTIN_ROLES: raise HTTPException(400, "Built-in roles cannot be deleted")
    with platform_tx(read_only=False) as c:
        if c.execute("SELECT 1 FROM users WHERE restaurant_id = %s::uuid AND role = %s", (u["restaurant_id"], name)).fetchone(): raise HTTPException(409, "Some team members still have this role")
        scope(c, u["restaurant_id"]); c.execute("DELETE FROM team_roles WHERE name = %s", (name,))
        audit(c, u["restaurant_id"], u, "role", None, f"deleted role '{name}'")
    return {"ok": True}

@app.get("/api/logs")
def logs(page: int = 1, size: int = 10, user_id: str = "", kind: str = "", session_id: str = Cookie(None)):
    u = require_auth(session_id); owner_only(u); page, size = max(page, 1), min(max(size, 1), 50); w, p = ["true"], []
    if user_id:
        try: uuid.UUID(user_id)
        except ValueError: raise HTTPException(422, "Invalid member")
        w.append("a.actor_user_id = %s::uuid"); p.append(user_id)
    if kind: w.append("a.kind = %s"); p.append(kind)
    W = " AND ".join(w)
    with tenant_tx(u["restaurant_id"], read_only=True) as c:
        total = c.execute(f"SELECT count(*) AS n FROM audit_logs a WHERE {W}", p).fetchone()["n"]
        rows = c.execute(f"""SELECT a.id, a.created_at, coalesce(a.actor_username, us.username, 'system') AS who, a.kind, a.section, a.action, a.details
                FROM audit_logs a LEFT JOIN users us ON us.id = a.actor_user_id WHERE {W} ORDER BY a.created_at DESC LIMIT %s OFFSET %s""", p + [size, (page - 1) * size]).fetchall()
    return {"rows": [dict(r) for r in rows], "total": total, "page": page, "pages": max(1, -(-total // size))}

@app.get("/api/data/{t}")
def lst(
    t: str,
    page: int = 1,
    page_size: int = 10,
    q: str = "",
    start: str = None,
    end: str = None,
    session_id: str = Cookie(None)
):
    chk(t)
    u = require_auth(session_id)
    check_permission(u, t)
    rid = str(u["restaurant_id"])

    # Determine sorting
    has_day = any(f["n"] == "day" for f in SCHEMA[t]["f"])
    # After
    order = "day DESC, created_at DESC, id DESC" if has_day else "created_at DESC, id DESC"

    # Build WHERE conditions
    conditions = ["deleted = false"]
    params = [rid]

    # Date range filtering for transaction tables
    if has_day and start and end:
        conditions.append("day BETWEEN %s::date AND %s::date")
        params.extend([start, end])

    # Text search filtering
    if q and q.strip():
        search_terms = []
        for f in SCHEMA[t]["f"]:
            if f["t"] in ("text", "select"):
                search_terms.append(f"coalesce({f['n']}::text, '') ILIKE %s")
                params.append(f"%{q.strip()}%")
        if search_terms:
            conditions.append(f"({' OR '.join(search_terms)})")

    where_clause = " AND ".join(conditions)

    with tenant_tx(rid, read_only=True) as conn:
        # Total matching records count for accurate pagination
        count_sql = f"SELECT count(*) AS total FROM {t} WHERE restaurant_id = %s::uuid AND {where_clause}"
        total_rows = conn.execute(count_sql, params).fetchone()["total"]

        # Paginated slice
        offset = max(0, (page - 1) * page_size)
        query_sql = f"""
            SELECT * FROM {t}
            WHERE restaurant_id = %s::uuid AND {where_clause}
            ORDER BY {order}
            LIMIT %s OFFSET %s
        """
        rows = conn.execute(query_sql, params + [page_size, offset]).fetchall()

        return {
            "items": [dict(r) for r in rows],
            "total": total_rows,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total_rows + page_size - 1) // page_size)
        }

@app.post("/api/data/{t}")
def add(t: str, d: dict, session_id: str = Cookie(None)):
    chk(t); u = require_auth(session_id); check_permission(u, t); rid = str(u["restaurant_id"]); d = clean(t, d, partial=False)
    with tenant_tx(rid) as conn:
        if t == "closings" and d.get("expected") is None:
            d["expected"] = float(conn.execute("SELECT coalesce(sum(amount),0) AS v FROM sales WHERE deleted = false AND day = %s::date AND method = 'cash'", (d["day"],)).fetchone()["v"])
        cols = list(d.keys()); sm = {f["n"]: f for f in SCHEMA[t]["f"]}
        ph = [f"%s::{'date' if c == 'day' else 'numeric' if sm[c]['t'] == 'number' else 'text'}" for c in cols]
        new_id = conn.execute(f"INSERT INTO {t} (restaurant_id, {', '.join(cols)}) VALUES (%s, {', '.join(ph)}) RETURNING id;", [rid] + [d[k] for k in cols]).fetchone()["id"]
        audit(conn, rid, u, "create", t, f"added {SCHEMA[t]['title']}: {brief(d)}", str(new_id), {"values": d})
        return {"id": str(new_id)}

@app.put("/api/data/{t}/{i}")
def upd(t: str, i: str, d: dict, session_id: str = Cookie(None)):
    chk(t); u = require_auth(session_id); check_permission(u, t); rid = str(u["restaurant_id"]); d = clean(t, d, partial=True)
    if not d: return {"ok": True}
    try: uuid.UUID(i)
    except ValueError: raise HTTPException(404, "Record not found")
    with tenant_tx(rid) as conn:
        cols = list(d.keys()); sm = {f["n"]: f for f in SCHEMA[t]["f"]}
        old = conn.execute(f"SELECT {', '.join(cols)} FROM {t} WHERE id = %s::uuid AND deleted = false", (i,)).fetchone()
        if not old: raise HTTPException(404, "Record not found")
        sets = [f"{c} = %s::{'date' if c == 'day' else 'numeric' if sm[c]['t'] == 'number' else 'text'}" for c in cols]
        conn.execute(f"UPDATE {t} SET {', '.join(sets)} WHERE id = %s::uuid", [d[k] for k in cols] + [i])
        ch = {c: [norm(old[c], sm[c]["t"] == "number"), norm(d[c], sm[c]["t"] == "number")] for c in cols if norm(old[c], sm[c]["t"] == "number") != norm(d[c], sm[c]["t"] == "number")}
        if ch: audit(conn, rid, u, "update", t, f"edited {SCHEMA[t]['title']}: {brief({**dict(old), **d})}", i, {"changes": ch})
    return {"ok": True}

@app.delete("/api/data/{t}/{i}")
def rm(t: str, i: str, session_id: str = Cookie(None)):
    chk(t); u = require_auth(session_id); check_permission(u, t); owner_only(u, "Only owners can delete records"); rid = str(u["restaurant_id"])
    try: uuid.UUID(i)
    except ValueError: raise HTTPException(404, "Record not found")
    with tenant_tx(rid) as conn:
        old = conn.execute(f"SELECT * FROM {t} WHERE id = %s::uuid AND deleted = false", (i,)).fetchone()
        if not old: raise HTTPException(404, "Record not found")
        conn.execute(f"UPDATE {t} SET deleted = true WHERE id = %s::uuid", (i,))
        audit(conn, rid, u, "delete", t, f"deleted {SCHEMA[t]['title']}: {brief(dict(old))}", i)
    return {"ok": True}

@app.get("/api/dashboard")
def dash(start: str, end: str, session_id: str = Cookie(None)):
    u = require_auth(session_id); check_permission(u, "dashboard"); rid = str(u["restaurant_id"]); T = effective_tiles(u)
    W, p = "deleted = false AND day BETWEEN %s::date AND %s::date", (start, end); want = lambda *k: bool(T & set(k))
    
    with tenant_tx(rid, read_only=False) as conn:
        # Auto-purge audit logs older than 7 days seamlessly
        conn.execute("DELETE FROM audit_logs WHERE restaurant_id = %s::uuid AND created_at < NOW() - INTERVAL '7 days'", (rid,))
        
        v = lambda sql: float((conn.execute(sql, p).fetchone() or {}).get("v") or 0)
        rows = lambda sql, pp=p: [dict(r) for r in conn.execute(sql, pp).fetchall()]
        
        ns = want("kpi_sales", "kpi_aov", "kpi_profit", "chart_sales_spend", "chart_payments", "chart_top_dishes", "chart_weekday")
        npu = want("kpi_purchases", "kpi_profit", "chart_sales_spend")
        nex = want("kpi_expenses", "kpi_profit", "chart_sales_spend")
        nwa = want("kpi_wastage", "kpi_profit", "chart_sales_spend")

        sales = v(f"SELECT coalesce(sum(amount),0) AS v FROM sales WHERE {W}") if ns else 0.0
        orders = int(v(f"SELECT count(distinct coalesce(nullif(ref,''), id::text)) AS v FROM sales WHERE {W}")) if want("kpi_sales", "kpi_aov") else 0
        purch = v(f"SELECT coalesce(sum(qty * unit_price),0) AS v FROM purchases WHERE {W}") if npu else 0.0
        owed = v(f"SELECT coalesce(sum(qty * unit_price - coalesce(paid,0)),0) AS v FROM purchases WHERE {W}") if want("kpi_purchases") else 0.0
        exp = v(f"SELECT coalesce(sum(amount),0) AS v FROM expenses WHERE {W}") if nex else 0.0
        waste = v(f"SELECT coalesce(sum(qty * coalesce(unit_cost,0)),0) AS v FROM wastage WHERE {W}") if nwa else 0.0
        rate = v(f"SELECT avg(rating) AS v FROM feedback WHERE {W}") if want("kpi_rating") else 0.0
        
        kpi = {}
        if "kpi_sales" in T: kpi.update(sales=sales, orders=orders)
        if "kpi_aov" in T: kpi["aov"] = sales / orders if orders else 0.0
        if "kpi_purchases" in T: kpi.update(purchases=purch, owed=owed)
        if "kpi_expenses" in T: kpi["expenses"] = exp
        if "kpi_profit" in T: kpi["profit"] = sales - purch - exp - waste
        if "kpi_wastage" in T: kpi["wastage"] = waste
        if "kpi_rating" in T: kpi["rating"] = rate
        
        spend = f"""SELECT day, sum(v) AS spend FROM (
            SELECT day, qty * unit_price AS v FROM purchases WHERE {W} 
            UNION ALL SELECT day, amount AS v FROM expenses WHERE {W}
            UNION ALL SELECT day, qty * coalesce(unit_cost,0) AS v FROM wastage WHERE {W}
        ) sub GROUP BY day ORDER BY day"""
        
        can_finances = want("kpi_purchases", "kpi_expenses", "kpi_profit", "chart_sales_spend")

        return {
            "is_owner": u["role"] in ("owner", "superadmin"),
            "can_finances": can_finances,
            "tiles": sorted(T),
            "kpi": kpi,
            "warnings": [],
            "by_day": rows(f"SELECT day, sum(amount) AS sales FROM sales WHERE {W} GROUP BY day ORDER BY day") if want("chart_sales_spend") else [],
            "spend_day": rows(spend, (start, end, start, end, start, end)) if want("chart_sales_spend") else [],
            "payments": rows(f"SELECT method AS k, sum(amount) AS v FROM sales WHERE {W} GROUP BY method") if want("chart_payments") else [],
            "top_items": rows(f"SELECT item, sum(qty) AS qty, sum(amount) AS revenue FROM sales WHERE {W} AND item IS NOT NULL GROUP BY item ORDER BY revenue DESC LIMIT 5") if want("chart_top_dishes") else [],
            "weekday": rows(f"SELECT extract(dow from day)::text AS k, sum(amount) AS v FROM sales WHERE {W} GROUP BY k") if want("chart_weekday") else [],
            "low_stock": rows("SELECT name, on_hand, unit, low_at FROM inventory WHERE deleted = false AND on_hand <= coalesce(low_at, 0) ORDER BY on_hand", ()) if want("low_stock") else [],
            "cash_diffs": rows(f"SELECT day, expected, actual, actual - expected AS diff FROM closings WHERE {W} AND abs(actual - expected) > 0.5 ORDER BY day DESC LIMIT 5") if want("cash_diffs") else []
        }
if os.path.exists(FE):
    app.mount("/", StaticFiles(directory=FE, html=True), name="frontend")
