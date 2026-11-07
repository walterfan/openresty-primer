---
title: "00. Project Overview"
updated_time: 2026-11-05
git_commit: 5f85578
updated_by: ai
source:
  - "https://github.com/openresty/lua-nginx-module/blob/master/README.markdown:217-304 @ 9661d95b5cbfaf5c34bf4a627896d16d6c2a34d3 (Description, Typical Uses; 2026-11-05)"
  - "https://github.com/openresty/lua-nginx-module/blob/master/README.markdown:703-751 @ 9661d95b5cbfaf5c34bf4a627896d16d6c2a34d3 (Known Issues; 2026-11-05)"
  - "https://github.com/openresty/lua-nginx-module/blob/master/README.markdown:1356-1392 @ 9661d95b5cbfaf5c34bf4a627896d16d6c2a34d3 (lua_code_cache; 2026-11-05)"
  - "https://github.com/openresty/lua-nginx-module/blob/master/README.markdown:8134-8180 @ 9661d95b5cbfaf5c34bf4a627896d16d6c2a34d3 (ngx.socket.tcp cosocket; 2026-11-05)"
  - "https://github.com/openresty/lua-nginx-module/blob/master/README.markdown:9013-9040 @ 9661d95b5cbfaf5c34bf4a627896d16d6c2a34d3 (ngx.thread.spawn light threads; 2026-11-05)"
  - "https://openresty.org/en/ (OpenResty official site, retrieved 2026-11-05)"
  - "nginx 1.31.1 / ngx_lua 0.10.31rc5 paths verified in this tree"
  - "[UNVERIFIED] https://www.akamai.com/cloud/guides/using-openresty/ - referenced by the requester; not retrievable (HTTP 403, no archive snapshot), so no claim on this page rests on it"
owners:
  created_by: [Walter Fan]
  updated_by: [Walter Fan]
  responsible: [Walter Fan]
ttl: 6 months
review_status: pending
review_score: 0
reviewed_by: null
confidentiality: L1
summary: OpenResty Primer - purpose, scope, users, and the DNS-failure view of OpenResty (Nginx + LuaJIT) documented in this knowledge base.
tags:
  domain:
  - openresty
  technology:
  - nginx
  - ngx_lua
  - luajit
  - lua-nginx-module
  concepts:
  - project-overview
  - dns-resolution
  audience: onboarding
  status: active
---

# 00. Project Overview

<!-- maintained-by: human+ai -->

