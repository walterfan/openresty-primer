---
title: "07. Conventions"
updated_time: 2026-11-05
git_commit: 5f85578
updated_by: ai
source:
  - "https://api7.ai/learning-center/openresty/openresty-coding-style-guide (API7 OpenResty Coding Style Guide, 2022-12-15)"
  - "https://api7.ai/learning-center/openresty/the-core-of-openresty-cosocket (API7: The Core of OpenResty - Cosocket)"
  - "https://openresty.org/en/faq.html (OpenResty FAQ - lua_socket_log_errors, cosocket error logging)"
  - "https://github.com/openresty/lua-nginx-module/blob/master/README.markdown:719-751 @ 9661d95b5cbfaf5c34bf4a627896d16d6c2a34d3 (Lua Coroutine Yielding/Resuming, Lua Variable Scope)"
  - "nginx 1.31.1 / ngx_lua 0.10.31rc5 DNS failure contract verified in this tree (error-handling tables below)"
owners:
  created_by: [Walter Fan]
  updated_by: [Walter Fan]
  responsible: [Walter Fan]
ttl: 6 months
review_status: pending
review_score: 0
reviewed_by: null
confidentiality: L1
summary: Conventions for Lua code running inside OpenResty/ngx_lua - coding style, naming, error handling, cosocket and connection-pool rules, configuration, and anti-patterns.
tags:
  domain:
  - openresty
  technology:
  - ngx_lua
  - lua
  - luajit
  - cosocket
  concepts:
  - coding-style
  - error-handling
  - cosocket
  - best-practices
  audience: dev
  status: active
---

# 07. Conventions

<!-- maintained-by: human+ai -->

Lua code that runs inside OpenResty/ngx_lua follows Nginx-style configuration on
the deployment side and the Lua/OpenResty conventions summarised here on the
code side. The DNS-failure caller rules below are verified against the nginx
1.31.1 / ngx_lua 0.10.31rc5 code in this tree; the style, cosocket, and
config guidance follows the API7 OpenResty coding style guide, the API7
cosocket guide, the OpenResty FAQ, and the `lua-nginx-module` README.

## Style and Tooling

- **Indentation**: 4 spaces. No tabs.
- **Spacing**: one space on both sides of operators (`local i = 1`).
- **No trailing semicolons**; keep statements on their own lines.
- **Blank lines**: separate functions with two blank lines; separate
  `if`/`elseif` branches with one.
- **Line length**: keep lines under ~80 characters; wrap and align continuation
  lines under the opening parenthesis.
- **Detect style automatically**: run `luacheck` and `lj-releng` in CI:
  ```bash
  luacheck -q lua
  ./utils/lj-releng lua/*.lua
  ```
- **Localize everything**: `local ngx = ngx`, `local require = require`, and
  `local timer_at = ngx.timer.at` before use; cache heavily used library
  functions in locals.

## Naming and Layout

- **Variables and functions**: `snake_case`. Constants: `ALL_CAPS`.
- **Modules**: one conceptual module per file; always load with the local form:
  `local foo = require("foo")` (never a bare `require("foo")` - the bare call
  leaks a global that is cleared at the end of the request).
- **Tables**: pre-allocate with `local new_tab = require("table.new"); local t =
  new_tab(100, 0)` for large tables. Never store `nil` in an array; use
  `ngx.null` when a JSON "null" is intended.

## Error Handling

Always branch on the error values that ngx_lua returns, and make your own
functions return `false, "error string"`:

```lua
local ok, err = sock:connect(host, port)
if not ok then
    ngx.log(ngx.ERR, "connect failed: ", err)
    return ngx.exit(ngx.HTTP_BAD_GATEWAY)
end
```

### Classify DNS failures before choosing a status or a retry

| Lua `err` contains | Suggested HTTP status | Retry in this request |
|--------------------|----------------------|------------------------|
| `Operation timed out` | 504 | Yes, bounded |
| `Server failure` | 502 | Yes, bounded |
| `Host not found` | 502 | No. The name is NXDOMAIN for this answer. |
| `Operation refused` | 502 | No |
| `Format error` or `Unimplemented` | 502 | No |
| `no resolver defined` | 500 | No. The worker configuration is wrong. |
| `could not be resolved` with no code | 502 | No, until the cause is known |

`proxy_pass` already returns 502 for both a missing resolver and a timeout. The
500 and 504 rows apply only when Lua chooses the status.

Retry rules for Lua HTTP callers:

- Cap attempts. The ingested note uses three tries with delays `0`, `0.05`, and
  `0.2` seconds.
- Stop on `Host not found`, `Operation refused`, and `no resolver defined`.
- Keep the attempt counter on the current request. Do not store it in a shared
  dict across requests.
