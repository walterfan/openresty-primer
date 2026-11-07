---
title: 'Appendix-03: Lua and LuaJIT Key Points'
updated_time: 2026-11-06
git_commit: 5f85578
updated_by: ai
source:
  - "https://www.lua.org/manual/5.1/manual.html (Lua 5.1 reference manual)"
  - "https://luajit.org/luajit.html (LuaJIT 2.1 overview and compatibility)"
  - "https://luajit.org/extensions.html (LuaJIT language and library extensions)"
  - "https://luajit.org/ext_ffi.html (LuaJIT FFI)"
  - "https://github.com/openresty/luajit2/blob/v2.1-agentzh/doc/extensions.html (OpenResty LuaJIT extensions and compatibility notes)"
  - "https://www.fanyamin.com/articles/2026-10-22-lua-top-10-mistakes-4e024200/ (Lua: 30 common mistakes, from beginner to advanced; original article updated 2026-10-25)"
  - "../../lazy-rabbit-blog/content/public/articles/blog/journal/tech_20261022_lua-top-10-mistakes.md (local source article)"
  - "doc/03-tech-stack.md (OpenResty runtime version context)"
owners:
  created_by: [Walter Fan]
  updated_by: [Walter Fan]
  responsible: [Walter Fan]
ttl: 6 months
review_status: pending
review_score: 0
reviewed_by: null
confidentiality: L1
summary: A practical tour of Lua 5.1 language fundamentals and LuaJIT features that matter when writing OpenResty applications.
tags:
  domain: [openresty]
  technology: [lua, luajit]
  concepts: [language, runtime, jit, ffi]
  audience: dev
  status: draft
---

# Appendix-03: Lua and LuaJIT Key Points

<!-- maintained-by: human+ai -->

This appendix is a guided review of the Lua language and LuaJIT runtime used
by OpenResty. It focuses on concepts that influence everyday application code,
debugging, and performance. OpenResty uses LuaJIT 2.1 with Lua 5.1 language
semantics; advice for a newer standalone Lua release may not apply directly.

## 1. Lua at a Glance

Lua is a small, embeddable, dynamically typed language. The host application
creates a Lua VM, exposes APIs to it, and decides when Lua code runs. In
OpenResty, `lua-nginx-module` embeds LuaJIT in each Nginx worker and exposes
Nginx request APIs such as `ngx`.

The language is built around a few simple ideas:

- Values have types; variables do not have declared types.
- Tables are the main general-purpose data structure.
- Functions are values and can be stored, passed, and returned.
- Lexical scoping and closures make local state explicit and reusable.
- Coroutines let a program suspend and resume execution cooperatively.
- Metatables let tables and userdata define selected operations.

## 2. Values, Types, and Truthiness

Lua 5.1 has eight basic types: `nil`, `boolean`, `number`, `string`, `function`,
`userdata`, `thread`, and `table`. A variable that has not been assigned has
the value `nil`. Assigning `nil` to a table field removes that field.

Only `false` and `nil` are false in a condition. In particular, `0` and `""`
are true. Code ported from languages where zero or an empty string is false
can therefore behave unexpectedly.

```lua
if value then
    -- Runs for 0 and "", as well as other non-false, non-nil values.
end
```

LuaJIT normally represents Lua numbers as double-precision floating-point
values. This is convenient for ordinary arithmetic, but very large integers
cannot all be represented exactly as Lua numbers. LuaJIT's FFI offers C
integer types when exact-width integer arithmetic or C data layouts are
needed.

Strings are immutable byte sequences. Lua string operations do not assume
UTF-8; applications that need Unicode-aware operations must handle encoding
explicitly. The length operator `#` returns a string's byte length.

## 3. Tables: Arrays, Maps, and Objects

A table is an associative container. It can be used as a sequence, a map, a
record, a module namespace, or the backing data for an object. Keys can be
almost any Lua value except `nil` and NaN. A field whose value is `nil` is
absent.

```lua
local user = {
    name = "Ada",
    roles = { "admin", "reader" },
}

user.active = true
user["display name"] = "Ada Lovelace"
```

The `#t` operator is reliable for a sequence with no holes. When integer keys
have gaps, the table has no unique sequence boundary, so `#t` can return one
of several border positions. Use an explicit count or keep sequences dense
when the length matters.

`pairs(t)` visits key/value pairs; its order is unspecified. `ipairs(t)` walks
integer keys from 1 and stops at the first missing value. Do not depend on
either traversal order for sorting or stable output.

