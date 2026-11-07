---
title: "02. Architecture"
updated_time: 2026-11-05
git_commit: 5f85578
updated_by: ai
source:
  - "doc/ (this repository layout, verified in tree)"
  - "doc/conf.py (Sphinx i18n + metadata footer hooks, verified in this tree)"
  - "nginx 1.31.1 / ngx_lua 0.10.31rc5 DNS resolution path verified in this tree (sections below)"
  - "https://github.com/openresty/lua-nginx-module/blob/master/README.markdown:220-303 @ 9661d95b5cbfaf5c34bf4a627896d16d6c2a34d3 (runtime embedding, phases, cosockets)"
owners:
  created_by: [Walter Fan]
  updated_by: [Walter Fan]
  responsible: [Walter Fan]
ttl: 6 months
review_status: pending
review_score: 0
reviewed_by: null
confidentiality: L1
summary: Architecture of both this documentation knowledge base and the OpenResty/ngx_lua runtime it documents, with the verified C4 view of the DNS resolution path.
tags:
  domain:
  - openresty
  technology:
  - nginx
  - ngx_lua
  - sphinx
  concepts:
  - architecture
  - c4
  - dns-resolution
  audience: dev
  status: active
---

# 02. Architecture

<!-- maintained-by: human+ai -->

This page has two layers. The first describes **this repository** - a Sphinx
knowledge base (the "system" you are looking at). The second documents the
**OpenResty/ngx_lua runtime**, with a C4 view of the DNS-resolution path that
is verified against nginx 1.31.1 / ngx_lua 0.10.31rc5 in this tree.

## This Repository (the PKB site)

### Context

- **Actors**: human engineers and AI assistants reading OpenResty/ngx_lua
  documentation; maintainers editing `doc/*.md`.
- **External systems**: GitHub Pages serves the built site; no runtime backend
  is involved.

### Container View

| Container | Responsibility | Technology | Depends on |
|-----------|----------------|------------|------------|
| Docs source | English source of truth + `zh_CN` catalogs | Markdown/MyST + `.po`/`.mo` | `doc/*.md`, `locale/zh_CN/LC_MESSAGES/` |
| Docs build | Extract gettext, compile translations, render HTML | Sphinx 8.2.3 + myst-parser + sphinx-intl | `uv.lock`, `conf.py`, `Makefile` |
| Published site | Bilingual static HTML | Sphinx RTD theme | `_build/site/{en,zh}`, landing `index.html` |
| Publishing | Push built site to GitHub Pages | `git worktree` -> `gh-pages` | `make publish` |

### Component View (key pieces)

- `conf.py`: Sphinx config, MyST extensions, i18n routing
  (`available_languages`), the language-switcher context, the title-translation
  hook, and the metadata-footer hook.
- `scripts/pkb_metadata_footer.py`: appends the compact one/two-line metadata
  footer rendered from each page's YAML frontmatter.
- `scripts/` helpers: `pkb_frontmatter.py`, `check_pkb_staleness.py`,
  `check_translation_sync.py`, `gen_index.py`, `pkb_query.py`.

### Code-Level View

| Area | Important files | Why it matters |
|------|-----------------|----------------|
| Metadata render | `scripts/pkb_metadata_footer.py` | Compact footer shows owners/commit/TTL |
| Title i18n | `conf.py:_translate_titles` | Translates the H1 and nav titles in zh_CN |
| Language switcher | `_templates/layout.html` | Amber bar under "openresty" in the sidebar |

## Documented Runtime (OpenResty/ngx_lua)

### Context

Who runs this OpenResty: each reader or operator installs and runs OpenResty
per [Quick Start](01-quick-start.md); this tree documents the behavior but does
not run a server itself. External systems a typical OpenResty app may call are
backends such as MySQL, PostgreSQL, Redis, Memcached, DNS, or upstream HTTP
services, accessed non-blockingly through cosockets.

What this tree does contain (as documented facts): nginx 1.31.1 plus the
OpenResty Lua modules under `openresty/bundle/`. Hostname connects from Lua do
not use the system resolver. They use Nginx `ngx_resolver` and the nameservers
from the `resolver` directive.

