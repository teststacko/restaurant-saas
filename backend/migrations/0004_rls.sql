-- Migration 0004: Row Level Security Policies for Multi-Tenant Isolation

-- Helper function to read current transaction session restaurant_id
CREATE OR REPLACE FUNCTION current_restaurant_id() RETURNS uuid AS $$
    SELECT nullif(current_setting('app.restaurant_id', true), '')::uuid;
$$ LANGUAGE sql STABLE;

-- Enable RLS and define isolation policies
DO $$
DECLARE
    tbl text;
BEGIN
    FOR tbl IN SELECT unnest(ARRAY['sales', 'purchases', 'inventory', 'expenses', 'closings', 'staff', 'wastage', 'feedback', 'audit_logs'])
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY;', tbl);
        EXECUTE format('DROP POLICY IF EXISTS tenant_isolation_policy ON %I;', tbl);
        EXECUTE format('CREATE POLICY tenant_isolation_policy ON %I USING (restaurant_id = current_restaurant_id()) WITH CHECK (restaurant_id = current_restaurant_id());', tbl);
    END LOOP;
END $$;
