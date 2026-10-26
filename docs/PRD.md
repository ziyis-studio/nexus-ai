# NEXUS AI
## Product Requirements Document (PRD)

**Product:** NEXUS AI — Multi-Tenant AI Ticket Intelligence Engine  
**Version:** 1.0  
**Created:** 2026-10-27  
**Status:** Approved for MVP Development (Proposed Baseline)  
**Project Type:** Enterprise SaaS / AI Engine Service  
**Development Model:** Single Developer / Portfolio Project  
**Target Delivery:** 21-Day MVP Sprint (Estimated)  
**Primary Language:** English UI / English API / Chinese & English AI Input  
**Document Owner:** Project Developer

---

# 1. Executive Summary

## 1.1 Product Overview

NEXUS AI is a multi-tenant, AI-powered ticket intelligence engine designed to help organizations analyze, classify, prioritize, and respond to customer service requests.

The system will enable enterprise users to:

1. Create and manage customer support tickets.
2. Automatically analyze ticket content using Large Language Models.
3. Generate structured AI analysis results.
4. Retrieve tenant-specific knowledge to support suggested responses.
5. Receive real-time AI processing status.
6. Review and approve AI-generated responses.
7. Maintain strict data isolation across organizations.
8. Monitor AI execution history and operational performance.

NEXUS AI will be designed as an independent AI Engine Service that can eventually integrate with a larger Enterprise Operating System.

**Core principle: Build one production-oriented engine service, not an entire ERP or Enterprise OS platform.**

## 1.2 Problem Statement

Organizations handling high volumes of customer support tickets commonly face several problems:

- Manual ticket classification requires significant time.
- Ticket prioritization varies between employees.
- Support agents repeatedly search for company-specific information.
- AI-generated answers may be inconsistent or unsupported.
- Employees lack visibility into AI task progress.
- Multi-organization platforms require secure data segregation.
- Existing AI integrations may lack structured outputs, auditing, and error recovery.

NEXUS AI addresses these problems by combining AI analysis with structured workflow management, tenant-aware knowledge retrieval, and secure enterprise application architecture.

## 1.3 Product Goals

| ID | Goal |
|---|---|
| G-01 | Provide a complete ticket-to-AI-analysis workflow |
| G-02 | Support multiple independent organizations |
| G-03 | Ensure strict cross-tenant data isolation |
| G-04 | Deliver predictable, documented REST APIs |
| G-05 | Provide real-time AI processing updates |
| G-06 | Produce structured and validated AI outputs |
| G-07 | Support human approval of AI recommendations |
| G-08 | Provide reliable error handling and recovery |
| G-09 | Enable reproducible deployment and automated testing |
| G-10 | Demonstrate maintainable enterprise-grade engineering practices |

## 1.4 Success Criteria

The MVP is considered successful when:

- Two demo tenants can operate independently.
- A user can authenticate and select an authorized tenant.
- A ticket can be created, listed, updated, and viewed.
- An AI analysis request returns an asynchronous job identifier.
- The worker completes an AI analysis and stores a validated result.
- WebSocket clients receive authorized real-time status updates.
- An authorized agent can approve or reject an AI suggestion.
- Cross-tenant access attempts are rejected.
- OpenAPI documentation is complete and consistent with implementation.
- Automated tests, database migrations, and Docker setup can be reproduced.

---

# 2. Scope and Release Priorities

## 2.1 Priority Definitions

**P0 — MVP Required**

Must be completed before the project is considered a functional MVP.

**P1 — Enhanced Release**

Important improvements implemented after the P0 end-to-end workflow is stable.

**P2 — Future Expansion**

Optional features demonstrating further enterprise scalability.

## 2.2 In Scope

| Module | Priority | Description |
|---|---|---|
| Authentication | P0 | Supabase Auth, JWT verification |
| Tenant Management | P0 | Tenant switching and membership validation |
| Role-Based Access | P0 | Admin, Agent, Viewer |
| Ticket Management | P0 | Create, read, update, list, filter |
| AI Classification | P0 | Category, priority, sentiment, summary |
| AI Response Generation | P0 | Generate suggested replies |
| Knowledge Base | P0 | Basic document management and retrieval |
| Asynchronous AI Jobs | P0 | Redis queue and Python worker |
| Real-Time Updates | P0 | WebSocket job notifications |
| Human Review | P0 | Approve/reject AI recommendations |
| Execution History | P0 | Job status and error history |
| Audit Logging | P0 | Important business and security events |
| REST API | P0 | FastAPI and OpenAPI |
| Nuxt Dashboard | P0 | Enterprise management interface |
| Tenant-Level RLS | P0 | PostgreSQL row access policies |
| Docker Deployment | P0 | Reproducible development environment |
| Automated Testing | P0 | Unit, integration and security testing |
| SQL Performance | P0 | Indexing and query analysis |
| Semantic RAG | P1 | pgvector embeddings and similarity retrieval |
| Member Invitations | P1 | Invite and revoke enterprise members |
| AI Usage Analytics | P1 | Token usage, latency and estimated costs |
| Advanced Retry Dashboard | P1 | Manual job retries and diagnostics |
| Advanced Monitoring | P1 | Metrics dashboard and alerting |
| Multiple AI Providers | P2 | Configurable model providers |
| Enterprise Integrations | P2 | ERP, CRM and external webhooks |
| Billing | P2 | Subscription and usage-based charging |

## 2.3 Out of Scope for MVP

The following features will not be implemented in P0:

- Complete enterprise ERP platform.
- Automated sending of customer emails.
- Billing and subscription management.
- Complex AI agent orchestration.
- Multi-region deployment.
- Kubernetes orchestration.
- Real-time collaboration editing.
- Full CRM integration.
- Fine-tuned or locally trained LLMs.
- Advanced analytics or predictive reporting.

**Scope constraint:** P1/P2 functionality must not block completion of P0.

---

# 3. Target Users and Roles

## 3.1 Tenant

A Tenant represents an independent organization using NEXUS AI.

Examples:

- Acme Corporation
- Nova Technologies

Each tenant has its own tickets, knowledge documents, AI execution results, and audit history.

A single user may belong to multiple tenants.

## 3.2 User Roles

### Admin

Responsible for organization-level administration.

Capabilities:

- View and manage tickets.
- Run AI analysis.
- Review AI recommendations.
- Manage knowledge documents.
- View execution and audit history.
- View organization members.
- Manage members in P1.

### Agent

Responsible for ticket processing.

Capabilities:

- View and manage tickets.
- Run AI analysis.
- Review AI recommendations.
- Access tenant knowledge.
- View execution history.

### Viewer

Read-only access.

Capabilities:

- View tickets.
- View AI analysis results.
- View knowledge documents.
- View execution history.

Cannot modify tickets or initiate billable AI operations.

## 3.3 Permission Matrix

