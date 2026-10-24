# Documentation and Progress Tracking


<!-- lifecycle-extension-v1: progress -->
Store private thread handoffs separately from public progress. open() reports
only a known task-snapshot denominator; unknown evidence stays unknown. Record
actual archive/create/sync receipts, not plans as successful actions. Keep
post-push receipts in local state to avoid endless commits recording their own
commit SHA. See handoff.md and progress.md.
<!-- /lifecycle-extension-v1: progress -->

## Discover existing conventions

Look for README.md, TODO.md, ROADMAP.md, CHANGELOG.md, PROGRESS.md, docs/, ADRs, design docs, architecture docs, and development logs.

Use the most suitable existing convention.

Do not create duplicate progress systems.

If no suitable progress tracking exists and long-running development needs one, create `PROGRESS.md`.

## Update after meaningful rounds

Record as appropriate:

- completed work
- changed modules
- fixed issues
- validation state
- unresolved issues
- remaining backlog
- next priority
- exact continuation point
- current branch
- latest commit
- push status
- remote synchronization status

Documentation must reflect actual repository state.

## Before stopping

When possible, persist completed work, changed files/modules, validation state, unresolved issues, remaining backlog, exact continuation point, current branch, latest commit, push/remote state, and blocking reason.

The next invocation should resume rather than restart completed work.
