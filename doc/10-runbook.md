---
title: "10. Runbook"
updated_time: 2026-11-06
git_commit: 5f85578
updated_by: ai
source:
  - "doc/01-quick-start.md, doc/Makefile, doc/07-conventions.md (this PKB, verified in this tree)"
  - "nginx 1.31.1 / ngx_lua 0.10.31rc5 DNS failure behavior verified in this tree"
owners:
  created_by: [Walter Fan]
  updated_by: [Walter Fan]
  responsible: [Walter Fan]
ttl: 6 months
review_status: pending
review_score: 0
reviewed_by: null
confidentiality: L1
summary: Operating and debugging OpenResty - run the docs site or a live server, configure the resolver and cosockets, troubleshoot Lua/cosocket/DNS issues, and verify behavior.
tags:
  domain:
  - openresty
  technology:
  - nginx
  - ngx_lua
  - lua
  - cosocket
  concepts:
  - runbook
  - troubleshooting
  - operations
  audience: ops
  status: active
---

# 10. Runbook

<!-- maintained-by: human+ai -->

Common operational and debugging steps for OpenResty/ngx_lua. The DNS-specific
troubleshooting below is verified against nginx 1.31.1 / ngx_lua 0.10.31rc5 in
this tree; the build/run steps cover this repository's documentation site.

## Prerequisites

| Tool | Minimum version | Check command |
|------|-----------------|---------------|
| OpenResty | Latest stable (e.g. 1.31.x) | `openresty -v` |
| resty (resty-cli) | shipped with OpenResty | `resty -e 'print(1)'` |
| dig | any recent (>= 9.11) | `dig -v` |
| curl | any recent (>= 7.x) | `curl --version` |

## Setup

For this repository the "build to run" is the docs site: `make deps` then
`make serve`. For a live OpenResty server to diagnose against, follow
[Quick Start](01-quick-start.md): install OpenResty and start the hello-world
`nginx.conf` with `nginx -p \`pwd\`/ -c conf/nginx.conf`.

Confirm the running config contains a `resolver` directive in the `http` or
location block that performs the connect:

```nginx
resolver 10.0.0.2 10.0.0.3 valid=30s ipv6=off;
resolver_timeout 5s;
```

Replace the example addresses with the environment's recursive resolvers.

## Run the Project

- Docs site: `make serve` (or `make serve-en`).
- OpenResty server (per [Quick Start](01-quick-start.md)): `nginx -p \`pwd\`/ -c
  conf/nginx.conf` starting from the scratch directory.
- One-off Lua: `resty -e 'print("hello, world")'`.

## Build and Package

- Docs site: `make build` (bilingual strict build), publish with `make publish`.
- OpenResty from source: `./configure --prefix=/usr/local/openresty && make &&
  make install` (see [Quick Start](01-quick-start.md)).

## Inspect Local State

| State | Location | How to inspect |
|-------|----------|----------------|
| Error log | `error_log` path from `nginx.conf` | Search for Lua errors (`lua_`, `nginx: [error]`) and DNS signs (`could not be resolved`, `no resolver defined`) |
| Running config | `nginx -T` | Dump the effective config; confirm `resolver`, `lua_code_cache`, pool settings |
| Nameserver reachability | The `resolver` addresses | `dig @<ns-ip> <name> A` and a UDP/53 check from the worker host |
| Cached answer lifetime | `resolver ... valid=` | Compare with keepalive timeout if clients keep reaching an old address |
| Cosocket pool | `lua_socket_pool_size` / `keepalive_timeout` | Pool is per worker and reset on reload; watch the error log for pool/connect errors, or export Nginx status/stub_status metrics |
| Lua code cache | `lua_code_cache` | `off` only during development; production must be `on` |

## Lua and Cosocket Troubleshooting

- **A Lua error with `bad argument`/`attempt to call` typically points to a
  misspelled global or a misused API** - run `luacheck` on the .lua files and
  confirm `local foo = require("foo")` is used.
- **`attempt to yield across C-call boundary`** - a yielding API
  (`ngx.location.capture`, `ngx.exit`, a cosocket call) was invoked at module
  top level or in a phase that cannot yield. Move it into a handler function
  and respect the [phase rules](08-lua-nginx-module.md).
- **`socket busy reading` / `socket busy writing`** - two light threads are
  using the same cosocket in the same direction at once.
- **`no resolver defined` on cosocket connect** - see the DNS section below.
- **A blocking call stalls all requests on a worker** - `os.execute`, `io.*`,
  or plain LuaSocket inside a request blocks the event loop; replace with
  cosocket-based APIs or `ngx.timer`.

## Common Issues (DNS)

```{mermaid}
flowchart TD
    fail["HTTP request failed"] --> nores{"err has no resolver defined?"}
    nores -->|yes| add["Add a resolver directive and reload"]
    nores -->|no| resolved{"err has could not be resolved?"}
    resolved -->|Host not found| nx["Check the name, then dig at the configured NS"]
    resolved -->|Operation timed out| to["Check NS reachability, UDP 53, and resolver_timeout"]
    resolved -->|Server failure| sf["Check that nameserver and its upstream"]
    resolved -->|Operation refused| ref["Check the nameserver ACL"]
    resolved -->|no| other{"IP works and the name does not?"}
    other -->|yes| dnsnet["TCP path is fine; DNS path is not"]
    other -->|no| stale{"DNS changed but the old address is still used?"}
    stale -->|yes| ttl["Shorten valid= and keepalive"]
```

| Symptom | Cause | Fix |
|---------|-------|-----|
| `no resolver defined to resolve` | No `resolver` in the connecting location | Add `resolver` and reload. Cosocket will not fall back to `resolv.conf`. |
| `could not be resolved (3: Host not found)` | NXDOMAIN, or an empty NOERROR treated as NXDOMAIN | Check spelling and that this nameserver is authoritative for the zone, including internal zones. |
| `could not be resolved (<errno>: Operation timed out)` | No reply before `resolver_timeout` | Check nameserver IP, container DNS (Docker `127.0.0.11`, cluster DNS), and UDP 53. A 5 second timeout is only too short if the recursive server is slower than that. |
| `could not be resolved (2: Server failure)` | Nameserver returned SERVFAIL | The next configured nameserver is not tried for this answer. Check that server and DNSSEC failures on it. |
| `could not be resolved (5: Operation refused)` | Nameserver refused the query | Allow the worker source address on the nameserver ACL. |
| IP connect works, name connect fails | DNS path, not the backend TCP path | Use the decision tree above. |
| Name now points at a new address, client still uses the old one | Success cache and keepalive | Lower `valid=` and the keepalive timeout together. |

## Related Documentation

- [Workflows](06-workflows.md)
- [Conventions](07-conventions.md)
- [Observability](11-observability.md)
- [Data and API](05-data-and-api.md)
