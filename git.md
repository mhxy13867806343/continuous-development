> watch() precedence: see `watch.md`. A managed watch worker performs one bounded
> round in its own worktree, with no nested watcher/subagents or automatic commit/push.
> Its lifecycle, quota and stop policy override the generic continuous-loop defaults
> below. Other invocation modes retain their existing behavior.

# Git Workflow and Remote Verification


<!-- lifecycle-extension-v1: sync -->
Periodic sync may publish only explicitly authorized reviewed checkpoints,
not arbitrary dirty work. Use repository locks, explicit branch destinations,
and independent live verification of every remote. Do not publish other
projects or private conversation handoffs to this public Skill repository.
Failed uploads are retried without force push or empty commits. See sync-quota.md.
<!-- /lifecycle-extension-v1: sync -->

## Review before commit

Before every commit inspect:

- git status
- git diff
- staged diff when necessary

Check for API keys, tokens, passwords, credentials, certificates, .env files, debug output, temporary files, generated junk, unrelated edits, binaries, large accidental files, and pre-existing user changes.

Never commit secrets.

Never silently include unrelated user work.

## Commit behavior

Commit coherent completed work with meaningful messages.

Possible prefixes: feat, fix, refactor, test, docs, chore, perf, build, ci.

Do not create empty commits.

## Push behavior

After safe successful commits inspect current branch, remotes, and upstream.

If upstream exists: `git push`

If no upstream exists and destination is unambiguous: `git push -u origin HEAD`

Never force push automatically.

## Verify remote state

After every push verify synchronization using appropriate commands such as:

- git status
- git branch -vv
- git log -1 --oneline
- git fetch
- git rev-parse HEAD
- git rev-parse @{u}

Only report the latest local commit as uploaded when local and upstream state are verified.

## Preserve user work

Do not overwrite, reset, discard, or silently bundle pre-existing changes.

If safe isolation is impossible, treat it as a blocker.

## Forbidden automatic Git actions

Never automatically execute:

- git push --force
- git push --force-with-lease
- git reset --hard

Never automatically rewrite shared history, delete remote branches, discard unknown work, or remove unrelated files.

Require explicit approval for destructive Git actions.
