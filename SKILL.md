---
name: continuous-development
description: Continuously develop the current repository by dynamically detecting technologies, architecture, workstreams, validation commands, documentation conventions, Git state, and safe continuation rules. Supports normal, scheduled, status, stop, always-on, and help/h quick reference modes. Supports Sub-agent selection, session lifecycle, handoff, progress, quota-aware sync, and background watch rules.
---

# Continuous Development

This is the main entry skill.

When invoked, load and follow all rule files in this directory before execution:

1. `invocation.md`
2. `repository.md`
3. `orchestration.md`
4. `validation.md`
5. `typesafe.md`
6. `documentation.md`
7. `git.md`
8. `quota-safety.md`
9. `subagents.md`
10. `watch.md`
11. `session-lifecycle.md`
12. `handoff.md`
13. `progress.md`
14. `sync-quota.md`
15. `host-adapters.md`

Treat these files as one combined skill specification.

## Synchronous loading rule

Before starting work:

- read every rule file listed above;
- merge their instructions with this `SKILL.md`;
- repository-specific `AGENTS.md` / project instructions still take precedence where they are more specific;
- do not skip a rule file merely because the task appears simple;
- do not treat the child `.md` files as independent skills;
- this `SKILL.md` is the only entry point.

## watch() management routing (takes precedence)

When the invocation contains watch(), read `watch.md` before any development.
Parse it through `scripts/watch_policy.py` or the integrated parser, then use
`scripts/watch_runtime.py` for the actual requested local action. Never call a
parse-only result a running service. Help/status/doctor do not enable development.
Do not combine watch commands with legacy expressions or other management calls.
When CONTINUOUS_WATCH_WORKER=1, never install another watcher; the supplied
one-round worker instructions override generic endless-loop/Git behavior.

## Command routing takes precedence

<!-- lifecycle-extension-v1: routing -->
For sessions(), handoff(), open(), and sync(), parse lifecycle intent before
any generic development, Git, subagent, or automation side effects. Follow
session-lifecycle.md, handoff.md, progress.md, sync-quota.md, and host-adapters.md.
open() and lifecycle status actions are read-only. handoff() only exports a
private handoff. Lifecycle stop actions disable only their own manager/job.
These management commands return after handling their own operation; they
must not fall through to the generic development loop. A parser error stops
routing. Runtime capability, actual successful actions, and read-back evidence
are required before reporting a manager/job as enabled. A parser result is not
execution. Thread caps, initial drain, quota protection, pending selection,
and explicit user restrictions take precedence over always()/do-not-stop.
<!-- /lifecycle-extension-v1: routing -->

Read all rule files relative to this SKILL.md, then classify the invocation
before starting repository development or causing side effects.

Follow `subagents.md` when a Sub-agent selector is present. It governs
agent selection, parameter validation, and interactive confirmation;
`orchestration.md` governs task scheduling within the resolved selection.

Help and status are read-only. A pending, cancelled, empty, invalid, or
unavailable Sub-agent selection must not fall through to the development
loop, commit/push operations, or automation creation.

Apply the generic Main behavior below only after an execution command
has been recognized, its selection is resolved, and the user's current
constraints permit execution.

Current explicit user restrictions take precedence. Selecting agents does
not grant new permissions or override a no-edit/no-commit/no-push request.

## Main behavior

When `$continuous-development` is invoked:

- immediately inspect the current repository;
- dynamically detect technologies and architecture;
- build the real backlog from repository evidence;
- choose safe parallel workstreams dynamically;
- use subagents when useful;
- implement, validate, document, commit, push, and verify remote sync when allowed;
- continue into the next round while legitimate executable work remains;
- stop only on genuine blockers, actual usage limits, high-risk actions, or truly completed backlog.

Do not hard-code frontend/backend/game/database roles.

Do not assume any particular framework, language, runtime, or project layout.

Do not respond with only a plan when execution is possible.

## Preferred persistent invocation

Use:

`$continuous-development always()`

This means:

- start immediately;
- continue development rounds without voluntarily stopping;
- keep useful subagents working when safe independent tasks remain;
- use an hourly scheduled continuation only as a recovery layer if the current run ends;
- stop only on valid stop conditions.

## Composable and Pythonic Invocations

The skill supports advanced chained modifiers and composable Python expressions:

- **Modifier Overrides (Last-Write-Wins)**: Chained modifiers like `always() run(0.1) run(1) xxx` where later specifications override earlier ones.
- **Python AST Expressions**: Pipeline subscripts `[a,b,c(),d(1)]`, binary operators `a+b+c()+d(1.2)`, dynamic variadics `+*args+**kw`, and functional `lambda(...)` / `lambda(map(...))` forms safely parsed via `scripts/parse_invocation.py` without code evaluation.