| Action | Admin | Agent | Viewer |
|---|---|---|---|
| View Tickets | Yes | Yes | Yes |
| Create Tickets | Yes | Yes | No |
| Edit Tickets | Yes | Yes | No |
| Change Ticket Status | Yes | Yes | No |
| Run AI Analysis | Yes | Yes | No |
| View AI Results | Yes | Yes | Yes |
| Approve AI Response | Yes | Yes | No |
| Reject AI Response | Yes | Yes | No |
| Read Knowledge Base | Yes | Yes | Yes |
| Manage Knowledge Documents | Yes | No | No |
| View Execution History | Yes | Yes | Yes |
| View Audit Logs | Yes | No | No |
| View Members | Yes | No | No |
| Manage Members | P1 | No | No |

Authorization will be enforced by the backend and database rather than relying on frontend UI visibility.

---

# 4. Core User Journeys

## 4.1 Journey A — Ticket Analysis

**Actor:** Agent

**Preconditions:**

- User is authenticated.
- User belongs to the selected tenant.
- User has permission to initiate AI analysis.
- Ticket exists within the selected tenant.

**Workflow:**

1. Agent signs into NEXUS AI.
2. Agent selects a tenant.
3. Agent opens the Ticket Dashboard.
4. Agent creates or selects a ticket.
5. Agent clicks "Analyze with AI".
6. Backend validates permissions and ticket ownership.
7. Backend creates an analysis job.
8. Backend returns a job identifier.
9. AI Worker processes the ticket asynchronously.
10. Frontend receives processing events through WebSocket.
11. AI produces structured analysis results.
12. Results are validated and persisted.
13. Agent reviews the suggested response.
14. Agent approves or rejects the result.
15. System records an audit event.

**Expected outcome:** The entire workflow is completed without blocking a long-running HTTP request.

## 4.2 Journey B — Tenant Isolation

**Actor:** User belonging to Tenant A

**Workflow:**

1. User logs into Tenant A.
2. User attempts to access a Ticket belonging to Tenant B.
3. Backend verifies the user's membership and ticket ownership.
4. Request is rejected.
5. Database access policies prevent unauthorized exposure.
6. Sensitive information is not returned.

**Expected outcome:** No unauthorized data disclosure occurs through REST, WebSocket, search, or AI responses.

## 4.3 Journey C — Knowledge-Based AI Response

**Actor:** Admin and Agent

**Workflow:**

1. Admin creates a tenant-specific knowledge document.
2. Document is stored with the correct tenant identifier.
3. Agent submits a support ticket for analysis.
4. AI Engine retrieves relevant knowledge where available.
5. Relevant context is included as reference material.
6. AI generates a response suggestion.
7. Result includes references to supporting documents.
8. Agent reviews and approves the suggestion.

**Expected outcome:** AI responses are traceable to tenant-specific information when policy or business claims are made.

For P0, retrieval can use PostgreSQL full-text search and a limited number of text documents. Vector-based semantic retrieval is a P1 enhancement.

---

# 5. Functional Requirements

## 5.1 Authentication Module

### FR-AUTH-001 — User Login [P0]

Users must authenticate using Supabase Auth.

Required:

- Email/password authentication.
- Login and logout.
- Session restoration.
- Expired session handling.
- Protected routes.

Optional P1:

- Google OAuth login.
- Password reset UI.
- Multi-factor authentication.

**Acceptance criteria:**

- Valid credentials allow access.
- Invalid credentials display a generic error.
- Protected resources require authenticated identity.
- Expired or invalid tokens are rejected.
- Logging out clears the active frontend session.

### FR-AUTH-002 — JWT Validation [P0]

All protected API endpoints must validate Supabase-issued access tokens.

Validation requirements:

- JWT signature.
- Approved signing algorithm.
- Issuer.
- Audience.
- Expiration.
- User identity.
- Relevant session validity checks where required.

The backend must not trust a user ID supplied through request body fields.

### FR-AUTH-003 — Tenant Authorization [P0]

Tenant authorization must use the authenticated user ID and the current database membership record.

Requirements:

- Tenant IDs provided by clients must be validated.
- Membership role must be loaded from trusted server data.
- Removed or deactivated members lose access.
- Roles must not be derived from user-editable JWT metadata.

**Acceptance criteria:**

User A cannot access Tenant B by changing request path parameters.

---

## 5.2 Tenant Module

### FR-TEN-001 — Tenant Selection [P0]

Authenticated users can view the tenants they belong to.

Displayed information:

- Tenant name.
- Tenant ID.
- User role.
- Active tenant indicator.

### FR-TEN-002 — Tenant Switching [P0]

Users belonging to multiple tenants can switch between organizations.

Requirements:

- All tenant-specific application queries must use the selected tenant context.
- Cached records from the previous tenant must be invalidated or isolated.
- Existing WebSocket subscriptions must be disconnected or reauthorized.
- Unauthorized tenant selections must be rejected.

### FR-TEN-003 — Membership Management [P1]

Tenant administrators can invite users and assign roles.

MVP approach:

Membership records and two demo tenants are provisioned through authorized setup or seed scripts rather than a public tenant-registration workflow.

---

## 5.3 Ticket Management Module

### FR-TKT-001 — Create Ticket [P0]

Users with Admin or Agent permission can create tickets.

Required fields:

- `subject`
- `description`

Optional fields:

- `customer_name`
- `customer_email`
- `external_reference`

Server-controlled fields:

- `id`
- `tenant_id`
- `created_by`
- `status`
- `created_at`
- `updated_at`

Business rules:

- Subject length: 3–200 characters.
- Description length: 10–10,000 characters.
- New ticket status defaults to `open`.
- Tenant ID is taken from validated route context.
- Created-by ID comes from the authenticated principal.
- Ticket creation does not automatically initiate AI analysis.

**Acceptance criteria:**

Valid requests return `201 Created`, and the ticket appears in the selected tenant's list.

### FR-TKT-002 — List Tickets [P0]

System must support:

- Cursor-based or stable pagination.
- Status filtering.
- Priority filtering.
- Search by subject.
- Sorting by creation date.
- Tenant-scoped results.

For MVP, choose stable cursor pagination with `created_at` and `id` as the ordering key, or document a consistent alternative in SDD.

Default page size: 20.

Maximum page size: 100.

### FR-TKT-003 — View Ticket Details [P0]

Ticket detail must display:

- Subject.
- Description.
- Status.
- Current priority.
- Created and updated timestamps.
- Related analysis runs.
- Latest AI result.
- Review status.

### FR-TKT-004 — Update Ticket [P0]

Admin and Agent can:

- Edit subject and description.
- Change ticket status.
- Adjust ticket priority manually.

The system must update `updated_at` and create relevant audit records.

### FR-TKT-005 — Ticket Lifecycle [P0]

Allowed ticket statuses:

- `open`
- `in_progress`
- `resolved`
- `closed`

Default allowed transitions:

- `open → in_progress`
- `open → resolved`
- `in_progress → resolved`
- `resolved → closed`
- `resolved → open` (reopened)

An Admin may reopen a closed ticket.

Invalid transitions must return a business validation error.

AI analysis must not automatically change the ticket lifecycle status.

### FR-TKT-006 — Delete Ticket [P1]

