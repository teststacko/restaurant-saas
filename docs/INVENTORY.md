# Legacy (SQLite) inventory - generated from backend/main.py

Machine-readable copy: backend/tests/fixtures/legacy_schema.json. Checkpoint 2 will add a test asserting every field below exists in PostgreSQL.

## Sections (8) and fields

### sales - Sales

| field | label | type | required | options |
|---|---|---|---|---|
| day | Date | date | yes |  |
| item | Item | text |  |  |
| qty | Qty | number |  |  |
| amount | Amount (₹) | number | yes |  |
| method | Payment | select |  | cash, upi, card, delivery |
| channel | Channel | select |  | dine-in, takeaway, delivery |
| ref | Bill no | text |  |  |

### purchases - Purchases

| field | label | type | required | options |
|---|---|---|---|---|
| day | Date | date | yes |  |
| supplier | Supplier | text | yes |  |
| item | Item | text | yes |  |
| unit | Unit | select |  | kg, g, l, ml, pcs, pack |
| qty | Quantity | number | yes |  |
| unit_price | Unit price (₹) | number | yes |  |
| paid | Paid so far (₹) | number |  |  |
| bill | Bill photo | image |  |  |

### expenses - Expenses

| field | label | type | required | options |
|---|---|---|---|---|
| day | Date | date | yes |  |
| category | Category | select | yes | Gas, Electricity, Water, Rent, Salary, Repairs, Packaging, Cleaning, Other |
| amount | Amount (₹) | number | yes |  |
| note | Note | text |  |  |
| bill | Bill photo | image |  |  |

### wastage - Wastage

| field | label | type | required | options |
|---|---|---|---|---|
| day | Date | date | yes |  |
| item | Ingredient / dish | text | yes |  |
| qty | Quantity | number | yes |  |
| unit_cost | Cost per unit (₹) | number |  |  |
| reason | Reason | select | yes | Spoiled, Spilled / damaged, Over-prepared, Returned, Expired |

### inventory - Inventory

| field | label | type | required | options |
|---|---|---|---|---|
| name | Ingredient | text | yes |  |
| unit | Unit | select |  | kg, g, l, ml, pcs, pack |
| on_hand | On hand | number | yes |  |
| low_at | Low-stock alert at | number |  |  |

### staff - Staff

| field | label | type | required | options |
|---|---|---|---|---|
| name | Name | text | yes |  |
| role | Role | select | yes | Owner, Manager, Cashier, Chef, Waiter, Helper |
| salary | Monthly salary (₹) | number |  |  |
| phone | Phone | text |  |  |

### feedback - Feedback

| field | label | type | required | options |
|---|---|---|---|---|
| day | Date | date | yes |  |
| rating | Rating (1-5) | number | yes |  |
| comment | Comment | text |  |  |
| status | Status | select |  | open, resolved |

### closings - Cash Closing

| field | label | type | required | options |
|---|---|---|---|---|
| day | Date | date | yes |  |
| expected | Expected cash (₹), auto if blank | number |  |  |
| actual | Cash counted (₹) | number | yes |  |
| note | Note | text |  |  |

Total business fields: 41. Every table also has: id, tenant, deleted, created.

## Routes (all currently UNAUTHENTICATED except for a required X-Tenant header)

| method | path | function |
|---|---|---|
| GET | /api/schema | schema |
| GET | /api/data/{t} | lst |
| POST | /api/data/{t} | add |
| PUT | /api/data/{t}/{i} | upd |
| DELETE | /api/data/{t}/{i} | rm |
| POST | /api/upload | upload |
| GET | /api/report/{t} | report |
| GET | /api/dashboard | dash |
| POST | /api/seed | seed |

Dashboard response keys: kpi{sales, orders, aov, purchases, expenses, wastage, profit, owed, rating}, by_day, spend_day, payments, channels, top_items, expense_cat, weekday, low_stock, cash_diffs, warnings.

## Behaviours that must survive the port

- Required-field and number validation messages (clean()).
- Soft delete; deleted rows excluded from lists, dashboard and CSV.
- Lists newest first (day desc then id desc) and capped at 2000 rows.
- Closing: expected cash auto-fills from that day's cash sales when left blank.
- Dashboard: orders = distinct non-empty bill no, else row id; profit = sales - purchases - expenses (labelled cash-basis); owed = qty*unit_price - paid; low stock = on_hand <= low_at; cash mismatch if |actual-expected| > 0.5.
- Upload whitelist: jpg, jpeg, png, webp, pdf.
- Audit entry on create, update, delete.
- CSV export per section.
- seed endpoint data shape (moves to manage.py seed-demo).

## Known defects fixed by the port

- tenant comes from a client header and ?tenant= URL.
- /uploads is public.
- /api/seed is unauthenticated.
- Frontend 'today' uses UTC.
- Floats for money.
- No unique closing per day.