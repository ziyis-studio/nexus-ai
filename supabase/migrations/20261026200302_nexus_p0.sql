-- NEXUS AI P0. Public entrypoints are invoker functions; privileged commands
-- live in the unexposed nexus_private schema and bind actor to auth.uid().
create schema if not exists nexus_private;
revoke all on schema nexus_private from public;
grant usage on schema nexus_private to authenticated;
do $$ begin create role nexus_worker nologin; exception when duplicate_object then null; end $$;
grant nexus_worker to postgres;

create table public.tenants (
 id uuid primary key default gen_random_uuid(), name varchar(150) not null,
 slug varchar(100) not null unique, created_at timestamptz not null default now()
);
create table public.memberships (
 tenant_id uuid not null references public.tenants(id), user_id uuid not null references auth.users(id),
 role text not null check(role in ('admin','agent','viewer')), is_active boolean not null default true,
 created_at timestamptz not null default now(), primary key(tenant_id,user_id)
);
create index memberships_user on public.memberships(user_id,tenant_id);
create table public.tickets (
 id uuid primary key default gen_random_uuid(), tenant_id uuid not null references public.tenants(id),
 subject varchar(200) not null check(length(trim(subject)) between 3 and 200),
 description text not null check(length(trim(description)) between 10 and 10000),
 customer_name varchar(150), customer_email varchar(254), external_reference varchar(200),
 status text not null default 'open' check(status in ('open','in_progress','resolved','closed')),
 priority text not null default 'normal' check(priority in ('low','normal','high','urgent')),
 created_by uuid not null default auth.uid() references auth.users(id),
 created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
 unique(tenant_id,id)
);
create index tickets_page on public.tickets(tenant_id,created_at desc,id desc);
create index tickets_status_page on public.tickets(tenant_id,status,created_at desc,id desc);
create index tickets_priority on public.tickets(tenant_id,priority);
create table public.knowledge_docs (
 id uuid primary key default gen_random_uuid(), tenant_id uuid not null references public.tenants(id),
 title varchar(200) not null check(length(trim(title)) between 3 and 200),
 content text not null check(length(trim(content)) between 10 and 50000),
 document_type text not null check(document_type in ('faq','policy','product_information','general_reference')),
 is_active boolean not null default true, created_by uuid not null default auth.uid() references auth.users(id),
 created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
 search_vector tsvector generated always as (to_tsvector('simple', title || ' ' || content)) stored,
 unique(tenant_id,id)
);
create index knowledge_active on public.knowledge_docs(tenant_id,is_active);
create index knowledge_fts on public.knowledge_docs using gin(search_vector);
create table public.analysis_runs (
 id uuid primary key default gen_random_uuid(), tenant_id uuid not null references public.tenants(id),
 ticket_id uuid not null, initiated_by uuid not null references auth.users(id),
 status text not null default 'queued' check(status in ('queued','processing','succeeded','failed')),
 model_id varchar(150) not null, idempotency_key varchar(150), request_hash varchar(128) not null,
 ticket_snapshot jsonb not null, attempt_count integer not null default 0 check(attempt_count >= 0),
 worker_lease_until timestamptz, lease_token uuid, error_code varchar(100), error_message varchar(500),
 created_at timestamptz not null default now(), started_at timestamptz, completed_at timestamptz,
 unique(tenant_id,id), unique(tenant_id,initiated_by,idempotency_key),
 foreign key(tenant_id,ticket_id) references public.tickets(tenant_id,id)
);
create index runs_ticket on public.analysis_runs(tenant_id,ticket_id,created_at desc);
create index runs_page on public.analysis_runs(tenant_id,created_at desc,id desc);
create index runs_recovery on public.analysis_runs(status,worker_lease_until,created_at);
create table public.ai_results (
 id uuid primary key default gen_random_uuid(), tenant_id uuid not null references public.tenants(id),
 run_id uuid not null unique,
 category text not null check(category in ('billing','delivery','technical','account','general','other')),
 suggested_priority text not null check(suggested_priority in ('low','normal','high','urgent')),
 sentiment text not null check(sentiment in ('positive','neutral','negative')),
 summary text not null check(length(summary) between 1 and 2000),
 suggested_reply text not null check(length(suggested_reply) between 1 and 6000),
 reasoning_summary text not null check(length(reasoning_summary) between 1 and 1000),
 source_document_ids jsonb not null default '[]' check(jsonb_typeof(source_document_ids)='array'),
 needs_human_review boolean not null default true,
 review_status text not null default 'pending' check(review_status in ('pending','approved','rejected')),
 reviewed_by uuid references auth.users(id), reviewed_at timestamptz,
 created_at timestamptz not null default now(),
 foreign key(tenant_id,run_id) references public.analysis_runs(tenant_id,id)
);
create index results_tenant_run on public.ai_results(tenant_id,run_id);
create table public.audit_logs (
 id uuid primary key default gen_random_uuid(), tenant_id uuid not null references public.tenants(id),
 actor_id uuid references auth.users(id), action varchar(100) not null,
 resource_type varchar(100) not null, resource_id uuid, metadata jsonb not null default '{}',
 created_at timestamptz not null default now()
);
create index audit_page on public.audit_logs(tenant_id,created_at desc,id desc);

