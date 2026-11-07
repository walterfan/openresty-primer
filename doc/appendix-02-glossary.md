---
title: 'Appendix-02: Glossary'
updated_time: 2026-11-06
git_commit: 5f85578
updated_by: ai
source:
  - "nginx 1.31.1 / ngx_lua 0.10.31rc5 verified in this tree (DNS terms below)"
  - "doc/08-lua-nginx-module.md, doc/appendix-03-lua.md (Lua/LuaJIT terms, this PKB)"
owners:
  created_by: [Walter Fan]
  updated_by: [Walter Fan]
  responsible: [Walter Fan]
ttl: 6 months
review_status: pending
review_score: 0
reviewed_by: null
confidentiality: L1
summary: Terms used across this OpenResty knowledge base - Lua and LuaJIT, ngx_lua APIs and cosockets, and the DNS resolution path.
tags:
  domain: [openresty]
  technology: [lua, luajit, ngx_lua, nginx]
  concepts: [glossary, language, runtime, dns]
  audience: dev
  status: active
---

# Appendix-02: Glossary

<!-- maintained-by: human+ai -->

Terms used across this knowledge base. DNS definitions match nginx 1.31.1 in
this tree; Lua/LuaJIT definitions follow the [Lua and LuaJIT
appendix](appendix-03-lua.md) and the [lua-nginx-module reference](08-lua-nginx-module.md).

## Terms

| Term | Meaning | Notes |
|------|---------|-------|
| OpenResty | Web platform embedding LuaJIT into Nginx | `lua-nginx-module` is its core; not an Nginx fork |
| LuaJIT | Lua 5.1-compatible VM with a tracing JIT | Used by OpenResty; FFI and `bit` extensions |
| ngx_lua | `lua-nginx-module`; embeds Lua handlers into Nginx phases | Also called "the Lua module" of OpenResty |
| Nginx API for Lua | The `ngx.*` surface from Lua | `ngx.var`, `ngx.req.*`, `ngx.location.capture`, `ngx.say`, ... |
| Cosocket | Nonblocking socket driven by ngx_lua on the Nginx event loop | `ngx.socket.tcp():connect()` |
| Light thread | A coroutine scheduled by ngx_lua within a request | `ngx.thread.spawn`; cooperative, not preemptive |
| `lua_shared_dict` | Per-worker shared memory dictionary | `ngx.shared.DICT`; no cross-worker sharing |
| Coroutine | Cooperative execution context in Lua | Yields explicitly; integrated with Nginx's event loop |
| Closure | Function capturing enclosing locals | Drives module state and worker-local caches |
| Metatable / metamethod | Customizes table/userdata operations | `__index`, `__newindex`, `__tostring`, `__gc` |
| FFI | LuaJIT foreign-function interface to C | `ffi.*`; crosses the C boundary |
| JIT trace | Recorded hot execution path compiled to machine code | LuaJIT tracing JIT |
| `resolver` | Directive that supplies nameserver addresses to `ngx_resolver` | Required for hostname connects. No libc fallback. |
| `resolver_timeout` | Absolute timeout for one resolve context | Default 30000 ms. Distinct from the 5 second resend interval. |
| `valid=` | Override for how long a successful answer may be cached | Omitted means the record TTL. Not a negative-cache TTL in the name rbtree. |
| RCODE | Low 4 bits of the DNS response flags | 0 NOERROR, 1 FORMERR, 2 SERVFAIL, 3 NXDOMAIN, 4 NOTIMP, 5 REFUSED |
| `NGX_RESOLVE_TIMEDOUT` | `ctx->state` after `resolver_timeout` | Same value as `ETIMEDOUT`. String is `Operation timed out`. |
| `rn->waiting` | Linked list of contexts waiting on one name | All of them fail together on a terminal RCODE |
| `NGX_RESOLVER_MAX_RECURSION` | CNAME chase limit | 50. The next chase fails with NXDOMAIN. |
| Nameserver rotation | Next `resolver` address after a send failure or a resend timeout | Not triggered by SERVFAIL |
| SNI | TLS server name sent during handshake | Must stay the original hostname when connecting to a resolved IP |

## Related Documentation

- [Workflows](06-workflows.md)
- [Data and API](05-data-and-api.md)
- [Lua and LuaJIT Key Points](appendix-03-lua.md)
- [Runbook](10-runbook.md)
