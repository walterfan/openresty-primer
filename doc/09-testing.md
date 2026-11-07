---
title: "09. Testing Strategy"
updated_time: 2026-11-05
git_commit: 5f85578
updated_by: ai
source:
  - "doc/Makefile (build/verify targets, verified in this tree)"
  - "doc/conf.py (strict sphinx settings, i18n, metadata footer)"
  - "doc/scripts/pkb_frontmatter.py, check_pkb_staleness.py, check_translation_sync.py (documented tooling in this tree)"
  - "https://api7.ai/learning-center/openresty/openresty-coding-style-guide (luacheck / lj-releng for Lua)"
  - "https://github.com/openresty/test-nginx (Test::Nginx - data-driven test scaffold for Nginx/OpenResty)"
  - "https://github.com/openresty/mockeagain (mockeagain - LD_PRELOAD slow-network mocking)"
owners:
  created_by: [Walter Fan]
  updated_by: [Walter Fan]
  responsible: [Walter Fan]
ttl: 6 months
review_status: pending
review_score: 0
reviewed_by: null
confidentiality: L1
summary: How this repo is validated - strict bilingual Sphinx builds, frontmatter/staleness/translation checks, Lua style gates, and manual smoke tests. A living regression list for documented claims.
tags:
  domain:
  - openresty
  technology:
  - sphinx
  - lua
  - gettext
  - uv
  concepts:
  - testing-strategy
  - verification
  - regression
  audience: dev
  status: active
---

# 09. Testing Strategy

<!-- maintained-by: human+ai -->

The primary product of this repo is documentation, so "testing" is about
proving the docs (and any Lua they contain) are correct and stay fresh. The
rules below are verified against the Makefile and scripts in this tree.

## Test Layers

| Layer | Primary checks | Notes |
|-------|----------------|-------|
| Docs build (gate) | `make build` (Sphinx `-W -n` for en and zh_CN) | Warnings are errors; a broken page fails the build |
| Metadata contract | `pkb_frontmatter.py validate <page>.md` | Blocking on every page created/changed |
| Staleness | `scripts/check_pkb_staleness.py` | Zero-token freshness report before LLM passes |
| Translation sync | `make pkb-check-i18n` (`check_translation_sync.py`) | Catches zh_CN drift vs English sources |
| Link / diagram | Sphinx nitpicky `-n` + `validate_template_links.py` | Missing targets and broken template links fail |
| Lua style (any Lua in repo) | `luacheck -q lua` and `lj-releng lua/*.lua` | Globals, line length, basic style |
| Runtime behavior (Lua/ngx_lua) | `prove -r t/` with **Test::Nginx** (`.t` files) | Drives a real nginx from `PATH`, rooted at `t/servroot/` (default port 1984) |
| Slow-network robustness | **mockeagain** `MOCKEAGAIN=w`/`r` via `LD_PRELOAD` | Exposes output-filter, parser, and cosocket bugs by mocking one-byte reads/writes |

## Runtime Function Testing (OpenResty Lua)

The official way to test `ngx_lua` handlers, cosockets, and phase behavior is the
[**Test::Nginx**](https://github.com/openresty/test-nginx) scaffold (data-driven
`.t` files built on `Test::Base`). It is the same harness upstream
`lua-nginx-module` tests are written in.

- Write a `.t` file under `t/` with `--- config` (nginx.conf block) and
  `--- request` / `--- response_body` sections.
- Run it with `prove -r t/` (or `prove -v t/foo.t`). `Test::Nginx::Socket`
  starts an nginx instance rooted at `t/servroot/`, listening by default on port
  `1984` (override with the `TEST_NGINX_PORT` environment variable).
- Use the `Test::Nginx::Socket::Lua` subclass for Lua-phase tests; the Stream
  and Dgram subclasses cover stream/TCP-UDP cases.