Ticket deletion will not be exposed in MVP.

This avoids accidental loss of AI and audit history before a retention and soft-deletion policy is designed.

---

## 5.4 AI Analysis Engine

### FR-AI-001 — Trigger AI Analysis [P0]

Admin and Agent users can trigger AI analysis for an existing ticket.

The API must:

1. Validate user authentication.
2. Verify tenant membership and role.
3. Verify the ticket belongs to the selected tenant.
4. Enforce configured usage/concurrency limits.
5. Create an analysis run.
6. Enqueue the job.
7. Return `202 Accepted`.

The HTTP request must not wait for LLM generation to complete.

### FR-AI-002 — Structured Classification [P0]

AI must analyze ticket content and return:

- `category`
- `suggested_priority`
- `sentiment`
- `summary`
- `suggested_reply`
- `needs_human_review`
- `reasoning_summary`
- `source_document_ids`

Supported categories for MVP:

- `billing`
- `delivery`
- `technical`
- `account`
- `general`
- `other`

Priority values:

- `low`
- `normal`
- `high`
- `urgent`

Sentiment values:

- `positive`
- `neutral`
- `negative`

The categorization vocabulary is controlled by the application, not dynamically invented by the model.

### FR-AI-003 — Output Validation [P0]

Every model response must be validated against a Pydantic schema before storage.

Requirements:

- Strict enum validation.
- Required field validation.
- Maximum text lengths.
- Safe handling of malformed JSON.
- Rejection or normalization of unsupported values.
- Error recording when validation fails.

The output must not be treated as trusted database instructions.

### FR-AI-004 — Response Generation [P0]

AI must generate a professional suggested customer response.

Constraints:

- Do not invent refund eligibility.
- Do not invent delivery guarantees.
- Do not invent organization policies.
- Do not expose internal system prompts.
- Do not fabricate knowledge document references.
- State when necessary information is unavailable.
- Treat customer messages and retrieved documents as untrusted content, not operational instructions.

AI suggestions are not sent automatically.

### FR-AI-005 — Knowledge Grounding [P0]

For tickets requiring business-policy facts, the system must retrieve relevant tenant-specific knowledge before generating an answer.

MVP retrieval method:

- Tenant-filtered keyword or PostgreSQL full-text search.
- Bounded document count.
- Bounded context length.

When no reliable knowledge is found, the AI should request clarification or advise human verification rather than fabricating a policy.

### FR-AI-006 — LLM Provider Integration [P0]

Use a configurable LLM provider adapter.

Required configuration:

- Provider identifier.
- Model identifier.
- API credential.
- Request timeout.
- Maximum output tokens.
- Retry parameters.
- Usage limits.

MVP requires only one working provider integration.

Provider credentials must be stored in server environment variables or an approved secret store.

### FR-AI-007 — AI Execution History [P0]

Every analysis run must preserve:

- Run ID.
- Tenant ID.
- Ticket ID.
- Initiating user.
- Model identifier.
- Start and completion timestamps.
- Execution status.
- Retry count.
- Sanitized error code and summary.
- Result ID when successful.

P1 enhancements:

- Token usage.
- Estimated inference cost.
- Prompt template version.
- Evaluation score.

### FR-AI-008 — Human Review [P0]

AI responses must support these review states:

- `pending`
- `approved`
- `rejected`

Rules:

- Newly generated responses start as `pending`.
- Only Admin and Agent can approve or reject.
- Review must record actor and timestamp.
- The first completed review is final in MVP.
- Repeat approval requests must not create duplicate audit events.
- A new AI analysis produces a separate result.

**Acceptance criteria:**

A Viewer cannot approve or reject results.

---

## 5.5 Knowledge Base Module

### FR-KB-001 — Create Knowledge Document [P0]

Tenant Admin can create documents with:

- Title.
- Content.
- Document type.
- Active status.

Supported document types:

- FAQ.
- Policy.
- Product Information.
- General Reference.

MVP supports text content through a form.

### FR-KB-002 — List and View Knowledge Documents [P0]

Users within a tenant can list and view documents belonging to that organization.

Documents from other tenants must never appear in search or retrieval results.

### FR-KB-003 — Update and Archive Documents [P0]

Tenant Admin can:

- Edit document content.
- Activate or archive documents.

Archived documents must not be used for new AI retrievals.

### FR-KB-004 — Semantic Retrieval [P1]

Use PostgreSQL with pgvector for knowledge retrieval.

Pipeline:

1. Document ingestion.
2. Text chunking.
3. Embedding generation.
4. Tenant-scoped vector storage.
5. Similarity search.
6. Context assembly.
7. LLM generation.
8. Source citation validation.

Vector search must filter by tenant identity before returning documents.

---

## 5.6 Asynchronous Job Processing

### FR-JOB-001 — Job Creation [P0]

Every AI analysis request generates an `analysis_run` record.

Job statuses:

- `queued`
- `processing`
- `succeeded`
- `failed`

Allowed transitions:

- `queued → processing`
- `queued → failed`
- `processing → succeeded`
- `processing → failed`

A completed or failed job is immutable for MVP.

To retry a completed or failed analysis manually, a new run must be created.

### FR-JOB-002 — Queue Processing [P0]

Redis Streams with a consumer group will be used as the initial reliable job queue.

Responsibilities:

- API submits jobs.
- Worker consumes jobs.
- Worker claims execution responsibility.
- Worker persists results.
- Worker acknowledges successfully handled messages.
- Unacknowledged jobs can be recovered.

The database remains the authoritative source for job state.

### FR-JOB-003 — Idempotency [P0]

The analysis creation API supports an `Idempotency-Key` header.

Requirements:

- Duplicate requests with the same tenant, actor and idempotency key return the same run.
- The same key with a different request payload returns `409 Conflict`.
- Database uniqueness constraints protect against race conditions.
- Worker redelivery must not create duplicate AI results.
- A processing lease or equivalent atomic claim prevents concurrent execution of the same run.

### FR-JOB-004 — Retry Policy [P0]

Retry transient errors such as:

- Provider rate limiting.
- Temporary network failure.
- Transient server errors.

Default configuration:

- Maximum attempts: 3, including the first attempt.
- Exponential backoff with jitter.
- Per-attempt timeout: 30 seconds.
- Configurable overall job deadline.

Validation errors, permission failures and malformed requests are not blindly retried.

When retry attempts are exhausted, mark the run as `failed`.

### FR-JOB-005 — Failure Recovery [P0]

A process crash must not permanently hide unfinished work.

Requirements:

- Recover expired worker claims.
- Reconcile stale queued jobs.
- Prevent multiple successful writes for the same run.
- Avoid acknowledging a job before durable completion.
- Persist failure information for diagnostics.

The exact lease and reconciliation mechanism must be specified in SDD.

---

## 5.7 WebSocket Real-Time Events

### FR-WS-001 — Real-Time Job Updates [P0]

Frontend clients can subscribe to an authorized job.

Endpoint:

`/ws/v1/tenants/{tenant_id}/runs/{run_id}`

