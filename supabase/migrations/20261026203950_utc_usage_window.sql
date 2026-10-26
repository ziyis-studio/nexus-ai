-- Keep the daily budget on UTC boundaries regardless of session TimeZone.
create or replace function nexus_private.create_analysis(tid uuid, ticket uuid, idem text, model text) returns jsonb
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
    (select count(*) from public.analysis_runs where tenant_id=tid and created_at>(date_trunc('day',now() at time zone 'UTC') at time zone 'UTC'))>=200 then
  raise exception 'USAGE_LIMIT' using errcode='P0001'; end if;
 insert into public.analysis_runs(tenant_id,ticket_id,initiated_by,model_id,idempotency_key,request_hash,ticket_snapshot)
 values(tid,ticket,auth.uid(),model,idem,fingerprint,jsonb_build_object('subject',t.subject,'description',t.description)) returning * into r;
 insert into public.audit_logs(tenant_id,actor_id,action,resource_type,resource_id) values(tid,auth.uid(),'analysis.requested','analysis_runs',r.id);
 return to_jsonb(r)-'ticket_snapshot'-'request_hash'-'lease_token';
end $$;
