-- Cover the actor foreign keys so user lifecycle checks do not scan every row.
create index tickets_created_by on public.tickets(created_by);
create index knowledge_created_by on public.knowledge_docs(created_by);
create index runs_initiated_by on public.analysis_runs(initiated_by);
create index results_reviewed_by on public.ai_results(reviewed_by);
create index audit_actor on public.audit_logs(actor_id);

-- Evaluate the request identity once per statement. Tenant and role checks
-- remain row-dependent and keep the existing authorization semantics.
alter policy membership_read on public.memberships using (
 (user_id=(select auth.uid()) and is_active)
 or nexus_private.has_role(tenant_id,array['admin'])
);
alter policy ticket_insert on public.tickets with check (
 nexus_private.has_role(tenant_id,array['admin','agent'])
 and created_by=(select auth.uid()) and status='open' and priority='normal'
);
alter policy doc_insert on public.knowledge_docs with check (
 nexus_private.has_role(tenant_id,array['admin']) and created_by=(select auth.uid())
);
