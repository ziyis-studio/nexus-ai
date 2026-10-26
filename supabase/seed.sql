-- Tenant records only; identity/account provisioning belongs to scripts/seed.py,
-- which uses the Supabase Auth Admin API rather than fabricating auth users.
insert into public.tenants(id,name,slug) values
 ('10000000-0000-4000-8000-000000000001','Acme Corporation','acme'),
 ('10000000-0000-4000-8000-000000000002','Nova Technologies','nova')
on conflict(id) do nothing;
