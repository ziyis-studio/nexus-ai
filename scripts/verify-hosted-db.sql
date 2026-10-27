-- Run as the project's database administrator after applying all migrations.
-- This verifies real PostgreSQL roles and Supabase auth.uid(), using request
-- claims supplied by the test. It does not verify Auth login or JWT signatures.
-- All fixture identities, business records and audit entries are rolled back.
begin;
do $smoke$
declare
 a uuid := gen_random_uuid(); b uuid := gen_random_uuid();
 admin_id uuid := gen_random_uuid(); agent_id uuid := gen_random_uuid();
 viewer_id uuid := gen_random_uuid(); outsider_id uuid := gen_random_uuid();
 ticket_a uuid := gen_random_uuid(); ticket_b uuid := gen_random_uuid();
 doc_a uuid := gen_random_uuid(); doc_b uuid := gen_random_uuid();
 run_id uuid; result_id uuid; response jsonb; repeated jsonb; affected integer;
begin
 if (select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace
     where n.nspname='public' and c.relkind='r' and c.relname=any(array[
      'tenants','memberships','tickets','knowledge_docs','analysis_runs','ai_results','audit_logs'])
     and c.relrowsecurity)<>7 then raise exception 'RLS coverage failed'; end if;
 if has_table_privilege('anon','public.tickets','SELECT')
    or has_table_privilege('authenticated','public.tickets','DELETE')
    or has_table_privilege('authenticated','public.analysis_runs','INSERT')
    or has_table_privilege('authenticated','public.ai_results','UPDATE')
    or has_schema_privilege('anon','nexus_private','USAGE')
    or has_function_privilege('anon','public.create_analysis(uuid,uuid,text,text)','EXECUTE')
    or exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
      where n.nspname='public' and p.proname in('create_analysis','review_analysis','session_active')
      and (has_function_privilege('anon',p.oid,'EXECUTE')
        or has_function_privilege('service_role',p.oid,'EXECUTE')))
    or has_function_privilege('authenticated','nexus_private.audit_change()','EXECUTE')
    or has_column_privilege('nexus_worker','public.memberships','role','UPDATE')
    or (select rolbypassrls or rolcanlogin from pg_roles where rolname='nexus_worker')
 then raise exception 'Privilege contract failed'; end if;

 -- FK-only test identities are never committed as real Auth accounts.
 insert into auth.users(id) values(admin_id),(agent_id),(viewer_id),(outsider_id);
 insert into public.tenants(id,name,slug) values
  (a,'Rollback test A','rollback-'||a),(b,'Rollback test B','rollback-'||b);
 insert into public.memberships(tenant_id,user_id,role) values
  (a,admin_id,'admin'),(b,admin_id,'admin'),(a,agent_id,'agent'),(a,viewer_id,'viewer');
 insert into public.tickets(id,tenant_id,subject,description,created_by) values
  (ticket_a,a,'Rollback test A','Temporary isolated ticket for database verification.',admin_id),
  (ticket_b,b,'Rollback test B','Temporary foreign ticket for database verification.',admin_id);
 insert into public.knowledge_docs(id,tenant_id,title,content,document_type,created_by) values
  (doc_a,a,'Rollback policy A','Temporary policy for rollback verification.','policy',admin_id),
  (doc_b,b,'Rollback policy B','Temporary foreign policy for rollback verification.','policy',admin_id);

 perform set_config('request.jwt.claim.sub',agent_id::text,true);
 perform set_config('request.jwt.claims',jsonb_build_object('sub',agent_id,'role','authenticated')::text,true);
 set local role authenticated;
 if (select count(*) from public.tickets where tenant_id in(a,b))<>1
    or (select count(id) from public.knowledge_docs where tenant_id in(a,b))<>1
    or (select count(*) from public.tenants where id in(a,b))<>1
 then raise exception 'Agent tenant isolation failed'; end if;
 update public.tickets set subject='Foreign edit must fail' where id=ticket_b;
 get diagnostics affected = row_count;
 if affected<>0 then raise exception 'Cross-tenant update was allowed'; end if;
 begin
  insert into public.tickets(tenant_id,subject,description)
   values(b,'Forbidden cross tenant','This cross-tenant insertion must be denied.');
  raise exception 'Cross-tenant insert was allowed';
 exception when insufficient_privilege then null; end;
 begin
  insert into public.knowledge_docs(tenant_id,title,content,document_type)
   values(a,'Forbidden agent policy','Only admins can create a policy.','policy');
  raise exception 'Agent knowledge insert was allowed';
 exception when insufficient_privilege then null; end;
 response := public.create_analysis(a,ticket_a,'rollback-smoke','rollback-model');
 run_id := (response->>'id')::uuid;
 if run_id is null or response->>'status'<>'queued'
    or response ?| array['ticket_snapshot','request_hash','lease_token']
 then raise exception 'Enqueue response contract failed'; end if;
 repeated := public.create_analysis(a,ticket_a,'rollback-smoke','rollback-model');
 if repeated->>'id'<>run_id::text then raise exception 'Idempotency replay failed'; end if;
 begin
  perform public.create_analysis(a,ticket_a,'rollback-smoke','different-model');
  raise exception 'Idempotency conflict was accepted';
 exception when unique_violation then null; end;

 reset role;
 perform set_config('request.jwt.claim.sub',viewer_id::text,true);
 perform set_config('request.jwt.claims',jsonb_build_object('sub',viewer_id,'role','authenticated')::text,true);
 set local role authenticated;
 if (select count(*) from public.tickets where tenant_id in(a,b))<>1
 then raise exception 'Viewer visibility failed'; end if;
 begin
  insert into public.tickets(tenant_id,subject,description)
   values(a,'Forbidden viewer write','A viewer cannot create a new support ticket.');
  raise exception 'Viewer write was allowed';
 exception when insufficient_privilege then null; end;
 begin
  perform public.create_analysis(a,ticket_a,'viewer-smoke','rollback-model');
  raise exception 'Viewer enqueue was allowed';
 exception when insufficient_privilege then null; end;

 reset role;
 perform set_config('request.jwt.claim.sub',outsider_id::text,true);
 perform set_config('request.jwt.claims',jsonb_build_object('sub',outsider_id,'role','authenticated',
  'user_metadata',jsonb_build_object('role','admin','tenant_id',a))::text,true);
 set local role authenticated;
 if exists(select 1 from public.tickets where tenant_id in(a,b))
    or exists(select 1 from public.tenants where id in(a,b))
 then raise exception 'Forged metadata granted tenant access'; end if;
 begin
  perform public.create_analysis(a,ticket_a,'outsider-smoke','rollback-model');
  raise exception 'Outsider enqueue was allowed';
 exception when insufficient_privilege then null; end;
 if public.session_active() then raise exception 'Nonexistent session was accepted'; end if;

 reset role;
 perform set_config('request.jwt.claim.sub','',true);
 perform set_config('request.jwt.claims','{}',true);
 set local role nexus_worker;
 update public.analysis_runs set status='processing',attempt_count=1,lease_token=gen_random_uuid()
  where id=run_id and tenant_id=a;
 get diagnostics affected = row_count;
 if affected<>1 then raise exception 'Worker claim failed'; end if;
 begin
  insert into public.ai_results(tenant_id,run_id,category,suggested_priority,sentiment,
   summary,suggested_reply,reasoning_summary,source_document_ids)
  values(a,run_id,'delivery','normal','neutral','Rollback summary','Rollback reply',
   'Rollback reasoning',jsonb_build_array(doc_b));
  raise exception 'Foreign source document was accepted';
 exception when check_violation then null; end;
 insert into public.ai_results(tenant_id,run_id,category,suggested_priority,sentiment,
  summary,suggested_reply,reasoning_summary,source_document_ids)
 values(a,run_id,'delivery','normal','neutral','Rollback summary','Rollback reply',
  'Rollback reasoning',jsonb_build_array(doc_a)) returning id into result_id;
 update public.analysis_runs set status='succeeded',completed_at=now() where id=run_id and tenant_id=a;
 begin
  update public.analysis_runs set error_message='Forbidden terminal edit' where id=run_id;
  raise exception 'Terminal run mutation was accepted';
 exception when check_violation then null; end;
 begin
  update public.ai_results set review_status='approved' where id=result_id;
  raise exception 'Worker review was allowed';
 exception when insufficient_privilege then null; end;

 reset role;
 perform set_config('request.jwt.claim.sub',agent_id::text,true);
 perform set_config('request.jwt.claims',jsonb_build_object('sub',agent_id,'role','authenticated')::text,true);
 set local role authenticated;
 response := public.review_analysis(a,run_id,'approved');
 repeated := public.review_analysis(a,run_id,'approved');
 if response->>'reviewed_by'<>agent_id::text or response<>repeated
 then raise exception 'Review actor or replay failed'; end if;
 begin
  perform public.review_analysis(a,run_id,'rejected');
  raise exception 'Final review was reversed';
 exception when unique_violation then null; end;

 reset role;
 if (select count(*) from public.audit_logs where tenant_id=a
     and resource_id=result_id and action='result.approved')<>1
 then raise exception 'Review audit was not exactly once'; end if;
 update public.memberships set is_active=false where tenant_id=a and user_id=agent_id;
 set local role authenticated;
 if exists(select 1 from public.tickets where tenant_id=a)
 then raise exception 'Revoked membership still reads tickets'; end if;
 begin
  perform public.create_analysis(a,ticket_a,'rollback-smoke','rollback-model');
  raise exception 'Revoked membership still enqueues';
 exception when insufficient_privilege then null; end;

 reset role;
 set local role anon;
 begin
  perform id from public.tickets limit 1;
  raise exception 'Anonymous ticket access was allowed';
 exception when insufficient_privilege then null; end;
 reset role;
end
$smoke$;
rollback;
select 'passed' as hosted_database_smoke, 'all test fixtures rolled back' as cleanup;
