---
title: "04. Repository Map"
updated_time: 2026-11-05
git_commit: 5f85578
updated_by: ai
source:
  - "doc/ (repository layout verified in this tree)"
  - "openresty/bundle/ nginx-1.31.1 / ngx_lua-0.10.31rc5 documented source paths (referenced, not vendored)"
owners:
  created_by: [Walter Fan]
  updated_by: [Walter Fan]
  responsible: [Walter Fan]
ttl: 6 months
review_status: pending
review_score: 0
reviewed_by: null
confidentiality: L1
summary: Layout of this repository - the doc/ Sphinx PKB (pages, locales, scripts, tooling) plus the upstream OpenResty source paths that the documentation cites.
tags:
  domain:
  - openresty
  technology:
  - nginx
  - ngx_lua
  - sphinx
  concepts:
  - repository-map
  - repository-layout
  audience: dev
  status: active
---

# 04. Repository Map

<!-- maintained-by: human+ai -->

This page maps the repository layout. The repository is a documentation
knowledge base: the `doc/` tree is the product, and the `openresty/bundle/`
paths used throughout the PKB are references to upstream source (not vendored
here).

## Directory Structure

```
openresty-primer/
├── Makefile                  # root convenience targets (deps/build/publish/serve)
├── README.md
├── LICENSE
└── doc/                      # Sphinx Project Knowledge Base (PKB_ROOT)
    ├── index.md              # Sphinx root + toctree
    ├── conf.py               # Sphinx config, i18n, title + metadata hooks
    ├── Makefile              # sphinx/gettext/agentbox/gh-pages targets
    ├── pyproject.toml        # Python deps (sphinx, myst-parser, sphinx-intl, ...)
    ├── uv.lock               # locked environment (uv sync --locked)
    ├── 00-overview.md ... 12-document.md   # numbered PKB pages
    ├── 08-lua-nginx-module.md              # ingested lua-nginx-module README
    ├── appendix-01-faq.md, appendix-02-glossary.md
    ├── ai-guide.md, diagrams-guide.md
    ├── adr/                  # ADR index + template
    ├── changes/              # change-proposal index + templates
    ├── locale/zh_CN/LC_MESSAGES/   # gettext .po/.mo catalogs
    ├── scripts/              # PKB helper scripts (pkb_frontmatter, pkb_query, ...)
    ├── _static/, _templates/ # CSS + language-switcher layout
    ├── functions/, agentbox.yaml   # optional AgentBox deploy
    └── _build/, _generated/  # gitignored build + sidecar artifacts
```

Upstream source paths cited by this PKB (not in this repo):

- `openresty/bundle/nginx-1.31.1/...`
- `openresty/bundle/ngx_lua-0.10.31rc5/...`
- `openresty/bundle/lua-resty-dns-0.23/...`

## Directory Responsibilities

| Path | Responsibility | Notes |
|------|----------------|-------|
| `doc/*.md` | Numbered knowledge pages (English source of truth) | Frontmatter per the metadata contract; see [12-document](12-document.md) |
| `doc/index.md` | Sphinx root and toctree | Register every page once here and in `scripts/gen_index.py` |
| `doc/locale/` | zh_CN gettext catalogs | `sphinx-intl update` merges from `_build/gettext` `.pot` files |
| `doc/scripts/` | Deterministic PKB helpers | `pkb_frontmatter.py`, `check_pkb_staleness.py`, `check_translation_sync.py`, `pkb_query.py`, ... |
| `doc/_build/`, `doc/_generated/` | Build output / sidecar artifacts | Gitignored; safe to delete |
| (documented only) `openresty/bundle/ngx_lua-0.10.31rc5/src/` | HTTP cosocket connect and Lua DNS errors | `ngx_http_lua_socket_tcp.c` |
| (documented only) `openresty/bundle/nginx-1.31.1/src/core/` | `ngx_resolver` query, cache, and timeout | `ngx_resolver.c`, `ngx_resolver.h` |
| (documented only) `openresty/bundle/lua-resty-dns-0.23/` | Optional Lua DNS client | Does not replace `ngx_resolver` unless called explicitly |

## Key Entry Points

| Area | File or directory | Why it matters |
|------|-------------------|----------------|
| Docs master | `doc/index.md` | Toctree; add new pages here |
| Docs build | `doc/Makefile`, `doc/conf.py` | `make deps` / `make build` / `make publish`, i18n and hooks |
| Build CI gate | `make build` (Sphinx `-W -n`) | Warnings become errors |
| Cosocket DNS (documented) | `openresty/bundle/ngx_lua-0.10.31rc5/src/ngx_http_lua_socket_tcp.c` | `connect()` starts resolve and formats `err` |
| Resolver (documented) | `openresty/bundle/nginx-1.31.1/src/core/ngx_resolver.c` | RCODE, resend, CNAME limit, timeout |
| Upstream DNS (documented) | `openresty/bundle/nginx-1.31.1/src/http/ngx_http_upstream.c` | Resolve failure becomes 502 |

## Organization Rules

- **Naming**: knowledge pages use `NN-slug.md` (stable numbering); helper
  scripts use `snake_case.py`; catalogs mirror page slugs
  (`00-overview.po`, `08-lua-nginx-module.po`).
- **Layering**: Lua and `proxy_pass` call `ngx_resolver`. `lua-resty-dns` is a
  separate client that uses cosockets to talk to DNS itself (documented only).
- **Module boundaries**: Resolver state stays in `ngx_resolver.c`. Lua only
  sees `nil, err` from the cosocket.
- **Scripts and tooling**: everything under `doc/scripts/` is run via `uv run
  --locked`; CI-intended checks are `make build`, `make pkb-check`,
  `make pkb-check-i18n`.

## Things New Contributors Usually Need First

- `doc/index.md` (navigation) and `doc/00-overview.md` (scope)
- `doc/Makefile` + `doc/conf.py` (how docs build)
- `doc/scripts/pkb_frontmatter.py` (metadata contract gate)
- (documented, for the DNS path) `ngx_resolver.c`, `ngx_http_lua_socket_tcp.c`,
  `ngx_http_upstream.c`

## Related Documentation

- [Architecture](02-architecture.md)
- [Data and API](05-data-and-api.md)
- [Conventions](07-conventions.md)
- [Documentation Process](12-document.md)
