---
title: "11. Observability"
updated_time: 2026-11-06
git_commit: 5f85578
updated_by: ai
source:
  - "nginx 1.31.1 / ngx_lua 0.10.31rc5 verified in this tree (DNS signals below)"
  - "doc/10-runbook.md, doc/07-conventions.md (this PKB)"
owners:
  created_by: [Walter Fan]
  updated_by: [Walter Fan]
  responsible: [Walter Fan]
ttl: 6 months
review_status: pending
review_score: 0
reviewed_by: null
confidentiality: L1
summary: Observing OpenResty - error-log signals and levels, request correlation, metrics choices, and alerts, with the DNS-failure signals as a worked example.
tags:
  domain:
  - openresty
  technology:
  - nginx
  - ngx_lua
  concepts:
  - observability
  - logging
  - metrics
  - tracing
  audience: ops
  status: active
---

# 11. Observability

<!-- maintained-by: human+ai -->

The primary signal for OpenResty is the Nginx error log plus `ngx.log` lines
from Lua; the runtime ships no per-request metrics by default. This page
documents what to log, how to correlate, and which counters to build - with the
DNS-failure signals as the worked example (verified against nginx 1.31.1 /
ngx_lua 0.10.31rc5 in this tree).

## Logging

| Aspect | Approach |
|--------|----------|
| Library or framework | Nginx error log, plus `ngx.log` in Lua |
| Levels | `ngx.ERR` for the final failure, `ngx.WARN` for a retry, `ngx.INFO`/`DEBUG` for detail |
| Format | Text lines, not JSON. Use `log_format` for access log with `$request_id`, timing, and status |
| Output location | The `error_log` path. Lua lines go to the same log. |
| Request correlation | Add `$request_id` (and upstream `X-Request-ID`) to the `log_format`; echo it in errors |

Log the hostname or resource involved, not credentials or query payloads.

### DNS lines to alert on

| Pattern | Meaning |
|---------|---------|
| `no resolver defined to resolve` | Configuration bug. Page immediately. |
| `could not be resolved (3: Host not found)` | NXDOMAIN |
| `could not be resolved (2: Server failure)` | SERVFAIL |
| `could not be resolved (5: Operation refused)` | REFUSED |
| `could not be resolved (` and `Operation timed out` | `resolver_timeout` elapsed |
| `wrong ident` in a debug or the resolver log level | Spoofed or late response, ignored |
| `compression pointers loop in DNS response` | Malformed packet, ignored |

`lua_socket_log_errors on` (the default) also logs cosocket errors that Lua
already handled. Turn it off only where Lua logs the same `err` itself.

### Lua / cosocket lines to watch

| Pattern | Meaning |
|---------|---------|
| `failed to load Lua inlined code` or `bad byte-code header` | Wrong/unexpected LuaJIT bytecode in a `*_by_lua_file` |
| `attempt to yield across C-call boundary` | Yielding API in a non-yielding context |
| `socket busy reading` / `socket busy writing` | Two light threads fighting over one cosocket |
| `lua_` abort / `stack traceback` | Lua panic or an unhandled error from a handler |

## Metrics

OpenResty does not export application metrics by default. Decide a pipeline
(e.g. `lua-resty-prometheus` beside Nginx `stub_status`/`vts`), then wire the
counters below; until then, parse the error log as described above.

| Metric | Type | Why it matters |
|--------|------|----------------|
| DNS failures by the strerror text | counter | Separates NXDOMAIN from timeouts |
| Time from `ngx_resolve_name` to the handler | histogram | Shows nameserver latency versus `resolver_timeout` |
| Connects that reuse a pooled fd after a DNS change | counter | Stale address after failover |
| Cosocket connect/read/send timeouts | counter | Backend availability signal |
| Lua handler errors by phase | counter | Configuration/regression detection |

Do not add an "NXDOMAIN negative-cache hit" metric for this tree. A failed
RCODE frees the name node, so the next lookup sends a new query.

## Tracing or Correlation

- **Request identifier**: use Nginx's built-in `$request_id` (or an upstream
  `X-Request-ID` echoed via `log_format`) and correlate in Lua through
  `ngx.var.request_id`; include it in the access log and your own error lines.
- **Cross-service visibility**: carry the same id into backend calls where the
  protocol allows (headers for HTTP, or in-band for other protocols).
- **Diagnostic value**: pair the Lua `err` with `dig` against the same
  `resolver` address from the worker network for DNS issues; pair a Lua
  traceback with the request id for code issues.

## Alerts and Health Signals

| Condition | Signal | Expected action |
|-----------|--------|-----------------|
| Any `no resolver defined` | error log | Add `resolver` and reload |
| Timeout rate rising, NXDOMAIN flat | `Operation timed out` | Check UDP 53 and nameserver health |
| SERVFAIL spike | `Server failure` | Check that nameserver. Do not expect automatic failover on this RCODE. |
| `Operation refused` | error log | Fix the nameserver ACL |
| Lua error rate rising | `stack traceback` in error log | Correlate by `$request_id`; fix the handler/regression |
| Worker CPU pegged with Lua on top | profiler (XRay / flamegraph) | Profile hot Lua; look for blocking calls in request path |

## Operational Checklist

- Error log is searchable for `could not be resolved` (DNS) and `stack
  traceback` (Lua).
- `no resolver defined` pages a human.
- Timeout and NXDOMAIN are counted separately.
- `$request_id` appears in the access log and application error lines.
- `valid=` and keepalive are both known for services that change addresses.

## Related Documentation

- [Workflows](06-workflows.md)
- [Runbook](10-runbook.md)
- [Conventions](07-conventions.md)