Supported event types:

- `run.queued`
- `run.started`
- `run.progress`
- `run.completed`
- `run.failed`

Events must contain:

- Event ID.
- Tenant ID.
- Run ID.
- Event type.
- Job status.
- Timestamp.
- Safe event payload.

### FR-WS-002 — WebSocket Authentication [P0]

The connection must require authentication and authorization before any tenant data is delivered.

MVP approach:

- Establish WebSocket connection.
- Require the first client message to contain an authentication payload within a short deadline.
- Validate the JWT.
- Validate tenant membership.
- Validate run ownership.
- Begin the subscription only after successful authorization.
- Reject invalid clients using an appropriate WebSocket close code.

Authentication tokens must not appear in application logs.

Production deployments must use encrypted WebSocket connections (`wss`).

### FR-WS-003 — Reconnection [P0]

If the WebSocket connection is interrupted:

1. Frontend indicates temporary disconnection.
2. Client reconnects with bounded exponential backoff.
3. User identity is revalidated.
4. Client obtains current run state from REST API.
5. Real-time updates resume.

Redis Pub/Sub or equivalent ephemeral notifications must not be treated as the source of truth.

### FR-WS-004 — Event Delivery Semantics [P0]

WebSocket events are best-effort notifications.

Frontend must tolerate:

- Duplicate events.
- Delayed events.
- Missed events.
- Reconnection.
- Out-of-order progress updates.

Authoritative status must always come from persisted job state.

---

# 6. Frontend Requirements

## 6.1 Frontend Technology

Framework: Nuxt / Vue  
Language: TypeScript  
UI Approach: Responsive enterprise SaaS dashboard  
State Management: Vue composables; Pinia where shared state complexity justifies it  
API Communication: REST over HTTPS  
Real-Time Communication: WebSocket

## 6.2 Design Principles

- Clean, minimal interface.
- Neutral gray visual system.
- High readability.
- Consistent spacing and typography.
- Clear status indicators.
- Responsive layouts.
- Low visual clutter.
- Accessible form labels and keyboard interactions.

Visual style must support usability rather than overpower the application.

## 6.3 Required Pages

### UI-001 — Login

Route: `/login`

Features:

- Email/password authentication.
- Form validation.
- Loading indicator.
- Safe authentication error display.

### UI-002 — Tenant Selection

Route: `/workspaces`

Features:

- Available organizations.
- Current user role.
- Tenant selection.

### UI-003 — Ticket Dashboard

Route: `/t/{tenant_id}/tickets`

Features:

- Ticket table.
- Status and priority filters.
- Search.
- Pagination.
- Create ticket action.
- Ticket status labels.

### UI-004 — Ticket Detail and AI Workspace

Route: `/t/{tenant_id}/tickets/{ticket_id}`

Features:

- Ticket information.
- Editing and status controls.
- AI Analyze button.
- Job progress status.
- AI results.
- Supporting knowledge references.
- Approval/rejection controls.
- Analysis history.

### UI-005 — Knowledge Base

Route: `/t/{tenant_id}/knowledge`

Features:

- Document list.
- Document detail.
- Create/edit/archive controls for Admin.
- Search.

### UI-006 — Execution History

Route: `/t/{tenant_id}/runs`

Features:

- Job list.
- Execution status.
- Initiating user.
- Execution timestamps.
- Error summaries.
- Links to associated tickets.

### UI-007 — Organization Settings

Route: `/t/{tenant_id}/settings`

MVP requirements:

- Organization information.
- Read-only tenant membership summary for Admin.

Member invitations and role changes are P1.

## 6.4 Shared UI States

Every data-driven view must provide:

- Loading state.
- Empty state.
- Error state.
- Success feedback.
- Unauthorized state.
- Network unavailable state.

Actions that create or update data must prevent accidental duplicate submission.

---

# 7. System Architecture Requirements

## 7.1 Architecture Style

The MVP will use a **Modular Monolith with an Independent AI Worker**.

This architecture is selected to:

- Keep the application maintainable.
- Avoid unnecessary distributed-service complexity.
- Support asynchronous AI workloads.
- Provide a clean service boundary for future integration.
- Allow the backend and worker to scale separately.

## 7.2 Main Components

| Component | Technology | Responsibility |
|---|---|---|
| Web Application | Nuxt / Vue / TypeScript | UI, client interactions |
| Authentication | Supabase Auth | Identity and sessions |
| API Service | Python / FastAPI | Business logic and REST APIs |
| Database | Supabase PostgreSQL | Persistent relational storage |
| Security | PostgreSQL RLS | Database-level tenant policies |
| Job Queue | Redis Streams | Asynchronous message delivery |
| AI Worker | Python | AI processing and result persistence |
| AI Integration | LLM API | Text classification and generation |
| Real-Time Gateway | FastAPI WebSocket | Job event notifications |
| Containerization | Docker / Compose | Local environment and deployment |
| CI | GitHub Actions | Automated checks |

## 7.3 Communication Protocols

- Nuxt → FastAPI: HTTPS REST
- Nuxt → Supabase Auth: HTTPS
- Nuxt ↔ FastAPI: WebSocket / WSS
- FastAPI → Supabase Data API: Authenticated, user-scoped requests
- FastAPI → Redis: Redis protocol
- Redis → Worker: Consumer group processing
- Worker → PostgreSQL: Server-side database access
- Worker → LLM: HTTPS
- Worker → Redis: Progress event publication

## 7.4 Database Access Boundary

The frontend will not directly write business tables through Supabase Data API.

FastAPI is the authoritative application API.

For user-initiated business operations:

- Verify JWT.
- Verify tenant membership and role.
- Forward requests through a properly user-scoped Supabase data-access client so PostgreSQL RLS is evaluated.
- Use a separate client context per request to prevent token leakage between users.

For background Worker operations:

- Use a dedicated server-side database connection or other approved privileged service access.
- Do not expose server credentials to the browser.
- Apply explicit tenant and resource checks.
- Use database constraints and transactional safety.
- Enforce least privilege wherever possible.

The implementation must never assume that a server-side privileged connection automatically receives end-user RLS protections.

Detailed connection pooling, transaction boundaries and client lifecycle must be documented in SDD.

---

# 8. Database Requirements

## 8.1 Database Technology

Primary Database: PostgreSQL managed by Supabase.

Requirements:

- UUID primary keys.
- UTC timestamps.
- Foreign key relationships.
- Unique constraints.
- Transaction integrity.
- Database migrations.
- Row-level security.
- Proper indexing.
- Query performance analysis.

## 8.2 Logical Data Model

### DB-001 — tenants

Purpose: Store organizations.

Fields:

| Field | Type | Constraint |
|---|---|---|
| id | UUID | Primary Key |
| name | VARCHAR(150) | Not Null |
| slug | VARCHAR(100) | Unique |
| created_at | TIMESTAMPTZ | Not Null |

### DB-002 — memberships

Purpose: Store tenant-user relationships.

Fields:

| Field | Type | Constraint |
|---|---|---|
| tenant_id | UUID | Tenant FK |
| user_id | UUID | Auth User FK |
| role | VARCHAR(20) | Role Enum/Check |
| created_at | TIMESTAMPTZ | Not Null |

Primary Key: `(tenant_id, user_id)`

Index requirement: Add an index beginning with `user_id` for user-to-tenant lookups.

### DB-003 — tickets

Purpose: Store customer tickets.

Fields:

| Field | Type | Constraint |
|---|---|---|
| id | UUID | Primary Key |
| tenant_id | UUID | Tenant FK |
| subject | VARCHAR(200) | Not Null |
| description | TEXT | Not Null |
| status | VARCHAR(30) | Not Null |
| priority | VARCHAR(20) | Not Null |
| customer_name | VARCHAR(150) | Nullable |
| customer_email | VARCHAR(254) | Nullable |
| created_by | UUID | User ID |
| created_at | TIMESTAMPTZ | Not Null |
| updated_at | TIMESTAMPTZ | Not Null |

Additional requirement:

Unique `(tenant_id, id)` to support tenant-consistent composite foreign keys.

### DB-004 — analysis_runs

Purpose: Track asynchronous AI executions.

Fields:

| Field | Type |
|---|---|
| id | UUID PK |
| tenant_id | UUID |
| ticket_id | UUID |
| initiated_by | UUID |
| status | VARCHAR(30) |
| model_id | VARCHAR(150) |
| idempotency_key | VARCHAR(150), nullable |
| request_hash | VARCHAR(128), nullable |
| attempt_count | INTEGER |
| worker_lease_until | TIMESTAMPTZ, nullable |
| error_code | VARCHAR(100), nullable |
| error_message | TEXT, nullable |
| created_at | TIMESTAMPTZ |
| started_at | TIMESTAMPTZ, nullable |
| completed_at | TIMESTAMPTZ, nullable |

Constraints:

- Foreign key `(tenant_id, ticket_id)` references `tickets(tenant_id, id)`.
- Unique `(tenant_id, id)`.
- Unique `(tenant_id, initiated_by, idempotency_key)` when the key is present.
- Attempt count must not be negative.

### DB-005 — ai_results

Purpose: Store AI output and review status.

Fields:

| Field | Type |
|---|---|
| id | UUID PK |
| tenant_id | UUID |
| run_id | UUID |
| category | VARCHAR(30) |
| suggested_priority | VARCHAR(20) |
| sentiment | VARCHAR(20) |
| summary | TEXT |
| suggested_reply | TEXT |
| reasoning_summary | TEXT |
| source_document_ids | JSONB |
| needs_human_review | BOOLEAN |
| review_status | VARCHAR(20) |
| reviewed_by | UUID, nullable |
| reviewed_at | TIMESTAMPTZ, nullable |
| created_at | TIMESTAMPTZ |

Constraints:

- Unique `run_id` for one result per execution.
- Composite foreign key `(tenant_id, run_id)` to `analysis_runs`.
- Review status must use an approved value.

### DB-006 — knowledge_docs

Purpose: Store organization knowledge documents.

Fields:

| Field | Type |
|---|---|
| id | UUID PK |
| tenant_id | UUID |
| title | VARCHAR(200) |
| content | TEXT |
| document_type | VARCHAR(30) |
| is_active | BOOLEAN |
| created_by | UUID |
| created_at | TIMESTAMPTZ |
| updated_at | TIMESTAMPTZ |

Constraint: Unique `(tenant_id, id)`.

### DB-007 — knowledge_chunks [P1]

Purpose: Store document chunks for vector search.

Fields:

| Field | Type |
|---|---|
| id | UUID PK |
| tenant_id | UUID |
| document_id | UUID |
| chunk_index | INTEGER |
| content | TEXT |
| embedding | VECTOR(N) |
| created_at | TIMESTAMPTZ |

`N` must match the selected embedding model dimension.

Constraint:

`(tenant_id, document_id)` references `knowledge_docs(tenant_id, id)`.

### DB-008 — audit_logs

Purpose: Store important security and business activities.

Fields:

| Field | Type |
|---|---|
| id | UUID PK |
| tenant_id | UUID |
| actor_id | UUID, nullable |
| action | VARCHAR(100) |
| resource_type | VARCHAR(100) |
| resource_id | UUID, nullable |
| metadata | JSONB |
| created_at | TIMESTAMPTZ |

Audit log data must never contain plaintext passwords, access tokens or LLM provider keys.

## 8.3 Required Indexes

Initial indexes:

- `tickets(tenant_id, status, created_at DESC, id DESC)`
- `tickets(tenant_id, priority)`
- `analysis_runs(tenant_id, ticket_id, created_at DESC)`
- `analysis_runs(status, worker_lease_until)` for recovery
- `ai_results(tenant_id, run_id)`
- `knowledge_docs(tenant_id, is_active)`
- `memberships(user_id, tenant_id)`
- `audit_logs(tenant_id, created_at DESC)`

Additional indexes may be created after measuring real query plans.

## 8.4 Performance Validation

Use PostgreSQL:

- `EXPLAIN`
- `EXPLAIN ANALYZE`
- `BUFFERS`
- Query execution statistics where available.

Generate representative synthetic data to benchmark:

- Tenant-specific pagination.
- Ticket status filtering.
- Latest analysis lookup.
- Tenant membership checks.
- Knowledge retrieval.

Performance evidence must include actual measurements rather than assumed speed improvements.

---

# 9. Multi-Tenant Security Requirements

## 9.1 Isolation Strategy

Use a shared database with tenant-specific rows.

Every tenant-owned business record must include `tenant_id`.

Tenant ownership must be enforced through:

1. Backend authorization.
2. PostgreSQL RLS where user-scoped access is used.
3. Foreign key constraints.
4. Restricted background-service permissions.
5. Automated cross-tenant security testing.

## 9.2 Row Level Security

RLS must be enabled on all exposed business tables.

Policies must distinguish:

- SELECT.
- INSERT.
- UPDATE.
- DELETE.

For writes, policies must prevent changing tenant ownership.

RLS must use trustworthy membership relationships and authenticated identity.

Particular care must be taken to avoid recursive policies involving the membership table.

If a privileged database helper function is necessary, its privileges, exposed schema and execution rights require explicit security review.

## 9.3 Supabase API Security

Requirements:

- Browser may use publishable project keys.
- Secret/service credentials remain server-side.
- Explicit table grants are required only for the operations exposed.
- RLS policies and grants must both be verified.
- User-editable metadata must not determine authorization.
- Service-role access must not be mistaken for end-user RLS enforcement.

## 9.4 Data Protection

Requirements:

- HTTPS/WSS in deployed environments.
- No plaintext secrets in repositories.
- Environment-specific configuration.
- Sanitized logging.
- Input validation.
- Protection against injection.
- Restricted CORS and WebSocket origins.
- Rate limiting on AI operations.
- No raw sensitive customer content in application logs by default.

Use synthetic customer data for public portfolio demonstrations.

## 9.5 Security Acceptance Tests