-- Membership helpers cannot select a supplied identity or expose membership rows.
create function nexus_private.has_role(tid uuid, roles text[]) returns boolean
language sql stable security definer set search_path = '' as $$
 select auth.uid() is not null and exists(select 1 from public.memberships m
 where m.tenant_id=tid and m.user_id=auth.uid() and m.is_active and m.role=any(roles))
$$;
revoke all on function nexus_private.has_role(uuid,text[]) from public;
grant execute on function nexus_private.has_role(uuid,text[]) to authenticated;

alter table public.tenants enable row level security;
alter table public.memberships enable row level security;
alter table public.tickets enable row level security;
alter table public.knowledge_docs enable row level security;
alter table public.analysis_runs enable row level security;
alter table public.ai_results enable row level security;
alter table public.audit_logs enable row level security;
create policy tenant_read on public.tenants for select to authenticated using(nexus_private.has_role(id,array['admin','agent','viewer']));
create policy membership_read on public.memberships for select to authenticated using(
 (user_id=auth.uid() and is_active) or nexus_private.has_role(tenant_id,array['admin']));
create policy ticket_read on public.tickets for select to authenticated using(nexus_private.has_role(tenant_id,array['admin','agent','viewer']));
create policy ticket_insert on public.tickets for insert to authenticated with check(
 nexus_private.has_role(tenant_id,array['admin','agent']) and created_by=auth.uid() and status='open' and priority='normal');
create policy ticket_update on public.tickets for update to authenticated using(nexus_private.has_role(tenant_id,array['admin','agent'])) with check(nexus_private.has_role(tenant_id,array['admin','agent']));
create policy doc_read on public.knowledge_docs for select to authenticated using(nexus_private.has_role(tenant_id,array['admin','agent','viewer']));
create policy doc_insert on public.knowledge_docs for insert to authenticated with check(nexus_private.has_role(tenant_id,array['admin']) and created_by=auth.uid());
create policy doc_update on public.knowledge_docs for update to authenticated using(nexus_private.has_role(tenant_id,array['admin'])) with check(nexus_private.has_role(tenant_id,array['admin']));
create policy run_read on public.analysis_runs for select to authenticated using(nexus_private.has_role(tenant_id,array['admin','agent','viewer']));
create policy result_read on public.ai_results for select to authenticated using(nexus_private.has_role(tenant_id,array['admin','agent','viewer']));
create policy audit_read on public.audit_logs for select to authenticated using(nexus_private.has_role(tenant_id,array['admin']));
revoke all on public.tenants,public.memberships,public.tickets,public.knowledge_docs,public.analysis_runs,public.ai_results,public.audit_logs from anon,authenticated;
grant select on public.tenants,public.memberships,public.tickets,public.analysis_runs,public.ai_results,public.audit_logs to authenticated;
grant select(id,tenant_id,title,content,document_type,is_active,created_by,created_at,updated_at) on public.knowledge_docs to authenticated;
grant insert(tenant_id,subject,description,customer_name,customer_email,external_reference) on public.tickets to authenticated;
grant update(subject,description,status,priority,customer_name,customer_email,external_reference) on public.tickets to authenticated;
grant insert(tenant_id,title,content,document_type,is_active) on public.knowledge_docs to authenticated;
grant update(title,content,document_type,is_active) on public.knowledge_docs to authenticated;

create function nexus_private.guard_ticket() returns trigger language plpgsql security invoker set search_path='' as $$
begin
 if new.tenant_id<>old.tenant_id or new.id<>old.id or new.created_by<>old.created_by or new.created_at<>old.created_at then
  raise exception 'IMMUTABLE_IDENTITY' using errcode='23514';
 end if;
 if new.status<>old.status and not (
  (old.status='open' and new.status in ('in_progress','resolved')) or
  (old.status='in_progress' and new.status='resolved') or
  (old.status='resolved' and new.status in ('closed','open')) or
  (old.status='closed' and new.status='open' and nexus_private.has_role(old.tenant_id,array['admin']))
 ) then raise exception 'INVALID_TRANSITION' using errcode='23514'; end if;
 new.updated_at=now(); return new;
