# OpenResty Primer

Reading notes and a living knowledge base for OpenResty (nginx plus Lua). The
focus is on how hostname lookups and DNS resolution failures surface through
`ngx_lua` HTTP cosockets and `proxy_pass` upstreams, mapping behavior back to
the nginx and ngx_lua sources.

## Documentation

The Sphinx/MyST knowledge base lives in [`doc/`](doc/), keyed to the OpenResty
source layout:

| Page | Topic |
|------|-------|
| [Overview](doc/00-overview.md) | Purpose, scope, and quality targets |
| [Quick Start](doc/01-quick-start.md) | First-run guide |
| [Architecture](doc/02-architecture.md) | Resolver and cosocket architecture |
| [Tech Stack](doc/03-tech-stack.md) | nginx, ngx_lua, Lua packages |
| [Repository Map](doc/04-repo-map.md) | Source tree map for the DNS path |
| [Data and API](doc/05-data-and-api.md) | Error values and HTTP statuses |
| [Workflows](doc/06-workflows.md) | Resolve success/failure flows |
| [Conventions](doc/07-conventions.md) | Retry and error-handling rules |
| [Testing](doc/09-testing.md) | Test layers and validation |
| [Runbook](doc/10-runbook.md) | Debugging resolver issues |
| [Observability](doc/11-observability.md) | Log lines and monitoring |
| [Documentation](doc/12-document.md) | How this knowledge base is maintained |

## Build the docs

```bash
cd doc
uv sync --locked     # install dependencies
make html            # strict English HTML build
make serve           # preview at http://127.0.0.1:8000/
make html-all        # bilingual (en + zh_CN) build
```

Output is written to `doc/_build/site/`. `make html-loose` skips the
warnings-as-errors flag if you only want a quick render.

## Repository layout

```text
doc/       Sphinx project knowledge base
```

## Installation

```
brew tap openresty/brew
brew install openresty
```

## Reference

https://github.com/openresty/lua-nginx-module

## License

Apache License 2.0. See [LICENSE](LICENSE).