Mandatory tests:

- Unauthenticated API access.
- Expired JWT.
- Invalid JWT signature.
- Unauthorized tenant selection.
- Cross-tenant ticket read.
- Cross-tenant ticket update.
- Cross-tenant analysis trigger.
- Cross-tenant result retrieval.
- Cross-tenant knowledge retrieval.
- Cross-tenant WebSocket subscription.
- Viewer attempts privileged action.
- Tenant ID mutation during update.
- Injection attempts in user-supplied text.
- Duplicate job submission.
- Worker replay and unauthorized resource association.

All critical tenant-isolation tests must pass before release.

---

# 10. REST API Requirements

## 10.1 API Standards

Framework: FastAPI.

API Style: RESTful JSON API.

Base Path:

`/api/v1`

Required standards:

- OpenAPI contract.
- Swagger UI.
- Pydantic request/response models.
- Consistent validation errors.
- Bearer authentication.
- Pagination.
- API versioning.
- Idempotency where necessary.
- Documented status codes.

## 10.2 Required Endpoints

### Authentication / Tenant Context

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/me` | Current user summary |
| GET | `/me/tenants` | Authorized tenants |

Authentication itself is handled by Supabase Auth.

### Tickets

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/tenants/{tid}/tickets` | List tickets |
| POST | `/tenants/{tid}/tickets` | Create ticket |
| GET | `/tenants/{tid}/tickets/{id}` | Ticket detail |
| PATCH | `/tenants/{tid}/tickets/{id}` | Update ticket |

### AI Analysis

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/tenants/{tid}/tickets/{id}/analyze` | Start analysis |
| GET | `/tenants/{tid}/runs` | Execution history |
| GET | `/tenants/{tid}/runs/{id}` | Run detail/status |
| GET | `/tenants/{tid}/runs/{id}/result` | Result detail |
| POST | `/tenants/{tid}/runs/{id}/approve` | Approve result |
| POST | `/tenants/{tid}/runs/{id}/reject` | Reject result |

### Knowledge Base

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/tenants/{tid}/knowledge` | List documents |
| POST | `/tenants/{tid}/knowledge` | Create document |
| GET | `/tenants/{tid}/knowledge/{id}` | Document detail |
| PATCH | `/tenants/{tid}/knowledge/{id}` | Update/archive |

### Members

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/tenants/{tid}/members` | Admin membership list |

### Operations

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health/live` | Process liveness |
| GET | `/health/ready` | Dependency readiness |

## 10.3 Request Example

`POST /api/v1/tenants/{tid}/tickets`

Request body:

```json
{
  "subject": "Delayed delivery",
  "description": "My order has been delayed for five days.",
  "customer_name": "Demo Customer"
}
```

Success response: `201 Created`

```json
{
  "id": "ticket-uuid",
  "tenant_id": "tenant-uuid",
  "subject": "Delayed delivery",
  "status": "open",
  "priority": "normal",
  "created_at": "2026-10-27T08:00:00Z"
}
```

Illustrative UUID placeholders must be replaced by actual UUID values in running examples and automated tests.

## 10.4 AI Analysis API Example

`POST /api/v1/tenants/{tid}/tickets/{id}/analyze`

Headers:

- `Authorization: Bearer <access_token>`
- `Idempotency-Key: <unique_request_key>`

Success response: `202 Accepted`

```json
{
  "run_id": "run-uuid",
  "status": "queued",
  "created_at": "2026-10-27T08:01:00Z"
}
```

## 10.5 AI Result Example

```json
{
  "run_id": "run-uuid",
  "status": "succeeded",
  "result": {
    "category": "delivery",
    "suggested_priority": "high",
    "sentiment": "negative",
    "summary": "Customer reports delayed delivery.",
    "suggested_reply": "We apologize for the delay...",
    "reasoning_summary": "Delivery delay and refund concern.",
    "needs_human_review": true,
    "source_document_ids": [],
    "review_status": "pending"
  }
}
```

## 10.6 Standard Error Format

Example:

```json
{
  "error": {
    "code": "TENANT_ACCESS_DENIED",
    "message": "You do not have permission to access this resource.",
    "request_id": "request-uuid"
  }
}
```

Required response codes:

- `400` Invalid business request.
- `401` Unauthenticated.
- `403` Forbidden.
- `404` Resource not found.
- `409` Conflict.
- `422` Schema validation failed.
- `429` Rate limit exceeded.
- `500` Internal error.
- `503` Dependency unavailable.

The system may use `404` rather than `403` for foreign-tenant resources to avoid revealing resource existence. This must be consistently documented and tested.

## 10.7 Doc-First Development

`contracts/openapi.yaml` is the proposed API contract source.

Workflow:

1. Define endpoint contract.
2. Review request/response schemas.
3. Implement FastAPI routes.
4. Generate implementation OpenAPI schema.
5. Compare the implementation against the contract.
6. Run contract tests.
7. Reject incompatible changes in CI.

WebSocket message definitions must be documented separately in `docs/websocket-protocol.md`.

---

# 11. Non-Functional Requirements

## 11.1 Performance

Initial performance targets for the demo environment:

| Metric | Target |
|---|---|
| CRUD API p95 | Under 500 ms |
| Ticket list p95 | Under 500 ms |
| WebSocket update propagation | Under 2 seconds in normal local conditions |
| Supported active test users | 10 concurrent users |
| Concurrent AI workers | Configurable; initially 2 |
| AI analysis processing | Asynchronous with bounded timeout |

API latency tests should use seeded data and exclude external LLM execution time.

AI processing time depends on the selected provider, token count and rate limits. Record actual latency distributions rather than promising a fixed production response time.

## 11.2 Reliability

Requirements:

- Persistent job state.
- Recoverable queue processing.
- Bounded retries.
- Idempotent requests.
- Graceful handling of LLM provider failure.
- Safe startup/shutdown.
- Health and readiness checks.
- No silent data loss after worker failures.

## 11.3 Maintainability

Requirements:

- Modular backend architecture.
- Separated routing, service and repository layers.
- Type annotations.
- Consistent code formatting.
- Explicit configuration models.
- Database migrations.
- Unit and integration tests.
- Architecture documentation.

Avoid placing complete business logic inside FastAPI route functions.

## 11.4 Observability

Structured logs must include:

- Timestamp.
- Severity.
- Service name.
- Request ID.
- Run ID where relevant.
- Tenant ID where relevant.
- Event name.
- Safe error code.

Sensitive content and credentials must be redacted.

Required operational metrics:

- API request count.
- API error count.
- API latency.
- Queue depth.
- Job completion count.
- Job failure count.
- Job duration.
- Retry count.

MVP can expose metrics through structured logs or a lightweight endpoint. A full metrics stack is P1.

## 11.5 Data Consistency

Requirements:

- Foreign key enforcement.
- Transactional updates.
- Consistent job status and result storage.
- Unique analysis result per run.
- No invalid review transitions.
- No cross-tenant references.
- Audit records for critical actions.

## 11.6 Time and Localization

