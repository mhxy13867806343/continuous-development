# Invocation and Automation Commands

## Supported commands

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

- `1h`
- `2h`
- `3h`
- `4h`
- `6h`
- `12h`
- `24h`

Examples:

- `$continuous-development run(1h)`
- `$continuous-development run(2h)`
- `$continuous-development run(6h) continue the current priority backlog`

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
