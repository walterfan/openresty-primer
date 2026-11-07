---
title: 'Appendix-01: FAQ'
updated_time: 2026-11-06
git_commit: 5f85578
updated_by: ai
source:
  - "nginx 1.31.1 / ngx_lua 0.10.31rc5 verified in this tree (DNS answers below)"
  - "doc/00-overview.md, doc/07-conventions.md, doc/08-lua-nginx-module.md (this PKB)"
owners:
  created_by: [Walter Fan]
  updated_by: [Walter Fan]
  responsible: [Walter Fan]
ttl: 6 months
review_status: pending
review_score: 0
reviewed_by: null
confidentiality: L1
summary: Frequently asked questions about writing and operating OpenResty/ngx_lua - language and runtime, cosockets and I/O, and the DNS resolution failure answers.
tags:
  domain: [openresty]
  technology: [lua, luajit, ngx_lua, nginx]
  concepts: [faq, language, cosocket, dns]
  audience: dev
  status: active
---

# Appendix-01: FAQ

<!-- maintained-by: human+ai -->

Frequently asked questions when writing or operating OpenResty/ngx_lua. The DNS
answers are verified against nginx 1.31.1 / ngx_lua 0.10.31rc5 in this tree.

## Language and Runtime

### Is OpenResty a fork of Nginx?

No. OpenResty is a higher-level platform that bundles an enhanced Nginx core,
an enhanced LuaJIT, vetted Lua libraries, and third-party C modules. Standard
Nginx configuration knowledge carries over.

### Can I use any Lua 5.x code?

OpenResty runs LuaJIT 2.1 with Lua 5.1 semantics (since ngx_lua v0.10.16 the
PUC-Rio interpreter is gone). Lua 5.3/5.4 features (native bitwise operators,
`//`, integer division, `table.pack`, and later library names) are not
portable. See [appendix-03-lua](appendix-03-lua.md).

### Why should I avoid Lua globals?

In ngx_lua, globals are per-request and cleared at the end of the request, so
module state must live in module tables or upvalues - and accidental globals
from typos are a common source of bugs. Use `local` everywhere. See
[Conventions](07-conventions.md).

### How do I share state between requests?

Within one worker: `lua_shared_dict` for named shared memory, or module-level
tables/upvalues (which persist for the worker lifetime). There is no direct
sharing across workers; use a backend (Redis, shared dict, etc.) when
cross-worker state is needed.

## Cosockets and I/O

### Why is my cosocket connect "blocking"?

It is not blocking the event loop - `ngx.socket.tcp()` is 100% non-blocking and
yields the coroutine. If the worker appears stalled, check for non-cosocket
blocking calls (`os.execute`, `io.*`, plain LuaSocket) in the request path.

### Why do I get `socket busy reading` / `socket busy writing`?

Two light threads are using the same cosocket in the same direction at once.
A cosocket allows one reader and one writer light thread, but not two readers
(or two writers).

### Why should I prefer `lua-resty-*` libraries over `ngx.location.capture`?

The `lua-resty-*` clients talk to backends over cosockets directly - more
flexible and memory-efficient than spawning Nginx subrequests, and they stay
inside the same event loop.

## DNS and Resolution

### Why does `connect("api.example.com", 443)` fail with `no resolver defined` even though the host can resolve the name?

Cosocket resolution uses only the Nginx `resolver` directive. It does not read
`/etc/resolv.conf`. Add `resolver` in the location that calls `connect`, then
reload.

### Does a SERVFAIL answer try the next nameserver?

No. In `ngx_resolver_process_a`, SERVFAIL, NXDOMAIN, NOTIMP, and REFUSED fail
every waiter on that name. The next nameserver is used when the UDP send fails,
or when the 5 second resend timer fires because nobody has answered yet.

### Why is a DNS timeout a 502 from `proxy_pass` but sometimes described as 504?

`ngx_http_upstream_resolve_handler` finalizes every non-zero resolve state,
including timeout, with `NGX_HTTP_BAD_GATEWAY`. Returning 504 for `Operation
timed out` is a Lua-level choice. See [Conventions](07-conventions.md).

### The DNS record changed and clients still hit the old address. Is the resolver stuck?

A successful answer is cached until `valid=` or the TTL, and a keepalive
connection keeps using the address it already connected to. Shorten both. A
failed lookup does not leave a negative entry in the name rbtree.

### When should Lua call `resty.dns.resolver` instead of `connect(host, port)`?

When the caller must choose nameservers, timeouts, or record types per query.
The library is `openresty/bundle/lua-resty-dns-0.23/`. After resolving, connect
to the address and set the original name on `Host` and TLS SNI. The module does
not share the `ngx_resolver` cache.

## Related Documentation

- [Workflows](06-workflows.md)
- [Runbook](10-runbook.md)
- [Conventions](07-conventions.md)
- [Data and API](05-data-and-api.md)
