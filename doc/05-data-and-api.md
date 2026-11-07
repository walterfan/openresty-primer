---
title: "05. Data and API"
updated_time: 2026-11-06
git_commit: 5f85578
updated_by: ai
source:
  - "https://github.com/openresty/lua-nginx-module/blob/master/README.markdown @ 9661d95b5cbfaf5c34bf4a627896d16d6c2a34d3 (Nginx API for Lua, cosockets, light threads)"
  - "nginx 1.31.1 / ngx_lua 0.10.31rc5 verified in this tree (DNS error contract below)"
  - "doc/08-lua-nginx-module.md (directive reference, this PKB)"
owners:
  created_by: [Walter Fan]
  updated_by: [Walter Fan]
  responsible: [Walter Fan]
ttl: 6 months
review_status: pending
review_score: 0
reviewed_by: null
confidentiality: L1
summary: The OpenResty/ngx_lua data and API surface - the Nginx API for Lua, cosockets, shared state, HTTP status mapping, and the verified DNS error contract as one example.
tags:
  domain:
  - openresty
  technology:
  - ngx_lua
  - nginx
  - lua
  concepts:
  - api
  - contracts
  - error-handling
  audience: dev
  status: active
---

# 05. Data and API

<!-- maintained-by: human+ai -->

This page covers the API and data contracts of OpenResty/ngx_lua as used from
Lua. It is not an exhaustive reference (see
[08-lua-nginx-module](08-lua-nginx-module.md) for every directive and API);
here we capture the contracts that most application code depends on, including
the DNS-resolution error contract as a worked example.

## The Nginx API for Lua

Lua code in OpenResty talks to Nginx through the `ngx.*` API - a coroutine
context is created per request and the API exposes request state, output, and
subsystems.

| Area | Representative API | Contract notes |
|------|--------------------|----------------|
| Request | `ngx.var`, `ngx.req.*`, `ngx.header.*`, `ngx.ctx` | Per-request state; `ngx.ctx` survives across phases within one request |
| Output | `ngx.print`, `ngx.say`, `ngx.flush`, `ngx.eof` | Write the response body; runs in content phase |
| Control | `ngx.exit`, `ngx.redirect`, `ngx.exec`, `ngx.location.capture*` | Terminate or jump; `capture` runs a subrequest and can yield |
| Timers | `ngx.timer.at`, `ngx.timer.every` | Run later on the same worker; must not block |
| Shared state | `ngx.shared.DICT` (lua_shared_dict), module-level tables | per-worker shared memory; no cross-worker sharing |
| Logging | `ngx.log(level, ...)` | Writes to the Nginx error log |
| Cosocket | `ngx.socket.tcp`, `udp`, `stream` | 100% non-blocking; see below |

## Cosockets and the Connect Contract

A cosocket (`ngx.socket.tcp()`) is the sanctioned way to talk to backends:

- `sock:connect(host, port)` returns `1` on success, or `nil` plus `err`.
- It yields the current coroutine back to the event loop while the TCP connect
  and any hostname resolution are in flight.
- Resolving a **hostname** uses Nginx `ngx_resolver` (the `resolver`
  directive), never the system resolver. Connecting to an **address literal**
  skips DNS.
- Timeouts are set with `settimeout(ms)` / `settimeouts(connect, send, read)`;
  idle sockets are returned to the pool with `setkeepalive()`.

## HTTP Status and Error Mapping

Distinguish the error the caller sees (a Lua `err` string, a cosocket
`nil, err`) from the HTTP status returned to the client.

- `proxy_pass` to a hostname returns **502** for any resolve failure, including
  timeout. Only a Lua `content_by_lua*` handler can choose a different status.
- Cosocket failures surface as `nil, err`; translate them to a deliberate HTTP
  status in Lua (see [Conventions](07-conventions.md)).

## Worked Example: the DNS Error Contract

The DNS failure contract between `ngx_resolver`, the HTTP cosocket, and
upstream is verified against nginx 1.31.1 / ngx_lua 0.10.31rc5 in this tree.

### Lua error strings

| Condition | `err` |
|-----------|--------|
| No resolver | `no resolver defined to resolve "<host>"` |
| `ngx_resolve_name` failed immediately | `<host> could not be resolved` |
| Resolver finished with `ctx->state` | `<host> could not be resolved (<state>: <ngx_resolver_strerror>)` |

`ngx_resolver_strerror` maps 1-5 to `Format error`, `Server failure`,
`Host not found`, `Unimplemented`, and `Operation refused`.
`NGX_RESOLVE_TIMEDOUT` maps to `Operation timed out`.

### Suggested HTTP status and retry

| Lua `err` contains | HTTP status | Retry in this request |
|--------------------|-------------|-----------------------|
| `Operation timed out` | 504 (Lua choice) | Yes, bounded |
| `Server failure` | 502 | Yes, bounded |
| `Host not found` | 502 | No (NXDOMAIN) |
| `Operation refused` | 502 | No |
| `Format error` / `Unimplemented` | 502 | No |
| `no resolver defined` | 500 | No (config error) |
| `could not be resolved` (no code) | 502 | No, until cause known |

### Key internals

| Name | Trigger | Consumer or handler | Notes |
|------|---------|---------------------|-------|
| `ngx_resolve_name` | Hostname connect | Resolver, then cosocket or upstream handler | Yields the Lua coroutine while in flight |
| `ngx_resolver_timeout_handler` | `ctx->timeout` | The ctx handler | Sets `NGX_RESOLVE_TIMEDOUT` |
| `ngx_resolver_resend` | Node `expire` with waiters | Next nameserver | Not used for a received SERVFAIL |

## Related Documentation

- [lua-nginx-module Directive Reference](08-lua-nginx-module.md)
- [Conventions](07-conventions.md)
- [Workflows](06-workflows.md)
