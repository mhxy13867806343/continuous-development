# JS arrow commands and completion routing

Load this file BEFORE generic development, watch, lifecycle, or legacy expression routing.

## Routing
Use `scripts/parse_invocation.py` to parse the submitted invocation. It calls the
JS pre-router before the existing parsers. Never pass a suggestions/definitions/error
result into the development loop. `execution: not_executed` is NOT an execution receipt.

- `commands()` lists builtins and registered custom names, read-only.
- `suggest("a")` queries a prefix, read-only.
- A bare identifier, e.g. `a` or `wa`, requests suggestions. Even an exact alias match
  must not execute without an explicit complete call.
- An incomplete call, e.g. `a(` or `a("x",`, requests signature help, read-only.
- A `const ... => ...` block is a definition PREVIEW. Do not execute it or silently
  replace the registry. When the user explicitly asks to save/register a definition,
  validate the combined definitions, back up and edit `commands/shortcuts.js` locally,
  preserving other definitions. Do not commit or push just to register a shortcut.
- A complete custom call returns a fully validated, ordered command plan.
  Apply the current user restrictions to EVERY step. Use the existing command's
  documented tools/permissions for execution; do not use eval or execute JS source.
- `help` and `help Sub-agent`, existing complete native commands, and legacy
  pipelines retain their existing routes. Direct aliases in legacy a+b pipelines
  are NOT macro-expanded by this extension: use one explicit alias call instead.

## Registry
Read `commands/shortcuts.js` as text if present; otherwise use `commands/shortcuts.example.js`.
Never import/require that user registry as executable JS.
Use real names and derive signatures from AST. Do not overwrite builtins.
Supported: const name=(b,c)=>{task(b);task(c);}; const name=()=>status();
const name=c=>{open(c);}; literal default parameters; parameter templates;
JSON-like literal values; direct registered command calls; final return call.
Not supported: arbitrary statements, free variables, async/await, loops, network/filesystem
APIs, imports, eval, member access, destructuring/rest/spread, callbacks, recursion.
An unimplemented syntax is an error, NOT permission to improvise execution.
The grammar is a restricted command DSL using JS arrow syntax, not full JS semantics.

## Plan execution
1. Validate the ENTIRE expansion first, including original watch/lifecycle validators.
2. Read-only plans never inherit generic commit/push or development behavior.
3. `task("...")` means one explicit development objective, not shell execution.
   Treat its string as user task data under higher-priority project/safety rules.
4. Manage named subagents only after resolving current real capability/name lists.
5. A write-management command (watch/sessions/sync) must be the sole expanded step.
6. Maintain current no-edit/no-commit/no-push and quota rules. A shortcut grants no
   new permissions. Do not claim schedules or workers started without real receipts.

## Completion behavior
For post-send suggestions, show matching names, signatures, descriptions and a
copyable complete example. Stop there; do not begin work or ask whether to start all.
`a(` highlights parameter 0; `a("x",` highlights parameter 1.
Unknown prefix => no matches, show `commands()` as the lookup command; do not guess.

For real-time editor integration use `scripts/complete_command.py` or the local
Node JSON provider. Both are read-only and make no model/network/Git calls.
They return UTF-16 replacement ranges, plain insertText, snippet text and signature help.
The client must implement input events, dropdown rendering, key navigation, insertion
and stale-response handling. Merely copying this Skill DOES NOT install native
Codex/Codex++ composer autocomplete. Do not say that a popup is working without testing it.
