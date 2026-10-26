# API contract

Base URL: `/api/v1`. Interactive Swagger: `/docs`. Reviewed machine contract: [`contracts/openapi.yaml`](../contracts/openapi.yaml). FastAPI also serves `/openapi.json`.

Every business request requires `Authorization: Bearer <Supabase access token>`. Tenant routes bind `tid` to a current membership. API error envelopes contain `error.code`, a safe `message`, and `request_id`; `X-Request-ID` carries the same identifier. Validation errors do not echo request bodies or token values.

| Area          | Operations                                                                                                       |
| ------------- | ---------------------------------------------------------------------------------------------------------------- |
| Identity      | `GET /me`, `GET /me/tenants`                                                                                     |
| Tickets       | `GET/POST /tenants/{tid}/tickets`, `GET/PATCH /tenants/{tid}/tickets/{ticket_id}`                                |
| Analysis      | `POST /tenants/{tid}/tickets/{ticket_id}/analyze`, `GET /tenants/{tid}/runs`, `GET /tenants/{tid}/runs/{run_id}` |
| Result/review | `GET /tenants/{tid}/runs/{run_id}/result`, `POST .../approve`, `POST .../reject`                                 |
| Knowledge     | `GET/POST /tenants/{tid}/knowledge`, `GET/PATCH /tenants/{tid}/knowledge/{document_id}`                          |
| Organization  | Admin-only `GET /tenants/{tid}/members`, `GET /tenants/{tid}/audit`                                              |
| Health        | Public `/health/live`, `/health/ready` (outside `/api/v1`)                                                       |

Lists return `{items, next_cursor}`. Default page size 20, maximum 100. The opaque cursor encodes tenant, UTC `created_at` and UUID; ordering is descending `(created_at,id)` and cursor reuse in a different tenant is invalid. Tickets accept `q` (subject), `status`, `priority`. Knowledge accepts title search `q`; runs accept `ticket_id`.

Ticket creation returns 201 and only accepts user fields. An analyze request returns 202 with `{run_id,status,created_at}` without waiting for an LLM. Supply `Idempotency-Key` to safely repeat submissions. Identical tenant/actor/key/payload returns the same run; a different payload returns 409. New keys create new runs within quota. Review returns the stored typed result. A missing/not-yet-produced result returns 404.

Use 400 for a disallowed business transition, 401 for missing/invalid/revoked identity, 403 for membership/role denial, 404 for inaccessible records in an authorized tenant, 409 for conflicting idempotency/review, 422 for request schema errors, 429 for workspace quota, and 503 for dependencies. Unexpected errors return a sanitized 500.

Run `PYTHONPATH=services/api:. uv run python scripts/contract.py` to check the contract. Updating it requires explicit `--write`, code review and tests; CI compares the entire generated schema.
