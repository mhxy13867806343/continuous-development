# Invocation and Automation Commands

## Supported commands

### help / h

`$continuous-development help`
`$continuous-development h`
`$continuous-development help()`
`@continuous-development help`
`@continuous-development h`

Behavior:

- output a complete list of all supported commands;
- provide clear descriptions, parameter options, and practical copy-paste examples for each mode;
- do not modify project source code, documentation, Git state, or automations;
- return immediately after displaying the reference information.

### help Sub-agent / h Sub-agent

`$continuous-development help Sub-agent`
`$continuous-development h Sub-agent`
`$continuous-development help() Sub-agent`
`@continuous-development help Sub-agent`
`@continuous-development h Sub-agent`

Behavior:

- output only the Sub-agent selection grammar, parameter options, interactive rules, and concrete examples;
- do not start continuous development, modify source files, or touch automations;
- serve as the primary safe read-only smoke-test command to verify Sub-agent rule integration without executing development work.

### Sub-agent selection

Follow `subagents.md` for the complete selection grammar and safeguards.

Supported forms after the continuous-development skill invocation:

- `Sub-agent` or `Sub-agent()` — select all currently callable agents.
- `Sub-agent(name)` — select one agent by its actual callable name.
- `Sub-agent(a,b,c)` — select multiple agents.
- `Sub-agent([a,b,c])` — equivalent list form.
- `Sub-agent a,b,c` — equivalent comma-separated form.
- `Sub-agent .` or `Sub-agent(.)` — request interactive selection first.

Names in examples are placeholders, not built-in agents.
Use ` -- ` before an additional task objective when this selector is used.

Sub-agent alone starts the current-session continuous workflow without
changing automations. To combine it with an existing execution mode, put
that mode first: `always() Sub-agent(a,b)` or `run(2h) Sub-agent(a,b)`.

Parse and validate the selection before development or automation changes.
Never interpret invalid input, cancellation, or an unanswered picker as all.
Do not claim that Markdown itself installs an input popup or a native command.

### Default

`$continuous-development`

Behavior:

- start continuous development immediately;
- do not create, enable, disable, or modify scheduled automations;
- leave existing automations unchanged.

### always()

`$continuous-development always()`

This is the preferred "do not stop" mode.

Behavior:

- start continuous development immediately;
- enter persistent continuous orchestrator mode;
- do not voluntarily stop after one task, feature, subagent, or development round;
- when one round finishes, immediately begin the next legitimate round;
- keep safe parallel capacity occupied with useful work when independent tasks exist;
- when a subagent finishes and more safe backlog remains, assign follow-up work;
- if one workstream blocks, move available capacity to another safe independent workstream;
- continue until a valid stop condition occurs;
- ensure a repository-specific hourly continuation automation exists as a recovery mechanism;
- reuse an existing matching automation when possible;
- do not create duplicate automations;
- if a matching automation is disabled, enable it;
- if its prompt is outdated, update it safely;
- do not wait for the scheduled automation before beginning work.

The intended behavior:

current run starts now
→ continuous development loop
→ immediate next round
→ immediate next round
→ continue while executable work remains
→ if platform/runtime ends the run
→ hourly automation later resumes saved progress
→ continuous loop begins again.

Important:

- `always()` cannot guarantee that one platform request runs forever;
- it means the agent must not voluntarily stop for convenience;
- platform/runtime limits may still end a run;
- the hourly automation is the recovery layer.

If automation APIs are unavailable:

- report that briefly;
- still enter persistent current-session mode;
- do not treat missing automation support as a blocker.

### run()

`$continuous-development run()`

Behavior:

- start continuous development immediately;
- enable scheduled continuation for the current repository;
- default schedule: every 1 hour;
- reuse an existing matching automation;
- avoid duplicates;
- future runs resume progress.

### run(<interval>)

Supported intervals:

- Decimal/Fractional hours: `0.1` (~6m), `0.5` (~30m), `1.2`, etc.
- Standard hours: `1h`, `2h`, `3h`, `4h`, `6h`, `12h`, `24h` (or bare integers `1`, `2`)

Examples:

- `$continuous-development run(0.1)`
- `$continuous-development run(1h)`
- `$continuous-development run(2h)`
- `$continuous-development run(6h) continue the current priority backlog`

### Multi-call chaining and override rule (Last-Write-Wins)

Commands can chain multiple modifiers in space-separated format:

- `$continuous-development always() run(0.1) xxx`
- `$continuous-development always() run(0.1) run(1)`

Rules:
1. **Later calls override earlier calls**: When multiple `run(...)` intervals are present (e.g. `run(0.1) run(1)`), the rightmost/last specification takes precedence (`1` overwrites `0.1`).
2. **Mixed modifiers**: `always()` sets persistent loop mode; `run(...)` sets the recovery/continuation interval. Chaining `always() run(0.1)` enters persistent mode with a 0.1h backup interval.
3. **Trailing objectives**: Any text after modifiers (or after ` -- `) is captured as the task objective (e.g. `xxx`).