Tables are reference values. Assigning a table to another variable copies the
reference, not the contents. A shallow copy also leaves nested tables shared.

## 4. Expressions and Control Flow

Lua has `if`, `while`, `repeat ... until`, numeric `for`, and generic `for`.
There is no built-in `switch` statement. The common `and` / `or` operators
short-circuit and return one of their operands, not necessarily a boolean.

```lua
local label = name and name ~= "" and name or "anonymous"

for i = 1, 3 do
    -- Numeric loop; the upper bound is included.
end

for key, value in pairs(config) do
    -- Generic loop over a table.
end
```

The expression `a and b or c` is not a full conditional expression: if `b` is
`false` or `nil`, the result is `c`. Use an explicit `if` when that case
matters.

Concatenation uses `..`. Repeatedly concatenating a large number of strings
can create unnecessary intermediate values; collect pieces in a table and
use `table.concat` when assembling larger output.

## 5. Functions, Scope, and Modules

Functions are first-class values. Lua supports multiple return values, and a
function can return another function. A nested function can capture local
variables from its enclosing scope; this is a closure.

```lua
local function make_counter()
    local count = 0
    return function()
        count = count + 1
        return count
    end
end

local next_id = make_counter()
```

Declare locals deliberately. An undeclared assignment creates or changes a
global in the current environment, which is easy to do accidentally with a
misspelled name. Prefer `local` for variables and `local function` for
private helpers.

In Lua 5.1, a module is commonly loaded with `require`. The module file
typically returns a table of functions. `require` caches the returned value
in `package.loaded`, so later calls in the same VM reuse the module. In
OpenResty, that VM is shared by requests handled by one worker: module-level
tables and upvalues persist between requests. Store immutable configuration
or worker-local caches there; do not store request-specific data in shared
module state. ngx_lua isolates Lua global variables by request and clears
them when the request ends, but an accidental global is still a bug-prone
substitute for a correctly scoped local or module field.

## 6. Metatables and Object-Like Patterns

A metatable can customize a limited set of operations. The most common
metamethod is `__index`, which provides fallback lookup; `__newindex` can
intercept writes. Metatables also support operations such as `__tostring` and
arithmetic operator overloading.

Metatables are a mechanism, not a requirement for object-oriented design.
Many Lua modules use plain tables with functions and explicit state because
that is easier to inspect and maintain.

```lua
local methods = {}
methods.__index = methods

function methods:greet()
    return "hello, " .. self.name
end

local function new_person(name)
    return setmetatable({ name = name }, methods)
end
```

The colon syntax is shorthand: `object:greet()` passes `object` as the first
argument, equivalent to `object.greet(object)`.

## 7. Errors, Cleanup, and Coroutines

`error()` raises an error. `pcall()` runs a function in protected mode and
returns a success flag plus its results or error value. Use protected calls
at deliberate boundaries; wrapping every line can hide the original failure
and make error handling harder to follow.

Lua 5.1 has no built-in `try/finally`. When cleanup must happen after a
failure, structure the operation so cleanup is explicit, or use a carefully
scoped protected call and then rethrow the error.

Coroutines are cooperative execution contexts, not operating-system threads.
They yield only when code explicitly yields or when the host integrates a
yielding operation. OpenResty integrates Lua coroutines with Nginx's event
loop: a cosocket operation can suspend the current request coroutine while
the worker handles other events. A blocking library call does not yield to
that event loop and can stall the worker.

Yielding is allowed only in supported ngx_lua phases and call contexts. For
example, module top-level code runs while a file is being loaded, not inside a
request handler; calling a yielding API there is invalid. Check the
[lua-nginx-module phase and context rules](08-lua-nginx-module.md) before
moving an API call into initialization code.

## 8. LuaJIT: Interpreter, JIT, and Extensions

LuaJIT is a Lua 5.1-compatible implementation with a fast interpreter and a
tracing just-in-time compiler. The JIT observes frequently executed paths,
records traces, and compiles eligible traces to machine code. It can improve
CPU-heavy hot paths, but it does not make blocking I/O non-blocking and does
not guarantee every function will be compiled.

Practical implications:

- Keep hot code predictable and measure before optimizing. A simple,
  well-profiled implementation is often the best starting point.
- Avoid assuming that a microbenchmark predicts application throughput;
  allocation, table shape, I/O, and Nginx phase behavior also matter.
- LuaJIT can fall back to interpretation when a path is not suitable for a
  compiled trace. That is normal; use LuaJIT's diagnostic options when
  investigating a measured hot path.