end $$;
create trigger guard_ticket before update on public.tickets for each row execute function nexus_private.guard_ticket();
create function nexus_private.touch_doc() returns trigger language plpgsql set search_path='' as $$
begin
 if new.tenant_id<>old.tenant_id or new.id<>old.id or new.created_by<>old.created_by or new.created_at<>old.created_at then
  raise exception 'IMMUTABLE_IDENTITY' using errcode='23514'; end if;
 new.updated_at=now(); return new;
end $$;
create trigger touch_doc before update on public.knowledge_docs for each row execute function nexus_private.touch_doc();

-- Trigger-only privilege: no caller-provided audit text, credentials or ticket content.
create function nexus_private.audit_change() returns trigger language plpgsql security definer set search_path='' as $$
declare action_name text; begin
 action_name=case when tg_table_name='tickets' then 'ticket.' when tg_table_name='knowledge_docs' then 'knowledge.' else 'result.' end;
 action_name=action_name || case when tg_op='INSERT' then 'created' when tg_table_name='ai_results' then to_jsonb(new)->>'review_status' else 'updated' end;
 insert into public.audit_logs(tenant_id,actor_id,action,resource_type,resource_id,metadata)
 values(new.tenant_id,auth.uid(),action_name,tg_table_name,new.id,'{}');
 return new;
end $$;
revoke all on function nexus_private.audit_change() from public,authenticated;
create trigger audit_ticket after insert or update on public.tickets for each row execute function nexus_private.audit_change();
create trigger audit_doc after insert or update on public.knowledge_docs for each row execute function nexus_private.audit_change();
create trigger audit_review after update on public.ai_results for each row when(old.review_status is distinct from new.review_status) execute function nexus_private.audit_change();

