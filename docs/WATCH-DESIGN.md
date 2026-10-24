# watch(): implementation scope and plan

## User outcome
Enable automatic continuation through a short Skill method; status and stop must be real operations.
No remote commits, no installation on the user's computer from this session.

## Chosen approach
Use Python standard library plus a macOS user LaunchAgent and the documented local
`codex app-server` stdio protocol. Markdown alone cannot monitor a finished turn.
A pure prompt-only version was rejected. GUI clicking/private database editing were rejected.

## Important scope decisions
- One registered background job per source Git repository, an isolated local Git worktree,
  and a worker-owned Codex thread; do not attach to arbitrary live GUI threads.
- First start requires a clean, committed source repository. Never stash/reset/commit user changes automatically.
- `watch()` enables; `watch("status")`, `watch("doctor")`, `watch("stop")`, `watch("resume")` are management commands.
- Monitor default 60 seconds; retries default 3; remaining allowance threshold 1%.
- Polling does not start a new model request when a turn is active. Missing quota is not permission to spend.
- ChatGPT login required; no API key fallback, credit purchase, automatic provider switching, force push or deployment.
- Read real account limits. Per-turn sandbox disallows network commands; unattended approval requests pause.
- Completed, user-interrupted, approval-needed, malformed results, unknown crashes during an active turn pause.
- Terminal transient failures with known terminal status and no active children may retry with backoff.
- A normal round may explicitly request the next legitimate task; do not invent backlog.
- Native macOS installation and real Codex model execution are NOT tested in this Linux build environment.

## Planned implementation
1. Add pure command parsing, quota gating, retry classification and tests; integrate before old regex routing.
2. Add a stdio JSON-RPC client, including interleaved notification handling and safe approval refusal.
3. Add a worker with atomic local state, per-job lock, resumable owned thread, and structured round reports.
4. Add macOS LaunchAgent enable/status/stop/resume, isolated worktree initialization, and dry-run support.
5. Update Skill routing, README, method documentation and capability matrix.
6. Run original tests plus new unit and fake-server subprocess tests; package actual files with checksums.

## Verification limits
Fake-protocol tests prove the client/worker's response to tested wire messages, not
compatibility with every installed Codex version or GUI. No claim of production installation.
