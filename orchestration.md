# Continuous Orchestration and Subagents

## Selected-agent boundary

When a Sub-agent selector is present, follow `subagents.md` and resolve
selection before task dispatch. Waiting for the user's explicit selection
is a valid pause even in always() mode.

Use only the resolved callable agent names. Do not add unselected agents,
substitute a generic agent for an invalid name, or bypass the selection
through nested delegation. The main agent remains the coordinator.

All selected agents must have an accounted-for state. Selection is not
concurrency: queue suitable tasks when the safe/runtime concurrency cap
is lower than the number of selected agents. Do not truncate the selection
or invent tasks to force every selected agent to run.

The existing dynamic-workstream and validation rules continue to apply.
Only the main agent integrates Git changes; preserve current user restrictions.

## Dynamic workstreams

Do not use fixed roles.

Before parallelizing inspect task dependencies, file/module overlap, shared mutable state, central configs, lock files, schemas, migrations, generated files, build outputs, and resource files.

Create workstreams from the actual repository and backlog.

## Dynamic subagent count

Choose concurrency based on safe parallelism:

- 1 agent for tightly coupled work
- 2 for two independent tasks
- 3 for three independent workstreams
- 4 only when four or more low-conflict workstreams exist

Do not create extra agents merely to maximize concurrency.

## Subagent task definition

Each subagent receives:

- exact objective
- scope
- relevant files/modules
- files/modules to avoid
- dependency assumptions
- validation expectations
- completion criteria

Each subagent reports:

- completed work
- changed files
- validation performed
- unresolved issues
- blockers
- next step if relevant

## Persistent continuous loop

Repeat:

1. inspect repository
2. inspect Git state
3. inspect project instructions
4. inspect progress docs
5. inspect backlog
6. inspect current failures
7. discover validation commands
8. identify safe workstreams
9. choose subagent count
10. spawn subagents
11. perform useful root-agent work
12. collect results
13. review changes
14. resolve conflicts
15. run validation
16. fix obvious regressions
17. update backlog
18. update documentation
19. review Git diff
20. commit safe completed work
21. push current branch when safe
22. verify remote synchronization
23. re-evaluate repository
24. immediately begin the next round

After step 24, return to step 1 without waiting for user confirmation.

## always() reinforcement

When `always()` is active:

- do not voluntarily end the current run while legitimate safe work remains;
- do not pause merely to summarize progress;
- do not ask whether to continue;
- do not wait for the scheduled automation if the current run can continue;
- when a subagent finishes, assign follow-up work if suitable backlog remains;
- if one workstream blocks, move capacity to another safe workstream;
- use the scheduled automation only as recovery if the current run ends.

## Do not stop for convenience

Invalid stop reasons include one task/feature/subagent/round finishing, progress being summarized, a convenient checkpoint, wanting to ask whether to continue, or a temporary backlog becoming empty.

If safe executable work remains, continue.

## Backlog renewal

If backlog appears empty, re-inspect TODO/FIXME, tests, compiler output, type checker, lint, runtime errors, progress docs, roadmap, unfinished integrations, incomplete documented features, regressions, and validation gaps.

Do not invent random product features.

If no legitimate executable work remains, stopping is allowed.
