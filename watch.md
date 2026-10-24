# watch(): actual local recovery runner

This module governs `watch` commands before the generic development loop. It is
not an instruction to pretend an Automation or GUI restart exists.

## Methods

- `@continuous-development watch()` — enable a background development job.
- `@continuous-development watch(every="60s", retry=3, threshold=1)` — explicit defaults.
- `@continuous-development watch(every="30s", retry=5, threshold=2) -- fix existing test failures`
- `@continuous-development watch("doctor")` — check Git, CLI, ChatGPT auth and readable allowance; no model turn.
- `@continuous-development watch("status")` — read the registered job and service state.
- `@continuous-development watch("stop")` — latch disabled, request graceful interruption, unregister when stopped.
- `@continuous-development watch("resume")` — explicit manual continuation of a stopped/blocked job after review.
- `@continuous-development help watch` — explain only.

`$continuous-development` prefixes are equivalent where that interface recognizes `$`.
Use one watch management method per message. Do not chain it with always(),
run(), sessions(), sync(), Sub-agent, `+` expressions, or lambda expressions.
An invalid watch call must never fall through to ordinary development.

## Intent versus execution

`scripts/parse_invocation.py` only parses; `execution: not_executed` is not an activation receipt.
For a management request, invoke the real script using the current, resolved
project path and the actual skill directory:

```bash
python3 "<actual-skill-directory>/scripts/watch_runtime.py" \
  --project "<actual-project-directory>" \
  --invocation '@continuous-development watch()' --apply
```

For a user-specified objective or parameters pass their validated invocation
verbatim as one argv value; do not evaluate it as Python/shell. Use the runtime's
argument-array command tool, or correct shell quoting. Do not interpolate a user
argument into a shell command unsafely.

For start, stop and resume, add `--apply` only when the user's command explicitly
requested that action. For help, status or doctor, omit `--apply`.

After an action, read back with `watch("status")`. Report separate facts:
- service registered;
- worker lock held / not held;
- actual phase, reason, latest quota observation;
- worker-owned thread id and worktree path (when present).

Do not say "running" solely because the plist/config was written. Do not bypass
permissions or weaken Codex's sandbox to install the service.

## Scope of this first executable adapter

Implementation: macOS user LaunchAgent + local `codex app-server` stdio.
Requirements: Python >=3.9, Git, local `codex` in PATH, a ChatGPT-backed Codex login,
and a clean committed Git repository. Existing source changes are NOT automatically
committed, stashed, reset, uploaded or discarded. Ask the main workflow to finish
its safe checkpoint first if the source is dirty.

The runner creates a dedicated `cd-watch/...` branch and Git worktree under a
private local state directory. It creates/resumes ONLY its own Codex thread.
It does NOT click the current GUI's Continue button, import all GUI chats,
archive chats, enforce the earlier 15-GUI-chat policy, or restart a dev server.
The current GUI thread must not be falsely reported as monitored. There are no
Claude Code / Antigravity / Kiro executors in this version.

Watch rounds are sequential; no detached child agents or background commands.
The normal Sub-agent workflow remains available outside watch mode. No automatic
Git commit/push/merge/deployment in watch v1; completed edits remain in the watch
worktree for review. This is separate from the existing sync() specification.

## Recovery policy

- One job per Git common directory; a process lock prevents duplicate workers.
- Before a model turn, read current ChatGPT allowance. Unknown allowance waits.
- Threshold is REMAINING allowance, not context percentage or used percentage.
- `remaining <= threshold` pauses; resume requires fresh allowance above threshold+1.
- Active turns are observed, not restarted on every timer tick.
- A terminal, explicitly retryable network/service failure retries up to `retry`
  times with exponential backoff (at least 60 seconds). Successful rounds reset it.
- A report requesting a legitimate next task starts the next round after `every`.
- A task marked done, user interruption, pending approval or invalid report pauses/stops.
- A disconnected server after turn/start has an uncertain outcome: pause as
  `ambiguous`, never blindly duplicate work. `watch("resume")` is a user decision
  after checking for orphaned work; never invoke it automatically.
- Three continuing rounds with no repository changes pause for review.
- No silence-based kill: a long reasoning/test step is not proof of a dead worker.
- LaunchAgent may relaunch a crashed monitor; the persisted policy is checked again.
  Neither process resurrection nor a stored thread id bypasses pause conditions.
- User stop is durable. Login/reboot cannot override it. Sleep/offline is not
  a promise of continuous execution. OS shutdown during a turn can require review.

The monitoring interval is a local control cadence, not a new full development
request each tick. `every="1s"` is accepted, but an active turn remains single;
quota polling during active work is no more frequent than once per 60 seconds.
Checks between rounds are fresh. Do not represent this as a free or unlimited
model loop. The account's billing settings still govern credits.

## Private state and failure receipts

Default state: `$CODEX_HOME/continuous-development/watch/<repository-hash>/`,
falling back to `~/.codex/continuous-development/watch/...`.
Config/state/reports use private permissions and are outside the source Git repo.
No API keys or tokens are embedded in the package. No API-key fallback.
`watch("doctor")` does not start a model turn, but it contacts the configured
local Codex service to inspect auth and allowance.

Failure must name what is missing: CLI, login, capability, clean Git checkpoint,
LaunchAgent registration, service permissions, or quota evidence. Never claim
installation or actual model execution merely because the command was recognized.
