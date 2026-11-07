---
title: "03. Tech Stack"
updated_time: 2026-11-05
git_commit: 5f85578
updated_by: ai
source:
  - "doc/pyproject.toml (Sphinx/MyST toolchain pinned versions, verified in this tree)"
  - "https://github.com/openresty/lua-nginx-module/blob/master/README.markdown:217-304 @ 9661d95b5cbfaf5c34bf4a627896d16d6c2a34d3 (runtime stack: Nginx + LuaJIT + ngx_lua)"
  - "doc/00-overview.md (scope and runtime facts, this PKB)"
  - "doc/02-architecture.md (runtime architecture, this PKB)"
owners:
  created_by: [Walter Fan]
  updated_by: [Walter Fan]
  responsible: [Walter Fan]
ttl: 6 months
review_status: pending
review_score: 0
reviewed_by: null
confidentiality: L1
summary: Technologies used to build this PKB site on top of OpenResty - the documented runtime stack (Nginx + LuaJIT + ngx_lua + cosockets) and the docs toolchain (Sphinx/MyST/sphinx-intl/uv).
tags:
  domain:
  - openresty
  technology:
  - nginx
  - lua
  - luajit
  - ngx_lua
  - sphinx
  - myst
  - uv
  concepts:
  - tech-stack
  - docs-toolchain
  audience: dev
  status: active
---

# 03. Tech Stack

<!-- maintained-by: human+ai -->

This page covers two things: the **runtime stack** that this knowledge base
documents (OpenResty) and the **docs toolchain** that builds the PKB site
itself. Versions below are verified in this tree.

## System View

| Layer | Main technology | Why it exists in this repo |
|-------|-----------------|----------------------------|
| Interface (documented runtime) | Nginx 1.31.1 | Enhanced Nginx core; request phases that Lua hooks into |
| Runtime (documented subject) | LuaJIT 2.1 + `lua-nginx-module` (ngx_lua) | Embeds Lua coroutines into the Nginx event model; 100% non-blocking |
| Backend access (documented subject) | Cosockets + `lua-resty-*` libraries | Non-blocking access to Redis/MySQL/Memcached/DNS/HTTP |
| Docs interface (this repo) | Sphinx + Sphinx RTD theme + sphinx-design | Renders the MyST knowledge base into a browsable site |
| Docs content | MyST (myst-parser 4.0.1) | Markdown with Sphinx directives, admonitions, Mermaid |
| Docs i18n | sphinx-intl 2.3.2 + gettext (`.pot`/`.po`/`.mo`) | English single source of truth; zh_CN via catalogs |
| Build and packaging (this repo) | `uv` (uv.lock) + Makefile | Locked, reproducible env; `make deps` / `make build` / `make publish` |
| Deployment (this repo) | GitHub Pages (`gh-pages`), optional AgentBox | `make publish` pushes `doc/_build/site` to Pages |

## Main Languages and Frameworks

- **Primary language (documented runtime)**: Lua, compiled by LuaJIT 2.1.
  Since ngx_lua `v0.10.16` the standard PUC-Rio Lua interpreter is no longer
  supported.
- **Secondary language (this repo)**: Python 3.11 for the Sphinx build, the
  `scripts/` helpers, and the metadata footer renderer.
- **Primary framework (documented runtime)**: `lua-nginx-module` (ngx_lua),
  the core component of OpenResty.


## Key Dependencies

| Package or crate | Area | Why it matters |
|------------------|------|----------------|
| Nginx 1.31.1 | runtime | `ngx_resolver`, event loop, upstream machinery (documented, not vendored) |
| LuaJIT 2.1 | runtime | JIT compilation; coroutines; bytecode loading for `*_by_lua_file` |
| `lua-nginx-module` | runtime | phase directives; cosockets; light threads; Nginx API for Lua |
| `lua-resty-*` (redis, mysql, dns, lock, lrucache) | runtime | non-blocking backend clients used in typical OpenResty apps |


## Runtime Interaction Model

For the **documented runtime**: a client request enters the Nginx event loop
and the `content_by_lua*`-style handler runs as a Lua coroutine; any backend
talk happens over cosockets (which yield the coroutine back to the event loop)
rather than blocking. See [Architecture](02-architecture.md) and
[Workflows](06-workflows.md).




## Common Misconceptions

| Misconception | Reality in this repo |
|---------------|----------------------|
| "OpenResty is a fork of Nginx" | It is a higher-level platform that uses Nginx as a component; standard Nginx config knowledge carries over |
| "Lua here is PUC-Rio Lua 5.1" | Since ngx_lua v0.10.16 it is LuaJIT only |
| "Hostname connects use the system resolver" | They use Nginx `ngx_resolver` and the `resolver` directive; no `getaddrinfo` fallback |
| "All Lua is 100% non-blocking" | Only when using cosockets / the Nginx API for Lua; blocking calls stall the worker |

## Related Documentation

- [Architecture](02-architecture.md)
- [Repository Map](04-repo-map.md)
- [lua-nginx-module Directive Reference](08-lua-nginx-module.md)