- `jit.*` controls JIT behavior and exposes status and diagnostics. Changing
  JIT settings should be based on evidence and the deployed LuaJIT build.

LuaJIT also includes useful extensions:

- `bit` provides 32-bit bitwise operations in Lua 5.1 syntax.
- `ffi` declares and calls C functions and describes C data structures from
  Lua. It can be fast and expressive, but it crosses the C boundary and
  requires correct declarations, ownership, and lifetime handling.
- `string`, `table`, and other standard libraries are available alongside
  LuaJIT-specific modules such as `jit` and `ffi`.

Use FFI when a stable C API or data layout makes it appropriate. For ordinary
network and database access in OpenResty, prefer the supported Nginx APIs and
`lua-resty-*` libraries, which integrate with the event loop.

## 9. Lua 5.1 Details to Remember in OpenResty

OpenResty code targets LuaJIT's Lua 5.1 behavior. Keep these differences in
mind when reading examples written for newer Lua versions:

- The Lua 5.1 baseline has no `//` integer-division operator or bitwise
  operator syntax. Some recent LuaJIT 2.1 builds add bitwise syntax as an
  extension; check the exact bundled version before relying on it.
- The module system uses `require` and `package.loaded`; newer examples may
  use newer module-loading conventions.
- `unpack` is the usual global function in Lua 5.1. Do not assume newer
  standard-library names are present unless the runtime explicitly provides
  them.
- LuaJIT adds selected extensions, but it is not a drop-in runtime for every
  feature introduced in later PUC-Rio Lua versions.
- OpenResty APIs add their own rules about request phases, yielding, worker
  lifetime, and shared state; Lua language knowledge alone does not define
  those rules.

For OpenResty, the practical model is: Lua code runs in a worker-local VM,
request handlers have coroutine context, and only APIs designed to cooperate
with Nginx can yield safely.

## 10. Thirty Common Mistakes, Adapted for OpenResty

