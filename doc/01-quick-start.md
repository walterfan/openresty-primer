---
title: "01. Quick Start"
updated_time: 2026-11-05
git_commit: 5f85578
updated_by: ai
source:
  - "https://openresty.org/en/getting-started.html (OpenResty Getting Started guide, updated 2026-08-12, fetched 2026-11-05)"
  - "https://openresty.org/en/installation.html (OpenResty Installation guide)"
  - "https://github.com/openresty/resty-cli (resty CLI)"
owners:
  created_by: [Walter Fan]
  updated_by: [Walter Fan]
  responsible: [Walter Fan]
ttl: 6 months
review_status: pending
review_score: 0
reviewed_by: null
confidentiality: L1
summary: First-run guide for OpenResty - install it, print "hello, world" with the resty CLI, then run a minimal HTTP server that speaks hello world via content_by_lua_block.
tags:
  domain:
  - openresty
  technology:
  - nginx
  - ngx_lua
  - luajit
  - resty-cli
  concepts:
  - quick-start
  - hello-world
  - content-phase
  audience: onboarding
  status: active
---

# 01. Quick Start

<!-- maintained-by: human+ai -->

This page gets you to a first successful OpenResty run quickly, following the
official [OpenResty Getting Started guide](https://openresty.org/en/getting-started.html).

## Prerequisites

| Tool | Minimum version | Check command | Install notes |
|------|-----------------|---------------|---------------|
| OpenResty | Latest stable (e.g. 1.31.x) | `openresty -v` (or `nginx -v`) | Official pre-built packages, Homebrew, or build from source |
| curl | any | `curl --version` | macOS ships it; Linux install via package manager |
| `resty` CLI | Shipped with OpenResty | `resty -e 'print(1)'` | In `PATH` by default with official packages; otherwise add `/usr/local/openresty/bin` to `PATH` |
| pcre/zlib/openssl dev headers | as required | - | Only when building from source |

## Install OpenResty

On Linux, use the official [pre-built packages](https://openresty.org/en/linux-packages.html)
when your distribution is supported. With the official package, the binary is
`openresty`; replace every `nginx` command on this page with `openresty`.

On macOS, the quickest path is Homebrew:

```bash
brew install openresty/brew/openresty
```

Otherwise, download the [source tarball](https://openresty.org/en/download.html)
and follow the [Installation guide](https://openresty.org/en/installation.html).

If `resty` is not on your `PATH`, export it (default prefix assumed):

```bash
export PATH=/usr/local/openresty/bin:$PATH
```

Verify the installation with the simplest program possible:

```bash
resty -e 'print("hello, world")'
# -> hello, world
```

## Run a "hello, world" HTTP Server

OpenResty is just an enhanced Nginx, so a working server is a working
`nginx.conf`. Create a scratch directory and the config:

```bash
mkdir -p ~/work/{logs,conf}
```

Add `~/work/conf/nginx.conf`:

```
worker_processes  1;
error_log logs/error.log;

events {
    worker_connections 1024;
}

http {
    server {
        listen 8080;
        location / {
            default_type text/html;
            content_by_lua_block {
                ngx.say("<p>hello, world</p>")
            }
        }
    }
}
```

Start the server from the scratch directory (prefix points Nginx at `~/work`,
relative paths like `logs/` and `conf/` resolve against it):

```bash
cd ~/work
PATH=/usr/local/openresty/nginx/sbin:$PATH
export PATH
nginx -p `pwd`/ -c conf/nginx.conf
```

What "working" looks like:

1. `nginx -p ... -c ...` exits without an error and the process stays up.
2. The service answers (in a browser or with curl):
   ```bash
   curl http://localhost:8080/
   # -> <p>hello, world</p>
   ```
3. Errors, if any, appear on stderr or in `logs/error.log` under `~/work`.

## Run Tests / Validate

Basic smoke checks for a fresh install:

```bash
openresty -v            # or nginx -v; print the version
resty -e 'print("ok")'  # resty CLI works
curl -s http://localhost:8080/ | grep "hello, world"
```

## Build for Production

The scratch server above is for exploration only. For a production build, build
OpenResty from source (or use the official packages) per the
[Installation guide](https://openresty.org/en/installation.html): unpack the
tarball, `./configure --prefix=/usr/local/openresty`, `make`, `make install`.
Expected install prefix: `/usr/local/openresty/` by default.

## Common Issues

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `resty: command not found` | `/usr/local/openresty/bin` not on `PATH` | `export PATH=/usr/local/openresty/bin:$PATH` |
| `nginx: command not found` | Nginx `sbin` not on `PATH` | `export PATH=/usr/local/openresty/nginx/sbin:$PATH` |
| `bind() to 0.0.0.0:8080 failed (98: Address already in use)` | Port 8080 busy | Pick another `listen` port or free 8080 |
| `could not open error log file` | Started from the wrong cwd | Run `nginx` with `-p` pointing at the scratch dir |
| `curl` gets a persistent 502/empty body | Server started before config was valid | Check `logs/error.log`; run `nginx -t -p pwd/ -c conf/nginx.conf` |

## Next Steps

- [Architecture](02-architecture.md)
- [Tech Stack](03-tech-stack.md)
- [lua-nginx-module Directive Reference](08-lua-nginx-module.md)
- [Runbook](10-runbook.md)
