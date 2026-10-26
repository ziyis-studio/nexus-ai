# SQL performance report

Measured 2026-10-27 on Windows, Python 3.12.14, native PostgreSQL 18.4 over loopback. Full OS, CPU, PostgreSQL build, plans, buffers and samples are recorded in [`evidence/sql-benchmark.json`](evidence/sql-benchmark.json). The supported Supabase stack uses PostgreSQL 17; CI runs the same native security/performance scripts against 17.11.

The benchmark creates an isolated temporary database with two tenants, all three roles, 10,000 synthetic tickets, 200 representative runs and 30 knowledge documents. Both tenants contain each lifecycle/priority value. It then warms and samples each query 60 times. Ticket, membership and execution queries run as `authenticated` with membership RLS; knowledge retrieval runs as the restricted `nexus_worker` role. No external model calls or hosted Supabase network are included.

| Query                      |   Median |      p95 |
| -------------------------- | -------: | -------: |
| Tenant ticket page         | 0.375 ms | 0.486 ms |
| Tenant/status page         | 0.442 ms | 0.747 ms |
| Membership lookup          | 0.165 ms | 0.280 ms |
| Execution history          | 0.374 ms | 0.522 ms |
| Active knowledge retrieval | 0.108 ms | 0.262 ms |

Ten concurrent authenticated database clients each sampled 60 ticket-list queries. The slowest client's p95 was 1.487 ms. These are database-client round-trip measurements on a warm local cluster, not HTTP API or production SLAs.

The status-index experiment retains the general tenant pagination index and compares before/after creating the more specific status index. A single EXPLAIN ANALYZE sample measured 0.203 ms before and 0.367 ms after. At this small warm-data scale, this does **not** establish a speedup; noise and alternative index selection dominate. Both plans are retained. Indexes remain aligned with query ordering and tenant predicates, but further tuning needs larger/skewed datasets and representative deployment measurements.

The initial index set includes tenant/date/UUID ordering, tenant/status/date ordering, tenant/priority, membership user/tenant, run ticket/date, recovery status/lease, result tenant/run, knowledge tenant/active with GIN text search, and audit tenant/date/UUID. Avoid adding speculative indexes without evaluating write/storage overhead.

Reproduce with `BENCHMARK_DATABASE_URL=<disposable PostgreSQL URL> uv run python scripts/benchmark.py`. The script creates and drops its own `nexus_perf_*` database and leaves application records alone. CI uploads its environment-specific measurements separately. HTTP p95 below 500 ms and WebSocket propagation below two seconds should also be measured on the real staging topology before claiming the PRD's full deployed performance gate.