- Store timestamps in UTC.
- Return ISO 8601 timestamps.
- Convert to user-local time in frontend.
- Display dates consistently.
- Accept Chinese and English support ticket content.
- English UI in MVP.

---

# 12. Technology Stack

## 12.1 Frontend

- Nuxt
- Vue
- TypeScript
- Tailwind CSS
- Pinia (when needed)
- Native WebSocket API
- Supabase Auth client

## 12.2 Backend

- Python 3.12+ (select and pin an actively supported runtime)
- FastAPI
- Pydantic v2
- HTTPX
- Supabase Python client
- SQLAlchemy / asyncpg for approved direct database operations
- Redis Python client
- Pytest

## 12.3 Database

- PostgreSQL (Supabase)
- PostgreSQL RLS
- Supabase Auth
- SQL migrations
- pgTAP database tests
- pgvector (P1)

## 12.4 Infrastructure

- Docker
- Docker Compose
- Linux CLI
- Git
- GitHub
- GitHub Actions
- Environment variable configuration

## 12.5 AI Integration

- Configurable LLM API
- Structured model output
- Pydantic validation
- Prompt versioning
- Retrieval pipeline
- Embeddings (P1)

Dependency versions must be pinned in lockfiles during development. Do not rely on unbounded latest-version dependencies.

---

# 13. Testing and Quality Assurance

## 13.1 Backend Unit Tests

Must test:

- Ticket validation.
- Role permissions.
- Tenant context.
- Ticket status transitions.
- AI result schema validation.
- Review status transitions.
- Error mapping.
- Retry decision logic.

## 13.2 Integration Tests

Must test:

- Creating tickets.
- Ticket pagination.
- Tenant-scoped queries.
- Analysis job submission.
- Worker job consumption.
- Database result persistence.
- AI review workflow.
- WebSocket authorization.
- Worker recovery.

External LLM calls should be mocked in CI to avoid nondeterministic tests and API charges.

## 13.3 Database Tests

Must test:

- RLS SELECT policies.
- RLS INSERT policies.
- RLS UPDATE policies.
- RLS DELETE policies.
- Foreign key constraints.
- Composite tenant relationships.
- Unique constraints.
- Membership authorization behavior.

## 13.4 End-to-End Tests

Minimum user journeys:

1. Login.
2. Select Tenant A.
3. Create ticket.
4. Start AI analysis.
5. Observe processing status.
6. Review AI result.
7. Approve response.
8. Switch to Tenant B.
9. Verify Tenant A information is unavailable.

## 13.5 Performance Tests

Seed at least:

- 2 tenants.
- 3 roles.
- 10,000 synthetic tickets across tenants.
- Representative analysis runs.
- Multiple knowledge documents.

Measure:

- Ticket list latency.
- Pagination queries.
- Membership checks.
- Execution history queries.
- Index usage.

Document test environment specifications alongside performance results.

## 13.6 Quality Gates

Release conditions:

- All critical security tests pass.
- All P0 acceptance tests pass.
- No known critical or high-severity security defects.
- No unresolved data isolation defects.
- No failing database migrations.
- CI passes.
- API contract checks pass.
- Backend automated test coverage target: at least 80% for business logic modules.
- Deployment and recovery procedures are documented.

Coverage is supporting evidence, not a replacement for meaningful tests.

---

# 14. DevOps and Deployment

## 14.1 Required Environments

### Local Development

- Nuxt frontend.
- FastAPI API.
- Python AI Worker.
- Redis.
- Supabase local stack or configured development project.

### Demo / Staging

- Deployed frontend.
- Deployed backend.
- Worker service.
- Managed or deployed Redis.
- Supabase development database.
- Test-only credentials and synthetic records.

## 14.2 Docker Requirements

Required services:

- `web`
- `api`
- `worker`
- `redis`

Supabase services may run via the Supabase CLI's supported local setup.

The Docker environment must support:

- Repeatable startup.
- Environment configuration.
- Health checks.
- Persistent local database setup.
- Log inspection.
- Clear shutdown procedures.

## 14.3 CI/CD Pipeline

Required stages:

1. Dependency installation.
2. Formatting verification.
3. Linting.
4. Type checking.
5. Backend unit tests.
6. Database integration/RLS tests.
7. OpenAPI contract verification.
8. Frontend build.
9. Docker build verification.

Deployment automation can be added after CI is stable.

## 14.4 Git Workflow

Recommended branches:

- `main`
- `develop`
- `feature/*`
- `fix/*`
- `release/*` (optional)

Requirements:

- Meaningful commit messages.
- Small, reviewable changes.
- Pull requests or equivalent documented merge process.
- No secrets committed.
- Protected main branch where supported.

For a solo developer, release branches are optional; the workflow should not create unnecessary administrative overhead.

---

# 15. Development Milestones

## Milestone 1 — Foundation

**Target: Day 1–5**

Deliverables:

- PRD v1.0.
- SDD draft.
- Architecture diagram.
- ERD.
- Supabase schema.
- Database migrations.
- Supabase Auth integration.
- Tenant membership and RLS.

Acceptance:

- Two demo tenants exist.
- Authorized users can authenticate.
- Basic tenant isolation tests pass.

## Milestone 2 — Backend Engine

**Target: Day 6–11**

Deliverables:

- FastAPI ticket endpoints.
- Pydantic schemas.
- OpenAPI contract.
- LLM integration.
- Redis Streams integration.
- AI Worker.
- Analysis result persistence.

Acceptance:

- Ticket can be created through REST API.
- AI analysis can run asynchronously.
- Result is persisted and retrievable.
- Worker failures produce controlled error states.

## Milestone 3 — Frontend and Real-Time Integration

**Target: Day 12–16**

Deliverables:

- Nuxt dashboard.
- Ticket management UI.
- AI Workspace.
- WebSocket events.
- Knowledge Base UI.
- Approval/rejection workflow.
- Execution history UI.

Acceptance:

- Complete end-to-end user journey succeeds.
- WebSocket reconnect logic works.
- Tenant switching does not expose cached data.

## Milestone 4 — Quality and Deployment

**Target: Day 17–21**

Deliverables:

- Security tests.
- Integration tests.
- Performance tests.
- SQL optimization report.
- Docker environment.
- GitHub Actions CI.
- Updated SDD.
- README.
- Demo recording.

Acceptance:

- All P0 release gates pass.
- A reviewer can reproduce the local deployment from repository instructions.

---

# 16. Repository Structure

```text
nexus-ai/
├── apps/
│   └── web/
│       ├── pages/
│       ├── components/
│       ├── composables/
│       ├── middleware/
│       ├── stores/
│       └── types/
├── services/
│   ├── api/
│   │   ├── app/
│   │   │   ├── routers/
│   │   │   ├── schemas/
│   │   │   ├── services/
│   │   │   ├── repositories/
│   │   │   ├── auth/
│   │   │   ├── core/
│   │   │   └── main.py
│   │   └── tests/
│   └── worker/
│       ├── handlers/
│       ├── ai/
│       ├── queue/
│       └── tests/
├── supabase/
│   ├── migrations/
│   ├── tests/
│   └── seed.sql
├── contracts/
│   └── openapi.yaml
├── docs/
│   ├── PRD.md
│   ├── SDD.md
│   ├── ERD.md
│   ├── ARCHITECTURE.md
│   ├── SECURITY.md
│   ├── API.md
│   ├── websocket-protocol.md
│   ├── TEST_PLAN.md
│   └── PERFORMANCE.md
├── scripts/
├── .github/
│   └── workflows/
├── docker-compose.yml
├── .env.example
└── README.md
```