-- Atomic idempotency, quota, snapshot and outbox record in one DB transaction.
create function nexus_private.create_analysis(tid uuid, ticket uuid, idem text, model text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare t public.tickets; r public.analysis_runs; fingerprint text;
begin
 if not nexus_private.has_role(tid,array['admin','agent']) then raise insufficient_privilege using message='TENANT_ACCESS_DENIED'; end if;
 if length(idem)>150 or length(idem)<1 or length(model)>150 then raise check_violation using message='INVALID_INPUT'; end if;
 perform pg_advisory_xact_lock(hashtextextended(tid::text,0));
 select * into t from public.tickets where tenant_id=tid and id=ticket;
 if not found then raise no_data_found using message='NOT_FOUND'; end if;
 fingerprint=md5(ticket::text || ':' || model);
 select * into r from public.analysis_runs where tenant_id=tid and initiated_by=auth.uid() and idempotency_key=idem;
 if found then
  if r.request_hash<>fingerprint then raise unique_violation using message='IDEMPOTENCY_CONFLICT'; end if;
  return to_jsonb(r)-'ticket_snapshot'-'request_hash'-'lease_token';
 end if;
 if (select count(*) from public.analysis_runs where tenant_id=tid and status in ('queued','processing'))>=10 or
    (select count(*) from public.analysis_runs where tenant_id=tid and created_at>now()-interval '1 minute')>=20 or
    (select count(*) from public.analysis_runs where tenant_id=tid and created_at>date_trunc('day',now()))>=200 then
  raise exception 'USAGE_LIMIT' using errcode='P0001'; end if;
 insert into public.analysis_runs(tenant_id,ticket_id,initiated_by,model_id,idempotency_key,request_hash,ticket_snapshot)
 values(tid,ticket,auth.uid(),model,idem,fingerprint,jsonb_build_object('subject',t.subject,'description',t.description)) returning * into r;
 insert into public.audit_logs(tenant_id,actor_id,action,resource_type,resource_id) values(tid,auth.uid(),'analysis.requested','analysis_runs',r.id);
 return to_jsonb(r)-'ticket_snapshot'-'request_hash'-'lease_token';
end $$;
revoke all on function nexus_private.create_analysis(uuid,uuid,text,text) from public;
grant execute on function nexus_private.create_analysis(uuid,uuid,text,text) to authenticated;
create function public.create_analysis(tid uuid, ticket uuid, idem text, model text) returns jsonb
language sql security invoker set search_path='' as $$ select nexus_private.create_analysis(tid,ticket,idem,model) $$;
revoke all on function public.create_analysis(uuid,uuid,text,text) from public;
grant execute on function public.create_analysis(uuid,uuid,text,text) to authenticated;

create function nexus_private.review_analysis(tid uuid, run uuid, decision text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare result public.ai_results; begin
 if not nexus_private.has_role(tid,array['admin','agent']) then raise insufficient_privilege using message='TENANT_ACCESS_DENIED'; end if;
 if decision not in ('approved','rejected') then raise check_violation using message='INVALID_INPUT'; end if;
 select * into result from public.ai_results where tenant_id=tid and run_id=run for update;
 if not found then raise no_data_found using message='NOT_FOUND'; end if;
 if result.review_status=decision then return to_jsonb(result); end if;
 if result.review_status<>'pending' then raise unique_violation using message='REVIEW_FINAL'; end if;
 update public.ai_results set review_status=decision,reviewed_by=auth.uid(),reviewed_at=now()
 where id=result.id returning * into result;
 return to_jsonb(result);
end $$;
revoke all on function nexus_private.review_analysis(uuid,uuid,text) from public;
grant execute on function nexus_private.review_analysis(uuid,uuid,text) to authenticated;
create function public.review_analysis(tid uuid, run uuid, decision text) returns jsonb
language sql security invoker set search_path='' as $$ select nexus_private.review_analysis(tid,run,decision) $$;
revoke all on function public.review_analysis(uuid,uuid,text) from public;
grant execute on function public.review_analysis(uuid,uuid,text) to authenticated;

-- Worker role is not a Data API or login role. Explicit policies permit its
-- background access; Python still binds every query to tenant + resource IDs.
grant usage on schema public to nexus_worker;
grant select on public.tickets,public.knowledge_docs,public.memberships,public.analysis_runs,public.ai_results to nexus_worker;
grant update(status,attempt_count,worker_lease_until,lease_token,error_code,error_message,started_at,completed_at) on public.analysis_runs to nexus_worker;
grant insert on public.ai_results,public.audit_logs to nexus_worker;
create policy worker_ticket on public.tickets for select to nexus_worker using(true);
create policy worker_doc on public.knowledge_docs for select to nexus_worker using(true);
create policy worker_members on public.memberships for select to nexus_worker using(true);
create policy worker_run_read on public.analysis_runs for select to nexus_worker using(true);
create policy worker_run_update on public.analysis_runs for update to nexus_worker using(true) with check(true);
create policy worker_result_read on public.ai_results for select to nexus_worker using(true);
create policy worker_result_insert on public.ai_results for insert to nexus_worker with check(true);
create policy worker_audit on public.audit_logs for insert to nexus_worker with check(true);

create function nexus_private.guard_run() returns trigger language plpgsql set search_path='' as $$
begin
 if old.status in ('succeeded','failed') then raise check_violation using message='RUN_TERMINAL'; end if;
 if (new.status<>old.status) and not ((old.status='queued' and new.status in ('processing','failed')) or
 (old.status='processing' and new.status in ('succeeded','failed'))) then raise check_violation using message='INVALID_RUN_TRANSITION'; end if;
 return new;
end $$;
create trigger guard_run before update on public.analysis_runs for each row execute function nexus_private.guard_run();

-- Results must refer only to active knowledge from their tenant; clients cannot
-- introduce fabricated references even if a model hallucinates document IDs.
create function nexus_private.validate_sources() returns trigger language plpgsql security invoker set search_path='' as $$
begin
 if exists(select 1 from jsonb_array_elements_text(new.source_document_ids) s
 where not exists(select 1 from public.knowledge_docs d where d.id=s::uuid and d.tenant_id=new.tenant_id and d.is_active))
 then raise check_violation using message='INVALID_SOURCE'; end if;
 return new;
end $$;
create trigger validate_sources before insert on public.ai_results for each row execute function nexus_private.validate_sources();

-- Nothing in the private schema may be executed through PUBLIC inheritance.
revoke all on function nexus_private.guard_ticket(),nexus_private.touch_doc(),nexus_private.guard_run(),nexus_private.validate_sources() from public;

create function nexus_private.session_active() returns boolean
language sql stable security definer set search_path='' as $$
 select auth.uid() is not null and exists(select 1 from auth.sessions s
 where s.id=(auth.jwt()->>'session_id')::uuid and s.user_id=auth.uid())
$$;
revoke all on function nexus_private.session_active() from public;
grant execute on function nexus_private.session_active() to authenticated;
create function public.session_active() returns boolean language sql stable security invoker set search_path='' as $$ select nexus_private.session_active() $$;
revoke all on function public.session_active() from public;
grant execute on function public.session_active() to authenticated;
