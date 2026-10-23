-- Migration 0003: Core Restaurant Business Tables & Audit Log

-- 1. Sales
CREATE TABLE sales (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    restaurant_id uuid NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
    deleted boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    day date NOT NULL DEFAULT current_date,
    item text NOT NULL,
    qty numeric(10, 2) NOT NULL DEFAULT 1,
    amount numeric(12, 2) NOT NULL DEFAULT 0.00,
    method text NOT NULL DEFAULT 'cash',
    channel text NOT NULL DEFAULT 'dine-in',
    ref text
);
CREATE INDEX sales_restaurant_day_idx ON sales(restaurant_id, day);

-- 2. Purchases
CREATE TABLE purchases (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    restaurant_id uuid NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
    deleted boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    day date NOT NULL DEFAULT current_date,
    supplier text NOT NULL,
    item text NOT NULL,
    unit text NOT NULL DEFAULT 'kg',
    qty numeric(10, 2) NOT NULL DEFAULT 1,
    unit_price numeric(12, 2) NOT NULL DEFAULT 0.00,
    paid numeric(12, 2) NOT NULL DEFAULT 0.00,
    bill text
);
CREATE INDEX purchases_restaurant_day_idx ON purchases(restaurant_id, day);

-- 3. Inventory
CREATE TABLE inventory (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    restaurant_id uuid NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
    deleted boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    name text NOT NULL,
    unit text NOT NULL DEFAULT 'kg',
    on_hand numeric(10, 2) NOT NULL DEFAULT 0.00,
    low_at numeric(10, 2) NOT NULL DEFAULT 0.00
);
CREATE INDEX inventory_restaurant_idx ON inventory(restaurant_id);

-- 4. Expenses
CREATE TABLE expenses (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    restaurant_id uuid NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
    deleted boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    day date NOT NULL DEFAULT current_date,
    category text NOT NULL,
    amount numeric(12, 2) NOT NULL DEFAULT 0.00,
    note text,
    bill text
);
CREATE INDEX expenses_restaurant_day_idx ON expenses(restaurant_id, day);

-- 5. Closings
CREATE TABLE closings (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    restaurant_id uuid NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
    deleted boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    day date NOT NULL DEFAULT current_date,
    expected numeric(12, 2) NOT NULL DEFAULT 0.00,
    actual numeric(12, 2) NOT NULL DEFAULT 0.00,
    note text
);
CREATE INDEX closings_restaurant_day_idx ON closings(restaurant_id, day);

-- 6. Staff
CREATE TABLE staff (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    restaurant_id uuid NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
    deleted boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    name text NOT NULL,
    role text NOT NULL,
    salary numeric(12, 2) NOT NULL DEFAULT 0.00,
    phone text
);
CREATE INDEX staff_restaurant_idx ON staff(restaurant_id);

-- 7. Wastage
CREATE TABLE wastage (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    restaurant_id uuid NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
    deleted boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    day date NOT NULL DEFAULT current_date,
    item text NOT NULL,
    qty numeric(10, 2) NOT NULL DEFAULT 1,
    unit_cost numeric(12, 2) NOT NULL DEFAULT 0.00,
    reason text
);
CREATE INDEX wastage_restaurant_day_idx ON wastage(restaurant_id, day);

-- 8. Feedback
CREATE TABLE feedback (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    restaurant_id uuid NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
    deleted boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    day date NOT NULL DEFAULT current_date,
    rating numeric(3, 1) NOT NULL DEFAULT 5.0,
    comment text,
    status text NOT NULL DEFAULT 'new'
);
CREATE INDEX feedback_restaurant_day_idx ON feedback(restaurant_id, day);

-- 9. Audit Logs
CREATE TABLE audit_logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    restaurant_id uuid NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
    actor_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    action text NOT NULL
);
CREATE INDEX audit_logs_restaurant_idx ON audit_logs(restaurant_id, created_at);

-- Grants for app_user
GRANT SELECT, INSERT, UPDATE, DELETE ON sales, purchases, inventory, expenses, closings, staff, wastage, feedback TO app_user;
GRANT SELECT, INSERT ON audit_logs TO app_user;