For slow and hostile networks, preload [**mockeagain**](https://github.com/openresty/mockeagain),
an `LD_PRELOAD` library that mocks the glibc `poll`/`read`/`writev`/`send`/
`recv` syscalls so only one byte is read or written at a time (returning
`EAGAIN`), exposing the same "connection hang" bugs that only showed up on slow
links:

```bash
make                                        # builds mockeagain.so
MOCKEAGAIN=w LD_PRELOAD=/path/to/mockeagain.so /path/to/openresty/nginx/sbin/nginx ...
```

- `MOCKEAGAIN=w` mocks writes, `MOCKEAGAIN=r` mocks reads, `MOCKEAGAIN=wr` both.
- `MOCKEAGAIN_VERBOSE=1` adds diagnostic lines to `error.log`.
- `MOCKEAGAIN_WRITE_TIMEOUT_PATTERN="..."` triggers an indefinite write timeout
  when the pattern appears in the output stream.
- When running under **Test::Nginx**, the required `env` directives
  (`env LD_PRELOAD;`, `env MOCKEAGAIN;`, ...) are configured automatically.

This is exactly the class of regression this PKB cares about for its
[Data and API](05-data-and-api.md) DNS contract and cosocket behavior: a wrong
`err` on a timed-out or half-written I/O only appears under such conditions.

## Core Regression Areas

- **DNS failure contract**: the Lua `err` strings and HTTP status mapping in
  [Data and API](05-data-and-api.md) and [Workflows](06-workflows.md) must stay
  exact against nginx 1.31.1 / ngx_lua 0.10.31rc5. Any wording change in the
  source is a regression to re-verify.
- **Directive reference fidelity**: [08-lua-nginx-module](08-lua-nginx-module.md)
  is a verbatim ingest of the README at commit `9661d95b`; re-verify when the
  upstream README advances (record the new commit in `source`).
- **Bilingual parity**: every English page has a synced `zh_CN` catalog; a page
  added to `index.md` must also be registered in `scripts/gen_index.py` and get
  its `.po` catalog generated.

## Test Data and Environments

- **Fixtures or seeds**: the ingested README snapshot in
  [08-lua-nginx-module](08-lua-nginx-module.md) and the pinned source URLs in
  each page's `source`.
- **State isolation**: Sphinx `_build/` and `_generated/` are gitignored; each
  build is reproducible from sources + `uv.lock`.
- **External dependency strategy**: none at build time (offline-capable); the
  docs site itself is served as static HTML.

## Validation Commands

```bash
make deps       # uv sync --locked
make build      # strict bilingual build (en + zh_CN)
make pkb-check  # rule-based staleness (zero tokens)
make pkb-check-i18n  # zh_CN catalog sync
```

Per-page after an edit:

```bash
python3 scripts/pkb_frontmatter.py validate <page>.md
```

## Manual Smoke Checks

1. `make serve` and open http://127.0.0.1:8000/ - landing page redirects by
   browser language to `/en/` or `/zh/`.
2. Spot-check the [lua-nginx-module page](08-lua-nginx-module.md) for rendered
   directives and anchored links.
3. From [Quick Start](01-quick-start.md): `resty -e 'print("hello, world")'`
   and the `curl` hello-world server check the OpenResty runtime the docs describe.

## Documentation Verification

Because this PKB is published docs, the build gate above is the main
verification. Additionally, before a release: run `make pkb-review-status` to
audit confidentiality/review state and `make pkb-check-i18n` to confirm
translations are in sync.

## Regression Additions

When a claim in the PKB is corrected (for example a DNS error string that did
not match the code), record here:

- the original (wrong) claim and the corrected one
- the source (file or commit) that proves the fix
- the smallest check that catches it next time (usually a grep against the
  expected `err` substring in [Data and API](05-data-and-api.md))

## Related Documentation

- [Workflows](06-workflows.md)
- [Runbook](10-runbook.md)
- [Documentation Process](12-document.md)