> OpenResty is an open-source web platform that integrates an enhanced Nginx
> core with LuaJIT, turning the Nginx event model into an application runtime
> where Lua scripts drive HTTP processing and non-blocking I/O to remote
> backends. It is a higher-level application and gateway platform that uses
> Nginx as a component, **not** an Nginx fork. See the [Akamai "Using
> OpenResty" guide](https://www.akamai.com/cloud/guides/using-openresty/) and
> [openresty.org](https://openresty.org/en/).

## Purpose

This repository is an **OpenResty Primer**: a Project Knowledge Base and
reading companion for working with OpenResty - Nginx plus LuaJIT (ngx_lua). It
serves both human engineers and AI assistants who need to

- **locate** how OpenResty/ngx_lua behaves in the source tree,
- **understand** the architecture around HTTP cosockets and DNS resolution,
- **execute** build, runbook, and debugging workflows, and
- **verify** behavior against the real nginx 1.31.1 / ngx_lua 0.10.31rc5 code
  and the `lua-nginx-module` documentation.

The current focus is the **DNS-resolution failure path**: how a hostname lookup
fails through `ngx_resolver`, HTTP cosockets, and upstreams, plus the
`content`-phase directives of `lua-nginx-module` (e.g. `content_by_lua_file`).

## What OpenResty Is

OpenResty is a web platform that **embeds LuaJIT 2.0/2.1 into Nginx**.
`lua-nginx-module` (ngx_lua) is its core component - "if you are using this
module, then you are essentially using OpenResty". Since ngx_lua `v0.10.16` the
standard PUC-Rio Lua interpreter is no longer supported; "Lua" here always means
LuaJIT.

The design intent is to run the server-side application *inside* the Nginx
worker, so a request never leaves the event loop to reach a backend. Typical
uses include access control and security checks before a request reaches the
upstream, mashing up several upstreams, choosing an upstream on the fly from
data in Redis/MySQL, complex URL dispatch at the rewrite phase, arbitrary
response-header manipulation, and custom caching for subrequests.

### Strengths and Limitations

1. strength
   1. Lua code can be **100% non-blocking** on network traffic, as long as the Nginx API for Lua is used for upstream access (MySQL, PostgreSQL, Memcached, Redis, HTTP).
   2. Performance is "comparable with native C programs" in CPU time and memory footprint, thanks to LuaJIT 2.x.
   3. One Lua VM per worker is shared by all requests, with request isolation via lightweight coroutines, resulting in a small memory footprint under heavy load.
   4. Loaded Lua modules persist at worker level, so hot code is compiled once.
   5. A rich `lua-resty-*` ecosystem (redis, mysql, memcached, dns, lock, lrucache, upload, websocket) provides access to almost any Nginx module via `ngx.location.capture`.
   6. Edit-and-refresh development is possible by switching `lua_code_cache off`.
   7. The upstream is mature and declared **production ready**.

2. limitation
   1. Blocking the worker is easy to do by accident: any library that is not cosocket-based (plain `io.*`, LuaSocket, `os.execute`) stalls every request on that worker.
   2. Only the **HTTP subsystem** is addressed downstream (HTTP 0.9/1.0/1.1/2.0, WebSocket); generic downstream TCP needs the separate `ngx_stream_lua` module.
   3. Lua **global** variables are per-request and cleared at request end; misusing them causes cross-request surprises, table lookups, and hard-to-debug typos. Always `local x = require('x')`.
   4. `dofile`/`require` are C functions in LuaJIT, so calling a yielding API (`ngx.location.capture`, `ngx.exit`, ...) at a Lua file's *top-level* scope raises "attempt to yield across C-call boundary".
   5. Not every phase can yield: directives injected into `ngx_http_rewrite_module` (e.g. `set_by_lua`) cannot use cosockets, sleeping, or light threads.
   6. `lua_code_cache off` runs every request in a **separate Lua VM**; it is dev-only and can drop "hello world" throughput by an order of magnitude.
   7. Platform wart: on macOS `tcpsock:connect` may report success even for `Connection Refused`; the real error only surfaces on the next cosocket operation.

## Programming Model: Synchronous Code, Non-blocking I/O

The defining property of ngx_lua is that application code **reads like blocking
code but executes without blocking the worker**: you write "synchronous but
still non-blocking access to the database backends and other storage".

- **Coroutines as the request context.** Nginx's event model is callback-driven;
  ngx_lua integrates Lua coroutines into it so each request handler is a
  coroutine. The Lua VM is shared across all requests of a worker to minimise
  memory, and "request contexts are segregated using lightweight Lua
  coroutines". Each `*_by_lua*` handler runs as a newly spawned coroutine in an
  independent global environment (a sandbox).
- **Light threads.** `ngx.thread.spawn` creates a "light thread" - a special
  Lua coroutine scheduled by ngx_lua - to run work concurrently within one
  request. The handler body itself is a boilerplate light thread called the
  *entry thread*. Scheduling is cooperative, not preemptive: a light thread runs
  exclusively until it yields on I/O, so CPU-bound Lua still blocks its worker.
- **Cosockets.** `ngx.socket.tcp()` returns a *cosocket*: an API intentionally
  compatible with LuaSocket's TCP API but "100% nonblocking out of the box".
  Under the hood a `connect`/`receive`/`send` yields the coroutine back to the
  Nginx event loop and resumes it when the event fires. Cosockets support
  timeouts, TLS handshakes, connection pooling (`setkeepalive`), and since
  `0.9.9` full-duplex use by one reader and one writer light thread.
  A cosocket has **exactly the lifetime of the handler that created it** - it
  must never be shared across requests or passed into a timer callback.
- **Hostname resolution is part of this model.** A cosocket `connect()` to a
  name does not call `getaddrinfo()`; it drives Nginx's own `ngx_resolver` and
  yields while the DNS query is in flight - which is precisely the failure path
  this PKB documents in [Workflows](06-workflows.md).
- **Dynamic behaviour.** Lua is loaded at runtime, so routing, access rules, and
  upstream selection can be computed per request. `*_by_lua_file` paths may
  contain Nginx variables for dynamic dispatch (with the matching injection
  risk), files may hold precompiled LuaJIT bytecode, and `lua_code_cache off`
  gives an edit-and-refresh loop during development. See
  [lua-nginx-module Directive Reference](08-lua-nginx-module.md).

## How Nginx and LuaJIT Fit Together

The integration is deliberately seamless rather than a bolt-on scripting layer:

- **LuaJIT lives inside the worker process**, not in an external interpreter or
  a FastCGI sidecar, so there is no IPC on the request path and the JIT keeps
  hot handlers close to C speed.
- **Lua hooks onto Nginx's request phases.** Handler directives map onto the
  existing phase machinery (`set_by_lua*`, `rewrite_by_lua*`, `access_by_lua*`,
  `content_by_lua*`, `header_filter_by_lua*`, `body_filter_by_lua*`,
  `log_by_lua*`, plus `init_by_lua*` and `ngx.timer.*`), so Lua extends the
  pipeline instead of replacing it.
- **Lua reuses the Nginx runtime**, not its own: the same event loop, the same
  `resolver`, the same upstream/proxy machinery, SSL stack, shared memory zones
  (`lua_shared_dict`), logging, and timers.
- **Nginx C modules remain reachable** from Lua through
  `ngx.location.capture` subrequests, although the `lua-resty-*` libraries are
  usually preferred as more flexible and memory-efficient.
- **OpenResty is not an Nginx fork.** It is a higher-level platform that bundles
  an enhanced Nginx core, an enhanced LuaJIT, vetted Lua libraries, and
  third-party C modules, so the standard Nginx configuration knowledge carries
  over unchanged.

## Scope Boundaries

| In scope | Out of scope |
|----------|--------------|
| OpenResty/ngx_lua source reading: DNS failure path in cosocket connect and upstream | FreeSWITCH, OpenSIPS, and other SIP components |
| `lua-nginx-module` directive reference (content-phase directives, LuaJIT bytecode) | Company-internal build/deploy procedures for OpenResty microservices |
| Build, runbook, observability, and testing guidance for this OpenResty tree | Non-software assets and unread source |
| Bilingual (en/zh_CN) Sphinx documentation | Authoring a full Chinese rewrite of the ingested upstream README (delegated: the ingest page falls back to English in zh_CN) |

## Key Users and Use Cases

- **Engineers debugging DNS failures**: reproduce and fix `no resolver
  defined`, `Operation timed out`, NXDOMAIN, and SERVFAIL errors via the
  runbook and conventions.
- **Engineers learning OpenResty/ngx_lua**: follow the architecture, repo-map,
  and the lua-nginx-module directive pages.
- **AI assistants / coding agents**: use the layered reading order in [How to
  Use This Documentation for AI](ai-guide.md) and the retrieval helpers
  (`scripts/pkb_query.py`) to stay on-path.
- **Documentation maintainers**: refresh pages per the [Documentation
  Process](12-document.md).

## System Snapshot

- **Deployment model**: documentation knowledge base (not a deployable
  application). There is no server to run to "use" the PKB itself.
- **Core runtime shape**: Sphinx + MyST bilingual site; the documented subject
  is the OpenResty runtime (Nginx event loop + LuaJIT coroutines).
- **Primary data path**: request -> `ngx_lua` cosocket or upstream ->
  `ngx_resolver` -> configured nameservers (see [Workflows](06-workflows.md)).
- **Top risk or constraint**: facts must stay locked to verified source
  versions (nginx 1.31.1, ngx_lua 0.10.31rc5, lua-nginx-module README); drift in
  upstream code can silently invalidate the docs.

## Quality Targets

| Area | Target | Notes |
|------|--------|-------|
| Performance | Docs build fast and token-cheap: rule-based freshness checks before LLM passes | `make build` strict (`-W`) |
| Availability | Bilingual site builds and serves on GitHub Pages (`make publish`) | en + zh_CN |
| Correctness | Every claim cites verified paths/URLs in `source` | `source-verified` is the AI ceiling |
| Security | Public content is `L1`; no credentials or internal hosts | Confidentiality policy |

## Key Project Facts

- **Code roots**: upstream OpenResty sources are referenced (not vendored):
  `openresty/bundle/nginx-1.31.1`, `openresty/bundle/ngx_lua-0.10.31rc5`.
- **Primary interfaces**: Sphinx/MyST docs (`doc/`), the Makefile targets
  (`make deps|build|publish`), and `scripts/pkb_query.py`.
- **Sources of truth docs**: nginx / ngx_lua source in the tree, the
  [lua-nginx-module README](https://github.com/openresty/lua-nginx-module), and
  the [Akamai "Using OpenResty" guide](https://www.akamai.com/cloud/guides/using-openresty/).

## Related Documentation

- [Quick Start](01-quick-start.md)
- [Architecture](02-architecture.md)
- [Tech Stack](03-tech-stack.md)
- [Repository Map](04-repo-map.md)
- [Runbook](10-runbook.md)
- [lua-nginx-module Directive Reference](08-lua-nginx-module.md)