The companion article [Lua Programming: 30 Common Mistakes, from Beginner to
Advanced](https://www.fanyamin.com/articles/2026-10-22-lua-top-10-mistakes-4e024200/)
is organized in three levels and its examples target Lua 5.5. The list below
retains its 30 topics while calling out where LuaJIT 2.1 / Lua 5.1 behavior
differs. Check the runtime version before copying an example: LuaJIT is not
Lua 5.5, and OpenResty adds its own phase and yielding rules.

### Beginner: Core Syntax and Data Model

1. **Index sequences from 1.** Lua's conventional first sequence element is
   `t[1]`; translate zero-based loop bounds carefully.
2. **Remember that `nil` removes a table field.** Use `false` or a dedicated
   sentinel when the distinction between “absent” and “present but empty”
   matters.
3. **Do not use `#t` to count a sparse table.** The length operator is
   well-defined for dense sequences; keep an explicit count if holes are
   possible.
4. **Check division syntax against the runtime.** Lua 5.1 / LuaJIT uses `/`
   and has no `//`; `//` is available in PUC-Lua 5.3 and later.
5. **Know when parentheses collapse multiple returns.** In Lua, a function
   call in a parenthesized expression yields one result; remove the extra
   parentheses when all results are intended.
6. **Concatenate with `..`, not `+`.** For many fragments, collect them and
   call `table.concat` instead of repeatedly copying a growing string.
7. **Compare tables by identity unless you implement content comparison.**
   Two separate tables with equal fields are not equal with `==`.
8. **Declare variables `local` by default.** An undeclared assignment writes
   to the current global environment; typos can create accidental globals.
9. **Understand closure capture and lifetime.** Closures retain captured
   variables, and closures created around shared mutable state can observe
   each other's updates. Capture a per-iteration local when each closure
   needs an independent value.
10. **Match colon definitions and calls.** `obj:method(x)` passes `obj` as
    the first argument; it is shorthand for `obj.method(obj, x)`.

### Intermediate: Libraries and Everyday Behavior

11. **`ipairs` stops at the first missing integer key.** It will not skip a
    hole to find later values; `pairs` sees present keys but has no ordering
    guarantee.
12. **Strings are immutable.** Repeated concatenation can copy increasingly
    large strings; use a fragment table plus `table.concat` for bulk output.
13. **Choose metatable hooks for the behavior you need.** `__index` handles
    missing-key reads; `__newindex` handles writes to missing keys. Existing
    raw fields bypass these hooks, which matters for proxies and validation.
14. **Do not use `a or default` when `false` is a valid value.** Test
    `a == nil` explicitly when “unset” differs from “disabled”.
15. **Distinguish removing a sequence item from clearing a key.**
    `table.remove(t, i)` shifts following items; `t[i] = nil` leaves a hole.
16. **Validate types passed to `string.format`.** `%d` and `%x` expect
    numbers; convert or validate input before formatting.
17. **Add a traceback when protected errors need context.** `pcall` returns
    the error value; `xpcall(fn, debug.traceback)` can attach a stack trace.
18. **Capture varargs before using them in nested functions.** The Lua 5.1
    standard library has no `table.pack` (some LuaJIT builds enable it through
    Lua 5.2 compatibility); use a pack helper that records
    `select('#', ...)` if nil-bearing argument lists must be preserved.
19. **Choose `require` or `dofile` deliberately.** `require` caches modules
    in `package.loaded`; `dofile` executes the file on each call. In OpenResty,
    module state persists for the worker lifetime.
20. **Know whether a copy is shallow or deep.** Copying a table's fields
    copies nested table references unless you recursively copy them.

### Advanced: Runtime, Memory, and Version Boundaries

21. **Track shared upvalues.** Closures returned by one factory can share
    mutable state; call the factory separately when each closure needs its
    own state.
22. **Treat weak tables as GC-assisted references, not deterministic caches.**
    Collection timing is not immediate or predictable; a strongly referenced
    value can also keep related data reachable.
23. **Do not assume table finalizers work in LuaJIT.** PUC-Lua added table
    `__gc` finalizers in 5.2; LuaJIT follows Lua 5.1 semantics, where `__gc`
    is for full userdata. Where supported, the finalizer must be present when
    the metatable is assigned. Prefer explicit cleanup for deterministic
    resource handling.
24. **Read coroutine values in the correct direction.** Arguments to
    `coroutine.resume` enter the coroutine; values from `coroutine.yield`
    return to the resumer, and the next `resume` supplies the values returned
    by `yield`.
25. **Treat `goto` as a runtime extension.** OpenResty LuaJIT supports
    `goto` and labels, although they are not part of PUC-Lua 5.1. Keep
    portability in mind when sharing code with a stock Lua 5.1 interpreter.
26. **Use the bitwise API provided by the runtime.** LuaJIT provides the
    `bit` library (for example, `bit.band`); some recent LuaJIT 2.1 builds
    also backport native bitwise syntax. PUC-Lua adds native bitwise operators
    in 5.3. Check the exact runtime before using syntax extensions.
27. **Give callable tables a `__call` metamethod.** Without it, calling a
    table value raises an error.
28. **Handle both results from dynamic compilation.** `load` may return
    `nil` and an error message; check compilation before calling the result.
    Lua 5.1 code may use `loadstring`, which is not the same API as newer
    PUC-Lua's `load`.
29. **Use `%q` only when producing a quoted Lua literal.** It escapes a
    string for source representation; use `%s` for ordinary human-facing text.
30. **Profile before applying micro-optimizations.** Localizing hot globals
    may help interpreter-heavy code, but LuaJIT's optimizer and workload
    affect the result. Benchmark the deployed runtime; never assume `#t` on a
    sparse sequence gives a count or a stable cost.

For an OpenResty review, pair this language checklist with checks for
request-specific versus worker-level state, legal yielding phases, and
cosocket-based I/O. These runtime rules are covered in
[Conventions](07-conventions.md) and the [lua-nginx-module reference](08-lua-nginx-module.md).

## Further Reading

- [Lua 5.1 Reference Manual](https://www.lua.org/manual/5.1/manual.html)
- [LuaJIT overview](https://luajit.org/luajit.html)
- [LuaJIT extensions](https://luajit.org/extensions.html)
- [LuaJIT FFI library](https://luajit.org/ext_ffi.html)
- [Lua Programming: 30 Common Mistakes, from Beginner to Advanced](https://www.fanyamin.com/articles/2026-10-22-lua-top-10-mistakes-4e024200/)
- [OpenResty LuaJIT extensions and compatibility notes](https://github.com/openresty/luajit2/blob/v2.1-agentzh/doc/extensions.html)
- Local source: `../../lazy-rabbit-blog/content/public/articles/blog/journal/tech_20261022_lua-top-10-mistakes.md` (version 1.1, updated 2026-10-25)
- [OpenResty Tech Stack](03-tech-stack.md)
- [Lua Nginx Module](08-lua-nginx-module.md)
