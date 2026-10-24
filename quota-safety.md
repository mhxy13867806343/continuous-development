> watch() precedence: see `watch.md`. A managed watch worker performs one bounded
> round in its own worktree, with no nested watcher/subagents or automatic commit/push.
> Its lifecycle, quota and stop policy override the generic continuous-loop defaults
> below. Other invocation modes retain their existing behavior.

# Usage Limits, Safety, and Stop Conditions

## Usage / quota rules

<!-- lifecycle-extension-v1: quota-priority -->
When sync-quota protection is enabled, authoritative remaining allowance at
or below its configured threshold is a valid protective pause, even before
the platform rejects a request. This overrides the older "only stop on actual
blocking signals" wording below. Unknown/stale quota is not a guessed numeric
value. Save checkpoints during work; a hard limit may prevent a final summary.
See sync-quota.md. Prompt instructions cannot disable account credit billing.
<!-- /lifecycle-extension-v1: quota-priority -->

Continue while Codex still executes normally.

Do not stop merely because remaining quota might be low.

Stop only on actual blocking signals such as:

- usage limit
- quota limit
- unrecoverable rate limit
- current model unavailable
- platform refusing further execution
- additional paid credits explicitly required

Never automatically:

- buy credits
- activate paid credits
- switch to paid third-party APIs
- use another paid provider to bypass limits
- bypass platform usage controls

If possible, update progress state before stopping.

## Production and destructive safety

Require explicit approval before production deployment, publishing releases, destructive migrations, dropping tables/databases, deleting production data, irreversible cloud actions, high-cost external actions, or destructive remote operations.

## Valid stop conditions

Stop only when at least one is true:

1. actual usage/quota limit blocks execution;
2. unrecoverable rate limit blocks execution;
3. platform/model is unavailable;
4. all legitimate executable backlog is complete;
5. a product/business/design decision requires the user;
6. the next action is destructive or high-risk;
7. repository/environment is too broken to proceed safely;
8. required credentials/access are missing and no safe local work remains;
9. continuing explicitly requires additional paid credits.

A completed development round alone is not a valid stop reason.

## always() mode note

In `always()` mode, a valid stop condition ends the current run. If the blocker is temporary, the hourly recovery automation may later resume the workflow.

Do not automatically resume actions that require explicit user approval.
