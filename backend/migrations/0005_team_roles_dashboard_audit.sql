-- Idempotent where your database was already altered by hand (run_migration.py).
alter table users add column if not exists allowed_sections jsonb default '["*"]'::jsonb;
alter table users add column if not exists allowed_tiles jsonb;                 -- null = legacy rule (derived from sections)
alter table users add column if not exists password_changed_at timestamptz;

-- Owners can now define their own roles, so the fixed role list is replaced by a length rule.
-- Privilege never comes from the label: owner/superadmin are reserved in code and by the check below.
do $$ declare c text; begin
  for c in select conname from pg_constraint where conrelid = 'users'::regclass and contype = 'c'
      and pg_get_constraintdef(oid) ilike '%role%' and pg_get_constraintdef(oid) not ilike '%restaurant_id%' loop
    execute format('alter table users drop constraint %I', c);
  end loop; end $$;
alter table users drop constraint if exists users_role_len;
alter table users add constraint users_role_len check (length(trim(role)) between 2 and 30);

-- Keep today's behaviour for existing accounts: they already see the dashboard and are not forced to change password.
update users set allowed_sections = coalesce(allowed_sections, '[]'::jsonb) || '["dashboard"]'::jsonb
 where role not in ('owner','superadmin') and not (coalesce(allowed_sections,'[]'::jsonb) ? '*') and not (coalesce(allowed_sections,'[]'::jsonb) ? 'dashboard');
update users set must_set_password = false where password_hash is not null;

alter table audit_logs add column if not exists actor_username text, add column if not exists kind text,
  add column if not exists section text, add column if not exists entity_id text, add column if not exists details jsonb;
create index if not exists audit_logs_actor_ix on audit_logs(restaurant_id, actor_user_id, created_at desc);

create table if not exists team_roles(
  id uuid primary key default gen_random_uuid(),
  restaurant_id uuid not null references restaurants(id) on delete cascade,
  name text not null check (length(name) between 2 and 30),
  created_at timestamptz not null default now(), unique (restaurant_id, name));
alter table team_roles enable row level security;
create policy tenant_isolation_policy on team_roles using (restaurant_id = current_restaurant_id()) with check (restaurant_id = current_restaurant_id());
grant select, insert, delete on team_roles to app_user;

update restaurants set name = 'Amber Fort Hotel Operation' where slug = 'demo-dhaba' and name = 'Demo Dhaba';
