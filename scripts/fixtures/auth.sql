-- Minimal identity schema ONLY for isolated native PostgreSQL tests.
-- Production uses Supabase Auth, which owns these tables and functions.
do $$ begin create role anon nologin; exception when duplicate_object then null; end $$;
do $$ begin create role authenticated nologin; exception when duplicate_object then null; end $$;
do $$ begin create role service_role nologin; exception when duplicate_object then null; end $$;
-- Match the hosted grants, including explicit API-role function execution.
alter default privileges in schema public grant execute on functions to anon,authenticated,service_role;
create schema auth;
create table auth.users(id uuid primary key, email text);
create table auth.sessions(id uuid primary key, user_id uuid references auth.users(id));
create function auth.uid() returns uuid language sql stable as $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
create function auth.jwt() returns jsonb language sql stable as $$ select coalesce(nullif(current_setting('request.jwt.claims',true),''),'{}')::jsonb $$;
grant usage on schema auth to authenticated,anon;
grant execute on function auth.uid(),auth.jwt() to authenticated,anon;