```{mermaid}
flowchart LR
    caller["Lua or proxy_pass"] --> cosocket["ngx_lua cosocket or upstream"]
    cosocket --> resolver["ngx_resolver"]
    resolver --> ns["Configured nameservers"]
```

### Container View

| Container | Responsibility | Technology | Depends on |
|-----------|----------------|------------|------------|
| Worker process | Runs the request and the resolver state machine | nginx 1.31.1 event loop | `resolver` addresses, UDP/TCP port 53 |
| Lua request | Starts `connect()` and reads `nil, err` | ngx_lua 0.10.31rc5 cosocket | Location `resolver` and `resolver_timeout` |

There are no other deployable containers in this tree; the PKB ships only the
documentation. Operators may add the usual OpenResty containers (Nginx workers,
Redis/MySQL backends) at run time.

### Component View

#### Resolver and cosocket

- **Responsibilities**: Map a hostname to addresses, cache successful answers in per-resolver red-black trees, and fail or resume every request waiting on that name.
- **Key entry points**: `ngx_http_lua_socket_tcp_connect`, `ngx_resolve_start`, `ngx_resolve_name`, `ngx_resolver_process_response`, `ngx_http_lua_socket_resolve_handler`, `ngx_http_upstream_resolve_handler`.
- **Important dependencies**: The `resolver` directive on the location or upstream. IPv6 queries are on unless `ipv6=off` (`r->ipv6` defaults to 1). A second nameserver is only a failover target for send failure and for the 5-second resend timer, not for SERVFAIL.
- **Failure modes**: Missing resolver, query timeout, non-zero RCODE, CNAME chain longer than 50, or a dropped malformed packet that later hits `resolver_timeout`. See [Workflows](06-workflows.md).

`openresty/bundle/lua-resty-dns-0.23/` is a separate cosocket DNS client. It does not replace `ngx_resolver` unless Lua calls it and then connects to the resulting address itself.

### Code-Level View

| Area | Important files or symbols | Why it matters |
|------|-----------------------------|----------------|
| Cosocket resolve | `ngx_http_lua_socket_tcp.c` `ngx_resolve_start`, resolve handler | Produces the Lua error strings |
| Resolver core | `ngx_resolver.c` `ngx_resolver_process_a`, `ngx_resolver_resend`, `ngx_resolver_timeout_handler`, `ngx_resolver_strerror` | RCODE handling, nameserver rotation, timeout |
| Upstream resolve | `ngx_http_upstream.c` `ngx_http_upstream_resolve_handler` | Maps every resolve failure to 502 |
| Limits | `ngx_resolver.h` `NGX_RESOLVER_MAX_RECURSION` 50 | CNAME chase cap |

### Key Runtime Flows

Success and failure steps are in [Workflows](06-workflows.md). Retry and HTTP
status guidance for callers is in [Conventions](07-conventions.md).

### Cross-Cutting Concerns

- **Authentication and authorization**: not applicable to this static PKB; in
  the documented runtime, access control is implemented in Lua (usually in
  `access_by_lua*`) rather than in the resolver path.
- **Error handling**: Cosocket returns the error to Lua. Upstream turns resolve
  failure into 502. See [Data and API](05-data-and-api.md).
- **Logging and tracing**: Error-log lines are listed in
  [Observability](11-observability.md). `lua_socket_log_errors` defaults to
  `on`.
- **Caching**: Successful answers stay in the name rbtree until `valid=` or the
  record TTL. A failed RCODE deletes that node. `resolver_timeout` does not
  control the resend interval.
- **Configuration and secrets**: Nameserver addresses belong in `nginx.conf`,
  not in source; secrets belong in environment variables or a secrets store
  (see [Conventions](07-conventions.md)).

### Deployment and Scaling Notes

- **Environments**: this PKB does not publish resolver addresses for dev,
  staging, or production; operators confirm the `resolver` and `resolver_timeout`
  values for each environment (see the example in [Conventions](07-conventions.md)).
- **Scaling model**: Each worker has its own resolver trees and in-flight queries.
- **Recovery considerations**: A single nameserver is a single point of failure
  for queries that get no UDP reply. SERVFAIL from that server still fails the
  request without trying the next server.

## Related Documentation

- [Workflows](06-workflows.md)
- [Data and API](05-data-and-api.md)
- [Runbook](10-runbook.md)
- [Repository Map](04-repo-map.md)
