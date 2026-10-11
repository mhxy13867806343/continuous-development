---
name: continuous-development
description: Continuously develop the current repository by dynamically detecting technologies, architecture, workstreams, validation commands, documentation conventions, Git state, and safe continuation rules. Supports normal, scheduled, status, stop, always-on, and help/h quick reference modes.
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

Treat these files as one combined skill specification.

## Synchronous loading rule

Before starting work:

- read every rule file listed above;
- merge their instructions with this `SKILL.md`;
- repository-specific `AGENTS.md` / project instructions still take precedence where they are more specific;
- do not skip a rule file merely because the task appears simple;
- do not treat the child `.md` files as independent skills;
- this `SKILL.md` is the only entry point.

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
