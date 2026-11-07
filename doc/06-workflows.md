---
title: 06. Workflows
updated_time: 2026-10-06
git_commit: 1c9c605
updated_by: human+ai
source: []
owners:
  created_by: []
  updated_by: []
  responsible: []
ttl: null
review_status: pending
review_score: 0
reviewed_by: null
confidentiality: L1
summary: 06. Workflows
tags:
  domain: []
  technology: []
  concepts: []
  audience: dev
  status: draft
---

# 06. Workflows

<!-- maintained-by: human+ai -->

Ingested from `OpenResty HTTP请求中DNS解析失败处理完整解析与建议.md` and checked against nginx 1.31.1 and ngx_lua 0.10.31rc5 in this tree. Where that note disagrees with the code, this page follows the code.

## Workflow Index

1. [HTTP request DNS resolution and failure](#workflow-1)

Other request paths are documented below (docs build/publish and translation); broader runtime request paths are out of scope for now.

---

## Workflow 1

### Trigger and Goal

- **Trigger**: Lua or an HTTP upstream connects to a hostname that is not already an address literal.
- **Goal**: Turn that name into one or more addresses, then continue the TCP connect. On failure, surface a stable error string to Lua, or finalize the upstream request.

`lua-resty-http` is not vendored in this repository. It only creates a cosocket and calls `connect()`. DNS itself is Nginx `ngx_resolver`.

### Main Flow

```{mermaid}
flowchart TD
    lua["Lua connect hostname, port"] --> literal{"Address already parsed?"}
    literal -->|yes| tcp["TCP connect"]
    literal -->|no| start["ngx_resolve_start"]
    start --> nores{"Resolver configured?"}
    nores -->|no| noreErr["nil, no resolver defined to resolve"]
    nores -->|yes| query["ngx_resolve_name"]
    query --> hit{"Cache hit and still valid?"}
    hit -->|yes| addrs["Addresses to the connect path"]
    hit -->|no| send["UDP query, TCP if truncated"]
    send --> resp["ngx_resolver_process_response"]
    resp --> ok{"RCODE 0 with A or AAAA?"}
    ok -->|yes| cache["Store in the name rbtree, then connect"]
    ok -->|no| fail["Fail rn waiting list or leave the query outstanding"]
    fail --> luaErr["Lua nil plus could not be resolved"]
```

The resolve runs on the Nginx event loop. The Lua coroutine yields in `connect()` and resumes in `ngx_http_lua_socket_resolve_handler`.

### Key Steps

1. `ngx_http_lua_socket_tcp_connect` parses the host. If `u->resolved->sockaddr` is already set, it connects and does not call the resolver. See `openresty/bundle/ngx_lua-0.10.31rc5/src/ngx_http_lua_socket_tcp.c`.
2. Otherwise it calls `ngx_resolve_start(clcf->resolver, ...)`. `NGX_NO_RESOLVER` means the location has no `resolver` directive. Cosocket does not read `/etc/resolv.conf` and does not call `getaddrinfo()`.
3. `ngx_resolve_name` looks up the name rbtree. A live cache entry returns immediately. A miss builds a DNS query, sends it, and arms `resolver_timeout` on that context (`ngx_resolver_set_timeout`).
4. `ngx_resolver_process_response` checks the header, then `ngx_resolver_process_a` handles A and AAAA answers, CNAME chains, and non-zero RCODEs.
5. Every context on `rn->waiting` shares one in-flight query. On a terminal RCODE the code walks that list, sets `ctx->state`, and calls each handler. There is no function named `ngx_resolver_fail_waiting`.
6. The cosocket handler turns `ctx->state` into a Lua `nil, err` pair. `proxy_pass` and other upstream hostname resolves use `ngx_http_upstream_resolve_handler` instead.

### Error and Edge Cases

| Case | Where handled | Expected outcome |
|------|---------------|------------------|
| No `resolver` directive | `ngx_http_lua_socket_tcp.c` when `ngx_resolve_start` returns `NGX_NO_RESOLVER` | Immediate Lua error `no resolver defined to resolve "<host>"`. Upstream logs the same text and finalizes with 502. |
| `ngx_resolve_name` returns an error before a query is outstanding | same file, after `ngx_resolve_name` | Lua error `"<host> could not be resolved"` with no numeric code. Upstream finalizes with 500. |
| UDP send fails | `ngx_resolve_name_locked` in `ngx_resolver.c` | One immediate resend on the next nameserver. |
| No reply before the per-query resend time | `ngx_resolver_resend` | If `rn->waiting` is still set, `last_connection` advances and the query is sent again. `resend_timeout` is 5 seconds, set in `ngx_resolver_create`. |
| `resolver_timeout` fires | `ngx_resolver_timeout_handler` | That context gets `NGX_RESOLVE_TIMEDOUT` (`NGX_ETIMEDOUT`, 110 on Linux) and its handler runs. Default merge value is 30000 ms in `ngx_http_core_module.c`. |
| RCODE SERVFAIL, NXDOMAIN, NOTIMP, or REFUSED | `ngx_resolver_process_a` when `code` is non-zero | Every waiter fails immediately with that code. The name node is removed from the rbtree. This build does not rotate nameservers because of SERVFAIL. |
| RCODE FORMERR, or a code above REFUSED | `ngx_resolver_process_response` | Logged as `DNS error (...)` and dropped. Waiters stay until resend or `resolver_timeout`. |
| NOERROR with an empty answer and no sibling A/AAAA | `ngx_resolver_process_a` | Treated as `NGX_RESOLVE_NXDOMAIN`. |
| CNAME chain | `ngx_resolve_name_locked` and the CNAME branch in `ngx_resolver_process_a` | Followed until `NGX_RESOLVER_MAX_RECURSION` (50). Past that, waiters fail with `NGX_RESOLVE_NXDOMAIN`. |
| Transaction id mismatch | `ngx_resolver_process_a` | Logged as `wrong ident ... expect` and ignored. The outstanding query is not failed by that packet. |
| Label compression loop or a short packet | `ngx_resolver_copy` and the short-response path | Logged (`compression pointers loop` limit is 128) and the packet is dropped. Waiters stay until resend or timeout. |
| UDP truncated (`TC`) | `ngx_resolver_process_a` | Switches that query to TCP via `ngx_resolver_send_tcp_query`. |

On a terminal RCODE the code sets `ctx->valid` to now plus the `resolver` `valid=` time, or 10 seconds when `valid` is 0, then frees the name node. Later lookups do not hit a stored negative entry in the rbtree.

### Data and Contracts Involved

Lua `connect()` failure strings, built in `ngx_http_lua_socket_resolve_handler`:

| `ctx->state` | `ngx_resolver_strerror` | Lua `err` shape |
|--------------|-------------------------|-----------------|
| 1 `NGX_RESOLVE_FORMERR` | Format error | `<host> could not be resolved (1: Format error)` |
| 2 `NGX_RESOLVE_SERVFAIL` | Server failure | `<host> could not be resolved (2: Server failure)` |
| 3 `NGX_RESOLVE_NXDOMAIN` | Host not found | `<host> could not be resolved (3: Host not found)` |
| 4 `NGX_RESOLVE_NOTIMP` | Unimplemented | `<host> could not be resolved (4: Unimplemented)` |
| 5 `NGX_RESOLVE_REFUSED` | Operation refused | `<host> could not be resolved (5: Operation refused)` |
| `NGX_ETIMEDOUT` | Operation timed out | `<host> could not be resolved (<errno>: Operation timed out)` |

The numeric timeout value follows the host `ETIMEDOUT`. Match the text `Operation timed out`, not a fixed integer.

Upstream `proxy_pass` logs `%V could not be resolved (%i: %s)` and finalizes with `NGX_HTTP_BAD_GATEWAY` for every non-zero `ctx->state`, including timeout. A missing resolver is also 502. Only the immediate `ngx_resolve_name` failure path is 500.

### Code References

- `openresty/bundle/ngx_lua-0.10.31rc5/src/ngx_http_lua_socket_tcp.c` — connect, missing resolver, resolve handler
- `workspace/ngx_http_lua_socket_tcp.c` — local copy of the same cosocket path
- `openresty/bundle/nginx-1.31.1/src/core/ngx_resolver.c` — query, resend, response, timeout
- `openresty/bundle/nginx-1.31.1/src/core/ngx_resolver.h` — RCODE constants, `NGX_RESOLVER_MAX_RECURSION`
- `openresty/bundle/nginx-1.31.1/src/http/ngx_http_upstream.c` — `ngx_http_upstream_resolve_handler`
- `openresty/bundle/nginx-1.31.1/src/http/ngx_http_core_module.c` — `resolver_timeout` default 30000 ms

## Workflow 2 — Build and Publish the PKB Site

### Trigger and Goal

- **Trigger**: A maintainer (or CI) wants to produce the bilingual site and put
  it online.
- **Goal**: From clean sources, verify a strict build and push static HTML to
  GitHub Pages.

### Main Flow

1. `make deps` -> `uv sync --locked` installs the pinned Sphinx toolchain.
2. `make build` (Sphinx `-W -n`) renders English and zh_CN into `_build/site/`.
3. A landing `index.html` redirects visitors to `/en/` or `/zh/` by browser
   language.
4. `make publish` creates/refreshes a `gh-pages` worktree, copies
   `_build/site/*`, adds `.nojekyll`, commits, and pushes.

### Key Steps

- `doc/Makefile html-en` / `html-zh` / `render_landing.py` drive each build.
- `make publish` uses `git worktree add` on `gh-pages` so the source branch is
  untouched.

## Workflow 3 — Refresh the Chinese (zh_CN) Translation

### Trigger and Goal

- **Trigger**: English sources changed, so the zh_CN build would otherwise fall
  back to English.
- **Goal**: Re-extract msgids, merge into `.po`, translate the new strings, and
  compile `.mo` so the zh site matches the English source.

### Main Flow

1. `sphinx-build -b gettext . _build/gettext` regenerates `.pot` catalogs.
2. `sphinx-intl update --pot-dir _build/gettext --locale-dir locale -l zh_CN`
   merges into `locale/zh_CN/LC_MESSAGES/*.po` (msgmerge semantics preserve
   existing translations).
3. Translate new `msgid`s, then `sphinx-intl build` compiles `.mo`.
4. `make build` renders the zh site; `make pkb-check-i18n` verifies sync.

### Notes

- Keep the English page as the single source of truth; never edit `.mo` by hand.
- The whole-module ingest page (`08-lua-nginx-module.md`) is a verbatim upstream
  reference and intentionally falls back to English in zh_CN.

## Related Documentation

- [Architecture](02-architecture.md)
- [Data and API](05-data-and-api.md)
- [Conventions](07-conventions.md)
- [Runbook](10-runbook.md)
- [Observability](11-observability.md)