---

# 17. MVP Demo Scenarios

## DEMO-001 — Complete AI Workflow

Steps:

1. Login as Agent.
2. Select Tenant A.
3. Create ticket.
4. Open ticket details.
5. Start AI analysis.
6. Receive async job ID.
7. Observe WebSocket progress.
8. Open structured AI result.
9. Approve suggestion.
10. Verify audit event.

**Expected result:** Successful end-to-end operation.

## DEMO-002 — Tenant Isolation

Steps:

1. Authenticate as Tenant A user.
2. Attempt to fetch Tenant B ticket through API.
3. Attempt to retrieve Tenant B AI result.
4. Attempt to subscribe to Tenant B WebSocket run.
5. Attempt to access Tenant B knowledge document.

**Expected result:** All unauthorized operations are rejected without disclosing business data.

## DEMO-003 — SQL Optimization

Steps:

1. Seed representative database.
2. Run target query.
3. Capture execution plan.
4. Add or adjust index.
5. Rerun query.
6. Compare execution statistics.

**Expected result:** Documented, reproducible performance evaluation and explanation.

## DEMO-004 — Failure Recovery

Steps:

1. Submit an AI job.
2. Simulate temporary provider failure or worker termination.
3. Observe retry/recovery.
4. Verify final persistent job state.
5. Refresh the frontend.
6. Confirm state reconstruction from the REST API.

**Expected result:** No duplicated results and no indefinitely lost job.

---

# 18. Risks and Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| LLM API instability | Analysis failure | Timeout, retries, failure states |
| LLM output inconsistency | Invalid results | Schema validation |
| Hallucinated answers | Incorrect advice | Grounding, cautious fallback, review |
| Cross-tenant access | Serious security issue | Authorization, RLS, composite FKs, tests |
| Worker crashes | Lost or stalled jobs | Recovery, lease, acknowledgement |
| Redis unavailable | Queue interruption | Controlled failure and reconciliation |
| Excessive API cost | Budget overruns | Usage/concurrency limits |
| Scope creep | Delayed MVP | P0/P1/P2 separation |
| Database performance | Slow APIs | Indexes and query benchmarking |
| WebSocket disconnection | Stale frontend state | Reconnection and REST reconciliation |
| Secret exposure | Security incident | Environment variables and redaction |

---

# 19. Definition of Done

A feature is considered complete only when:

- Implementation matches the approved requirement.
- Request and response schemas are documented.
- Input validation exists.
- Authentication and permissions are enforced.
- Tenant isolation is verified where relevant.
- Error scenarios are handled.
- Automated tests are added.
- Relevant UI states are implemented.
- Logs provide useful diagnostic information.
- No new critical security issues are introduced.
- Documentation is updated.

A successful manual demonstration alone is not sufficient for completion.

---

# 20. Required Project Deliverables

## Documentation

- PRD v1.0
- Software Design Document (SDD)
- ERD
- Architecture Diagram
- API Contract
- Security Design
- Testing Plan
- Performance Report
- Deployment Guide

## Source Code

- Nuxt Application
- FastAPI Service
- Python AI Worker
- Database Migrations
- RLS Policies
- Redis Queue Integration
- Docker Configuration
- Automated Tests
- CI Workflow

## Portfolio

- Public GitHub Repository
- High-Quality README
- Architecture Overview
- Screenshots
- Live Demo (where feasible)
- Technical Walkthrough Video
- Documented Engineering Tradeoffs

---

# 21. Implementation Decisions and Assumptions

The following decisions are adopted to prevent ambiguity during MVP development:

| Decision | MVP Choice |
|---|---|
| Database topology | Shared PostgreSQL database, tenant_id isolation |
| Backend architecture | Modular monolith plus separate Worker |
| Primary API | FastAPI |
| Authentication provider | Supabase Auth |
| User permission source | Database membership records |
| Frontend data operations | Through FastAPI |
| Async job transport | Redis Streams |
| Authoritative job state | PostgreSQL |
| Real-time transport | Authenticated WebSocket |
| AI provider | One configurable provider |
| Knowledge retrieval | Tenant-scoped PostgreSQL text search |
| Semantic search | P1 |
| AI response delivery | Human review only, no automatic outbound message |
| Tenant provisioning | Seeded/admin setup for MVP |
| Database schema changes | Versioned migrations |
| Time storage | UTC |
| Development approach | Doc-First and Test-Driven where practical |

**Architecture tradeoff:** The application will not introduce extra microservices solely for architectural appearance. Components are separated where their responsibilities and operational behavior justify it.

---

# 22. Development Kickoff Checklist

Before building the first feature:

- [ ] Initialize GitHub repository.
- [ ] Create Nuxt project.
- [ ] Create Python/FastAPI project.
- [ ] Initialize Supabase project and local environment.
- [ ] Configure environment variables.
- [ ] Create the first ERD.
- [ ] Define SQL migrations.
- [ ] Set up test tenants and accounts.
- [ ] Define RBAC rules.
- [ ] Define the OpenAPI v1 contract.
- [ ] Create SDD architecture and security sections.
- [ ] Configure Docker Compose.
- [ ] Configure initial CI pipeline.

**First implementation target:**

An authenticated Agent from Tenant A can create and read a ticket through FastAPI while all unauthorized cross-tenant operations are rejected.

Only after this vertical slice works should the AI processing pipeline be added.

---

# 23. Reference Documentation

Technical references should be checked against the installed dependency versions during implementation.

- Supabase RLS: https://supabase.com/docs/guides/database/postgres/row-level-security
- Supabase Auth JWT: https://supabase.com/docs/guides/auth/jwts
- Supabase Vector Columns: https://supabase.com/docs/guides/ai/vector-columns
- FastAPI Documentation: https://fastapi.tiangolo.com/
- FastAPI OpenAPI: https://fastapi.tiangolo.com/reference/openapi/docs/
- Nuxt Documentation: https://nuxt.com/docs
- Redis Streams: https://redis.io/docs/latest/develop/data-types/streams/
- PostgreSQL Documentation: https://www.postgresql.org/docs/
- Docker Documentation: https://docs.docker.com/

---

# 24. Final Product Acceptance

NEXUS AI v1.0 will be accepted as a completed MVP when an authorized enterprise user can securely manage tickets, launch asynchronous AI analyses, receive real-time execution updates, review validated AI results and operate entirely within their permitted tenant, with documented APIs, reproducible deployment and passing automated tests.

**End of PRD v1.0**