### Pythonic composable expressions

Supports composable Python syntax (AST-parsed with zero-eval safety via `scripts/parse_invocation.py`):

1. **Subscript pipeline**:
   `$continuous-development[a, b, c(), d(1)]`
   Selects agents `a`, `b` and parameterized workstream steps `c()`, `d(1)`.

2. **Binary operator composition (`+`)**:
   `$continuous-development a+b+c()+d(1.2)`
   Composes pipeline stages and concurrent agents using Python `+` expressions.

3. **Dynamic variadics (`*args`, `**kw`)**:
   `$continuous-development a+b+c()+d(1.2)+*args+**kw`
   Permits variable positional arguments and configuration keyword arguments to be forwarded to orchestrators and subagents.

4. **Functional / Lambda deferred execution**:
   - `$continuous-development lambda(run())` — lazy-evaluated scheduled continuation.
   - `$continuous-development lambda(map(run()))` — batch mapped continuation across tasks.
   - `$continuous-development lambda(a+b+c()+d(1.2))` — deferred conditional workflow.

Behavior:

- start development immediately;
- create or update the repository-specific continuation automation;
- use the requested interval;
- avoid duplicates;
- future runs resume existing progress.

If the interval is unsupported, do not guess.

### stop()

`$continuous-development stop()`

Behavior:

- find the scheduled continuous-development automation for the current repository;
- disable it;
- do not delete it unless explicitly requested;
- do not disable unrelated automations;
- do not modify project source code.

### status()

`$continuous-development status()`

Inspect only:

- repository identity
- detected technologies
- detected architecture
- current branch
- git status
- git diff
- upstream synchronization
- progress documentation
- remaining backlog
- validation state when safe
- Typesafe AI availability when relevant
- matching automation state
- automation cadence

Do not modify source, documentation, Git state, or automations.

## Command parsing

For invocations containing Sub-agent, resolve command routing and selection
according to `subagents.md` before applying the default development behavior.

`help Sub-agent`, `h Sub-agent`, and `help() Sub-agent` show selection help.
`status() Sub-agent` inspects available and selected agents without spawning.
`stop() Sub-agent(...)` is unsupported; stop() retains its automation meaning.

For execution modes, use the order:
[always() or run(...), optional] Sub-agent [selection, optional] [ -- objective]

When help/h lists commands, include Sub-agent forms, example names, the
all-versus-concurrency distinction, and the conditional picker behavior.

`$continuous-development help` / `$continuous-development h` / `@continuous-development help` / `@continuous-development h`
- command = help
- behavior = print full command list, descriptions, and examples; no changes made

`$continuous-development always()`
- command = always
- current-session mode = persistent continuous loop
- recovery automation = hourly

`$continuous-development run()`
- command = run
- interval = 1h

`$continuous-development run(2h) fix current API bugs`
- command = run
- interval = 2h
- objective = `fix current API bugs`

`$continuous-development always() run(0.1) run(1) xxx`
- chained modifiers: always() + run(0.1) + run(1)
- override resolution: later run(1) overwrites run(0.1) -> interval = 1h
- mode = always (with 1h recovery interval)
- objective = `xxx`

`$continuous-development[a,b,c(),d(1)]`
- command = subscript pipeline
- agents = `a`, `b`
- tasks = `c()`, `d(1)`

`$continuous-development a+b+c()+d(1.2)+*args+**kw`
- command = binary composition
- agents = `a`, `b`
- parameterized tasks = `c()`, `d(1.2)`
- dynamic variadics = forward `*args`, `**kw` to task orchestrators

`$continuous-development lambda(run())` / `lambda(map(run()))`
- command = deferred functional lambda
- is_lambda = true
- evaluation = deferred lazy schedule / batch mapping

Additional text refines the objective but does not replace the continuous-development rules.

## Automation identity

Use a stable repository-specific name:

`Continuous Development — <repository-name>`

Before creating a scheduled task:

1. inspect existing automations;
2. find one for the current repository;
3. reuse or update it;
4. avoid duplicates.

Scheduled continuation should preserve:

- repository name
- repository path when available
- progress-document location when available
- continuation behavior
- this skill as the governing workflow

## Scheduled continuation behavior

Every scheduled run should:

1. resume the same repository;
2. read project instructions;
3. read progress documentation;
4. inspect Git state;
5. restore unfinished backlog;
6. avoid repeating completed work;
7. identify safe workstreams dynamically;
8. use subagents when beneficial;
9. implement;
10. validate;
11. review;
12. update documentation;
13. commit safe completed work;
14. push when safe;
15. verify remote synchronization;
16. rebuild backlog;
17. continue until a valid stop condition occurs.

A scheduled run must not stop merely because one development round completed.

For `always()` mode, scheduled continuation should re-enter persistent continuous-loop behavior.
