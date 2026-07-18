# Supabase Guide

Correct patterns for Supabase projects. Follow these when writing migrations, functions, RLS policies, auth hooks, or seed data.

---

## Database Functions

**Always set `search_path` to empty and use fully qualified names:**

```sql
create or replace function public.my_function()
returns void
language plpgsql
security invoker
set search_path = ''
as $$
begin
  insert into public.my_table (col) values ('val');
end;
$$;
```

Without explicit `search_path`, Postgres resolves object names against untrusted schemas — a privilege escalation vector with `security definer` functions.

**Default to `security invoker`**. Use `security definer` only when the function must bypass RLS (e.g., reading a roles table from an auth hook).

---

## Auth Hooks

**Auth hook functions must use `security definer` + empty `search_path`:**

```sql
create or replace function public.custom_access_token_hook(event jsonb)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  user_role public.app_role;
begin
  select role into user_role
  from public.user_roles
  where user_id = (event->>'user_id')::uuid;

  -- Add role to claims
  event := jsonb_set(
    event,
    '{claims,app_role}',
    to_jsonb(user_role::text)
  );

  return event;
end;
$$;
```

Why `security definer`: the hook runs as `supabase_auth_admin`, which has no access to your public tables or their RLS policies. `security definer` executes as the function owner (`postgres`), bypassing RLS.

Why empty `search_path`: `supabase_auth_admin` has a different default `search_path` that won't resolve your custom types (e.g., `app_role` enum). Always qualify with schema: `public.app_role`, `public.user_roles`.

**Grant/revoke correctly:**

```sql
grant execute on function public.custom_access_token_hook to supabase_auth_admin;
revoke execute on function public.custom_access_token_hook from authenticated, anon, public;
```

---

## RLS Policies

**Wrap function calls in `(select ...)` for performance:**

```sql
-- Correct: function evaluated once via initPlan
create policy "users own rows" on public.posts
  for select to authenticated
  using (user_id = (select auth.uid()));

-- For role-check functions:
create policy "admins only" on public.settings
  for all to authenticated
  using ((select public.is_admin()));
```

The `(select ...)` wrapper causes the optimizer to cache the result instead of calling the function per-row. On 100K+ row tables this is 10-100x faster.

**Always specify the role with `TO`:**

```sql
create policy "read own" on public.profiles
  for select to authenticated  -- not 'public', not omitted
  using (user_id = (select auth.uid()));
```

Omitting `TO` defaults to `public` (all roles including `anon`), which evaluates `auth.uid()` unnecessarily for anonymous requests.

**Index columns used in RLS:**

```sql
create index idx_posts_user_id on public.posts using btree (user_id);
```

Without an index, RLS with `auth.uid() = user_id` forces a sequential scan on every query.

**Prefer row-column IN fixed-set over fixed-value IN row-subquery:**

```sql
-- Correct: get user's teams once, filter main table by index
create policy "team access" on public.projects
  for select to authenticated
  using (team_id in (select public.get_user_teams()));
```

Not: `auth.uid() in (select user_id from team_members where team_id = projects.team_id)` — this runs the subquery per row.

---

## Seed Data (auth.users)

**Never leave string columns NULL — use empty strings:**

```sql
insert into auth.users (
  id, email, encrypted_password,
  email_confirmed_at, created_at, updated_at,
  raw_app_meta_data, raw_user_meta_data,
  confirmation_token, recovery_token, email_change_token_new,
  email_change, phone_change, reauthentication_token
) values (
  gen_random_uuid(), 'user@test.local',
  crypt('password123', gen_salt('bf')),
  now(), now(), now(),
  '{"provider":"email","providers":["email"]}'::jsonb, '{}'::jsonb,
  '', '', '',
  '', '', ''
);
```

GoTrue (written in Go) scans these columns into Go `string` types. NULL → string scan fails with: `converting NULL to string is unsupported`. Always provide `''` for token/change columns.

**Always include an `identities` row:**

```sql
insert into auth.identities (
  id, user_id, provider_id, provider,
  identity_data, last_sign_in_at, created_at, updated_at
) values (
  gen_random_uuid(), '<user-uuid>', '<user-email>', 'email',
  jsonb_build_object('sub', '<user-uuid>', 'email', '<user-email>'),
  now(), now(), now()
);
```

Without an identity row, sign-in via the auth API fails silently.

---

## Migrations

**One concern per migration file.** Don't mix schema changes with RLS policies with seed data.

**Auth hook migrations must include grants in the same file:**

```sql
-- 001_auth_hook.sql
create or replace function public.custom_access_token_hook(event jsonb) ...;

grant execute on function public.custom_access_token_hook to supabase_auth_admin;
grant usage on schema public to supabase_auth_admin;
revoke execute on function public.custom_access_token_hook from authenticated, anon, public;
```

If grants are in a separate migration that fails, the hook silently does nothing.

**Enable RLS explicitly on every new table:**

```sql
create table public.posts ( ... );
alter table public.posts enable row level security;
```

Tables created via SQL (not the dashboard Table Editor) do NOT get RLS enabled automatically. Without RLS, the table is fully exposed via the public API.
