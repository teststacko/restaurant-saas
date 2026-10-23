create table restaurants(
  id uuid primary key default gen_random_uuid(),
  name text not null check (length(trim(name)) > 0),
  slug citext not null unique,
  status text not null default 'active' check (status in ('active','suspended')),
  logo_file_id uuid,
  contact_phone text, contact_email citext,
  currency char(3) not null default 'INR',
  timezone text not null default 'Asia/Kolkata',
  created_at timestamptz not null default now(), updated_at timestamptz not null default now());

create table users(
  id uuid primary key default gen_random_uuid(),
  restaurant_id uuid references restaurants(id) on delete restrict,
  username citext not null unique check (length(username) >= 3),
  email citext,
  full_name text,
  password_hash text,                                   -- null until the user completes setup
  role text not null check (role in ('superadmin','owner','manager','cashier')),
  is_active boolean not null default true,
  must_set_password boolean not null default true,
  theme text not null default 'light' check (theme in ('light','dark')),
  mfa_secret_enc text, mfa_enabled boolean not null default false, mfa_recovery_hashes text[],
  failed_logins int not null default 0, locked_until timestamptz, last_login_at timestamptz,
  created_by uuid references users(id),
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  check ((role = 'superadmin') = (restaurant_id is null)));   -- only superadmins are platform-level
create unique index users_email_uq on users(email) where email is not null;
create index users_restaurant_ix on users(restaurant_id);

create table sessions(
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  token_hash bytea not null unique,                     -- SHA-256 of the cookie token; the token itself is never stored
  created_at timestamptz not null default now(), last_seen_at timestamptz not null default now(),
  expires_at timestamptz not null, revoked_at timestamptz,
  ip inet, user_agent text, mfa_verified_at timestamptz,
  inspecting_restaurant_id uuid references restaurants(id));  -- superadmin support mode
create index sessions_user_ix on sessions(user_id);

create table auth_tokens(
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  purpose text not null check (purpose in ('setup','reset')),
  token_hash bytea not null unique,
  expires_at timestamptz not null, used_at timestamptz,
  created_by uuid references users(id), created_at timestamptz not null default now());
create index auth_tokens_user_ix on auth_tokens(user_id);

create table rate_limits(
  key text not null, window_start timestamptz not null, hits int not null default 1,
  primary key (key, window_start));