- Set a connect timeout on the cosocket so a DNS timeout is not the only
  deadline.
- Connecting by a resolved address requires the original hostname on the `Host`
  header and on TLS SNI. Verifying a certificate against the bare IP will fail.

## Cosockets and Connection Pools

Cosockets are the sanctioned way to talk to backends from Lua; use them instead
of `ngx.location.capture` where a `lua-resty-*` library fits.

- **Create one cosocket per request** (`ngx.socket.tcp()`). A cosocket has
  exactly the lifetime of the handler that created it - never share it across
  requests or pass it into `ngx.timer.*` callbacks.
- **Set timeouts before I/O**, separately for connect, send, and read with
  `settimeout(ms)` or `settimeouts(connect_ms, send_ms, read_ms)`:
  ```lua
  local sock = ngx.socket.tcp()
  sock:settimeouts(1000, 1000, 5000)
  ```
- **Return idle connections to the pool** with `sock:setkeepalive()` instead of
  closing them; the pool is chosen by the destination address and optional
  `pool` name.
- **Default tuning knobs** (nginx.conf): `lua_socket_connect_timeout`,
  `lua_socket_send_timeout`, `lua_socket_read_timeout` (all default 60 s),
  `lua_socket_pool_size` (default 30), and `lua_socket_keepalive_timeout`
  (default 60 s).
- **Full duplex is allowed**: a reader and a writer light thread may operate on
  the same cosocket, but two light threads must not both read (or write, or
  connect) it at once.

## Configuration and Secrets

Recommended `http` settings for the DNS path. Confirm the addresses for each
environment before use.

```nginx
resolver 10.0.0.2 10.0.0.3 valid=30s ipv6=off;
resolver_timeout 5s;
lua_socket_log_errors off;
lua_socket_connect_timeout 5s;
lua_socket_read_timeout 5s;
lua_socket_pool_size 100;
lua_socket_keepalive_timeout 60s;
```

- Declare `resolver`. Without it, hostname connects fail immediately.
- Use at least two nameservers so a missing UDP reply can move on. A SERVFAIL
  answer does not move on.
- `valid=30s` caps how long a successful answer is kept. The code default is the
  record TTL when `valid` is omitted.
- `ipv6=off` skips AAAA when the network has no IPv6 path. The resolver default
  is IPv6 on.
- `resolver_timeout 5s` replaces the 30 second default. The 5 second resend
  interval is compiled in and is a different timer.
- Keep cosocket keepalive shorter than `valid` when backends change address. A
  pooled connection keeps the old address after DNS changes.
- `lua_socket_log_errors off` avoids a second error-log line after Lua has
  already handled the cosocket error (the directive defaults to `on`).
- Never put credentials in Lua source. Keep tokens in environment variables
  listed in the `env` directive, or in a secrets store, and load them at start
  with `init_by_lua*`.

## Testing and Review Expectations

- Require a linter/CI gate: `luacheck -q lua` and `lj-releng lua/*.lua`.
- When changing `ngx_resolver.c` or the cosocket resolve handler, cover: missing
  resolver, NXDOMAIN, timeout, and a CNAME chain that hits
  `NGX_RESOLVER_MAX_RECURSION`.
- Add a paired success and failure test for each new cosocket path (happy path
  plus timeout / `Connection refused` / `Host not found`).

## Anti-Patterns

- Using global variables or a bare `require("x")` at module top level.
- Calling `getaddrinfo`, shelling out to `dig`, or any blocking call
  (`io.*`, `os.execute`, plain LuaSocket) inside a request - it stalls every
  request on that worker.
- Retrying NXDOMAIN, REFUSED, or a missing resolver.
- Unbounded retries against the same nameservers.
- Using an IP URL for HTTPS without the original name as SNI.
- Assuming SERVFAIL tries the next nameserver. In this tree it fails the
  waiters.
- Splicing strings in a hot loop; use `table.concat`.
- Sharing a cosocket (or a light thread) across requests or into a timer
  callback.

## Sources

- [API7: OpenResty Coding Style Guide](https://api7.ai/learning-center/openresty/openresty-coding-style-guide)
- [API7: The Core of OpenResty - Cosocket](https://api7.ai/learning-center/openresty/the-core-of-openresty-cosocket)
- [OpenResty FAQ](https://openresty.org/en/faq.html)
- [lua-nginx-module README](https://github.com/openresty/lua-nginx-module)

## Related Documentation

- [Workflows](06-workflows.md)
- [Data and API](05-data-and-api.md)
- [Runbook](10-runbook.md)
- [Observability](11-observability.md)
