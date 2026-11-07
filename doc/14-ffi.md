---
title: "14. OpenResty FFI (Foreign Function Interface)"
updated_time: 2026-11-06
git_commit: 5f85578
updated_by: ai
source:
  - "https://luajit.org/ext_ffi.html (LuaJIT FFI library)"
  - "https://github.com/openresty/lua-resty-core (lua-resty-core - FFI-rewritten core Nginx APIs)"
  - "https://github.com/urbanairship/lua-resty-ffi (lua-resty-ffi - multi-language FFI bridge)"
  - "doc/appendix-03-lua.md (Lua/LuaJIT fundamentals, this PKB)"
owners:
  created_by: [Walter Fan]
  updated_by: [Walter Fan]
  responsible: [Walter Fan]
ttl: 6 months
review_status: pending
review_score: 0
reviewed_by: null
confidentiality: L1
summary: How FFI works in OpenResty - LuaJIT FFI fundamentals, the lua-resty-core ecosystem, basic usage, best practices, and the cross-language lua-resty-ffi bridge.
tags:
  domain: [openresty]
  technology: [lua, luajit, ffi, lua-resty-core]
  concepts: [ffi, performance, jit, c]
  audience: dev
  status: active
---

# 14. OpenResty FFI (Foreign Function Interface)

<!-- maintained-by: human+ai -->

In OpenResty, FFI (Foreign Function Interface) primarily means **LuaJIT FFI**:
it lets Lua code call external C functions and manipulate C data structures
directly. Because the classic Nginx Lua API is implemented on top of the
standard Lua C API (which stops the just-in-time compiler from optimizing the
calls), OpenResty relies heavily on FFI-based rewrites to get maximum
performance and avoid JIT-compilation barriers. See
[appendix-03-lua](appendix-03-lua.md) for the Lua/LuaJIT fundamentals this
page builds on.

## 1. lua-resty-core (Built-in FFI Ecosystem)

OpenResty bundles [lua-resty-core](https://github.com/openresty/lua-resty-core)
by default. This library re-implements many core Nginx Lua APIs (such as URI
parsing, regex, base64 encoding, and shared dictionaries) using LuaJIT FFI.

The benefit: your code can run fully inside LuaJIT's compiled machine code
without falling back to the slower interpreted mode, because the rewritten
APIs are just FFI calls that the JIT can compile, instead of C-function
callbacks that force an interpreter round-trip.

## 2. Basic Usage Example

Use the native `ffi` module to load standard C libraries or custom shared
libraries (`.so`) into your Nginx workers:

```lua
local ffi = require("ffi")

-- 1. Define the C function prototypes
ffi.cdef[[
    int printf(const char *fmt, ...);
    double pow(double x, double y);
]]

-- 2. Call the functions directly via the 'ffi.C' namespace
ffi.C.printf("Hello from FFI!\n")
local result = ffi.C.pow(2.0, 3.0)  -- returns 8.0
```

## 3. FFI Best Practices in OpenResty

When writing high-concurrency code inside Nginx, FFI needs special care:

- **Avoid blocking calls.** Standard C functions are synchronous. Calling a C
  function that blocks (for example heavy disk I/O or a synchronous network
  call) freezes the entire Nginx worker thread and destroys OpenResty's
  asynchronous advantage.
- **Keep `ffi.cdef` at the module (global) level.** Never run `ffi.cdef` inside
  a request handler such as `content_by_lua_block`; it is a heavyweight
  initialization operation. Define it at the top of your Lua module so it runs
  once during the Nginx configuration/loading phase, not per request.
- **Manage C memory deliberately.** Be careful with `ffi.new()` allocations.
  For large structs allocated frequently, rely on LuaJIT's garbage collector,
  or manage them manually with `ffi.gc()` or an explicit C `free` function, to
  avoid memory leaks.

## 4. Advanced: Multi-Language FFI (lua-resty-ffi)

To move beyond C, the third-party
[lua-resty-ffi](https://github.com/urbanairship/lua-resty-ffi) provides a
generic, non-blocking API for hybrid programming. It uses Nginx thread pools to
safely offload heavy work to mainstream languages without blocking the primary
event loop:

| Supported language | Typical use case via lua-resty-ffi |
|--------------------|-------------------------------------|
| Go / Rust | Offloading CPU-bound tasks, heavy cryptography, or using complex gRPC/Kafka clients |
| Python / Java | Integrating machine learning models or legacy enterprise SDKs directly into Nginx gateways |

## References

- [LuaJIT FFI library](https://luajit.org/ext_ffi.html)
- [lua-resty-core](https://github.com/openresty/lua-resty-core)
- [lua-resty-ffi](https://github.com/urbanairship/lua-resty-ffi)
- [Lua and LuaJIT Key Points](appendix-03-lua.md)
