# Entity relationships

```mermaid
erDiagram
  auth_users ||--o{ memberships : belongs
  tenants ||--o{ memberships : authorizes
  tenants ||--o{ tickets : owns
  tenants ||--o{ knowledge_docs : owns
  tickets ||--o{ analysis_runs : analyzes
  analysis_runs ||--o| ai_results : produces
  tenants ||--o{ audit_logs : records
  auth_users ||--o{ analysis_runs : initiates
  tenants { uuid id PK string name string slug UK }
  memberships { uuid tenant_id PK,FK uuid user_id PK,FK string role boolean is_active }
  tickets { uuid id PK uuid tenant_id FK string subject text description string status string priority uuid created_by FK timestamptz created_at timestamptz updated_at }
  knowledge_docs { uuid id PK uuid tenant_id FK string title text content string document_type boolean is_active tsvector search_vector }
  analysis_runs { uuid id PK uuid tenant_id FK uuid ticket_id FK uuid initiated_by FK string status string idempotency_key jsonb ticket_snapshot int attempt_count uuid lease_token timestamptz worker_lease_until }
  ai_results { uuid id PK uuid tenant_id FK uuid run_id FK,UK string category string suggested_priority string sentiment text suggested_reply jsonb source_document_ids string review_status uuid reviewed_by FK }
  audit_logs { uuid id PK uuid tenant_id FK uuid actor_id FK string action string resource_type uuid resource_id jsonb metadata }
```

Tenant-consistent composite foreign keys connect `(tenant_id, ticket_id)` and `(tenant_id, run_id)`. A unique `run_id` permits one result per execution. `(tenant_id, initiated_by, idempotency_key)` protects duplicate submissions. Source-document IDs are additionally checked by a tenant/active-document trigger and the worker's retrieved-document allowlist.

There are no business-data DELETE grants or API endpoints in P0. Archived knowledge remains readable for historical citations. Audit records contain identifiers and safe event metadata, never ticket text or credentials.
