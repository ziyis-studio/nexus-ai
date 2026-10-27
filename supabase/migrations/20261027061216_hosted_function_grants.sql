-- Hosted projects can explicitly grant EXECUTE to API roles by default.
-- Revoking PUBLIC alone does not remove those role-specific grants.
revoke all on function public.create_analysis(uuid,uuid,text,text),
 public.review_analysis(uuid,uuid,text), public.session_active()
 from public,anon,service_role;
grant execute on function public.create_analysis(uuid,uuid,text,text),
 public.review_analysis(uuid,uuid,text), public.session_active()
 to authenticated;
