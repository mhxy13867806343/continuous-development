#!/usr/bin/env python3
"""Merge this extension into an existing skill. Dry-run by default.

Only edits local skill files. No Git commands, model calls, thread operations,
network access, scheduler installation, or credential changes are performed.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import uuid

PACKAGE = Path(__file__).resolve().parent
COPY_FILES = [
 'session-lifecycle.md','handoff.md','progress.md','sync-quota.md',
 'host-adapters.md','lifecycle.defaults.json','templates/SESSION-HANDOFF.md',
 'scripts/lifecycle_policy.py','tests/test_lifecycle_policy.py',
 'README-SESSION-MANAGEMENT.md','SESSION-INTEGRATION.md','docs/SOURCES.md',
]

ROUTING = '''
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
'''
INVOCATION = '''
<!-- lifecycle-extension-v1: commands -->
### Session lifecycle, progress and sync

- `sessions(initial=20, limit=15, rounds=15, scope="host")`: adopt a verified
  initial batch, finish old tasks, save handoffs and archive safely, then refill
  within the cap. Threshold rounds do not mark an unfinished task complete.
- `sessions("status")` / `sessions("stop")`: inspect/disable that manager only.
- `handoff()` / `handoff("source ID or URL")`: private Markdown handoff.
- `open()` / `open("project name/ID/path or thread URL")`: read-only progress.
- `sync(every="5m", threshold=1, on_low="checkpoint-push-pause")`: request
  a real supported/local synchronization schedule and a low-quota gate.
- `sync("status")` / `sync("stop")`: inspect/disable that synchronization job.

See README-SESSION-MANAGEMENT.md and SESSION-INTEGRATION.md for capability
requirements. Use one lifecycle command per message. New command arguments
are literals only. Parse them with scripts/lifecycle_policy.py before legacy
h/help matching. Syntax accepted does not mean a timer or host operation ran.
<!-- /lifecycle-extension-v1: commands -->
'''
ORCHESTRATION = '''
<!-- lifecycle-extension-v1: admission -->
## Lifecycle admission before delegation

Apply enabled lifecycle/quota checks before dispatch. Drain the initial batch
without killing running tasks. A rotation-requested thread may finish its
current scoped task but must not accept another. A turn completion notification
is not business-task completion. Reserve thread capacity under a scope-wide
lock before creating successors. Verify handoff, safe execution state and
archive success first. Never bypass a pause using subagents or recovery jobs.
See session-lifecycle.md and sync-quota.md.
<!-- /lifecycle-extension-v1: admission -->

'''
QUOTA = '''
<!-- lifecycle-extension-v1: quota-priority -->
When sync-quota protection is enabled, authoritative remaining allowance at
or below its configured threshold is a valid protective pause, even before
the platform rejects a request. This overrides the older "only stop on actual
blocking signals" wording below. Unknown/stale quota is not a guessed numeric
value. Save checkpoints during work; a hard limit may prevent a final summary.
See sync-quota.md. Prompt instructions cannot disable account credit billing.
<!-- /lifecycle-extension-v1: quota-priority -->
'''
GIT = '''
<!-- lifecycle-extension-v1: sync -->
Periodic sync may publish only explicitly authorized reviewed checkpoints,
not arbitrary dirty work. Use repository locks, explicit branch destinations,
and independent live verification of every remote. Do not publish other
projects or private conversation handoffs to this public Skill repository.
Failed uploads are retried without force push or empty commits. See sync-quota.md.
<!-- /lifecycle-extension-v1: sync -->

'''
DOC = '''
<!-- lifecycle-extension-v1: progress -->
Store private thread handoffs separately from public progress. open() reports
only a known task-snapshot denominator; unknown evidence stays unknown. Record
actual archive/create/sync receipts, not plans as successful actions. Keep
post-push receipts in local state to avoid endless commits recording their own
commit SHA. See handoff.md and progress.md.
<!-- /lifecycle-extension-v1: progress -->

'''
README = '''

<!-- lifecycle-extension-v1: readme -->
## 会话管理、进度查看与低额度同步扩展

使用与限制见 [README-SESSION-MANAGEMENT.md](README-SESSION-MANAGEMENT.md)，
宿主接入步骤见 [SESSION-INTEGRATION.md](SESSION-INTEGRATION.md)。

```text
@continuous-development sessions(initial=20, limit=15, rounds=15)
@continuous-development handoff()
@continuous-development open()
@continuous-development sync(every="5m", threshold=1, on_low="checkpoint-push-pause")
```

本扩展脚本只做安全解析和策略计算。实际会话管理、5分钟定时器和Git推送
需要相应宿主工具/执行器接入并验证；安装文档不等于这些功能已经启用。
<!-- /lifecycle-extension-v1: readme -->
'''


def sha(data): return hashlib.sha256(data).hexdigest()


def _insert(text, anchor, block, marker, before=False):
    if marker in text:
        if block.strip() not in text:
            raise ValueError(f'Existing integration was edited; merge manually: {marker}')
        return text
    if text.count(anchor) != 1:
        raise ValueError(f'Expected one exact anchor, found {text.count(anchor)}: {anchor!r}')
    return text.replace(anchor, block + anchor if before else anchor + block, 1)


def _safe_path(root, rel):
    p = root / rel
    for part in [p, *p.parents]:
        if part == root.parent: break
        if part.is_symlink(): raise ValueError(f'Symlink path requires manual review: {p}')
    return p


def plan_changes(target):
    target = Path(target).expanduser()
    if not target.is_dir() or target.is_symlink():
        raise ValueError('Target must be an existing non-symlink skill directory')
    target = target.resolve()
    names = ['SKILL.md','invocation.md','orchestration.md','quota-safety.md',
             'git.md','documentation.md','README.md','scripts/parse_invocation.py']
    old = {}
    for rel in names:
        p = _safe_path(target, rel)
        old[rel] = p.read_bytes()
    texts = {k:v.decode('utf-8') for k,v in old.items()}
    if 'name: continuous-development' not in texts['SKILL.md'].split('---',2)[1]:
        raise ValueError('Target SKILL.md is not continuous-development')
    s = texts['SKILL.md']
    s = _insert(s, '9. `subagents.md`', '\n10. `session-lifecycle.md`\n11. `handoff.md`\n12. `progress.md`\n13. `sync-quota.md`\n14. `host-adapters.md`', '10. `session-lifecycle.md`')
    s = _insert(s, '## Command routing takes precedence\n', ROUTING, '<!-- lifecycle-extension-v1: routing -->')
    texts['SKILL.md'] = s
    texts['invocation.md'] = _insert(texts['invocation.md'], '## Supported commands\n', INVOCATION, '<!-- lifecycle-extension-v1: commands -->')
    texts['orchestration.md'] = _insert(texts['orchestration.md'], '## Dynamic workstreams\n', ORCHESTRATION, '<!-- lifecycle-extension-v1: admission -->', before=True)
    texts['quota-safety.md'] = _insert(texts['quota-safety.md'], '## Usage / quota rules\n', QUOTA, '<!-- lifecycle-extension-v1: quota-priority -->')
    texts['git.md'] = _insert(texts['git.md'], '## Review before commit\n', GIT, '<!-- lifecycle-extension-v1: sync -->', before=True)
    texts['documentation.md'] = _insert(texts['documentation.md'], '## Discover existing conventions\n', DOC, '<!-- lifecycle-extension-v1: progress -->', before=True)
    if '<!-- lifecycle-extension-v1: readme -->' not in texts['README.md']:
        texts['README.md'] = texts['README.md'].rstrip() + README
    elif README.strip() not in texts['README.md']:
        raise ValueError('README lifecycle section was edited; merge manually')
    s = texts['scripts/parse_invocation.py']
    block = '\n# lifecycle-extension-v1: safe management routing\nfrom lifecycle_policy import parse_lifecycle\n'
    s = _insert(s, 'import sys\n', block, '# lifecycle-extension-v1: safe management routing')
    block = ('        # lifecycle-extension-v1: route before legacy h/help regex\n'
             '        lifecycle = parse_lifecycle(raw_input)\n'
             '        if lifecycle is not None:\n'
             '            return lifecycle\n\n')
    s = _insert(s, '    def parse(self, raw_input: str) -> dict:\n', block, '# lifecycle-extension-v1: route before legacy h/help regex')
    old_call = '        result = parser.parse(expr)\n'
    new_call = ('        # lifecycle-extension-v1: invalid management input never falls through\n'
                '        try:\n'
                '            result = parser.parse(expr)\n'
                '        except ValueError as exc:\n'
                '            print(json.dumps({"error": str(exc), "execution": "not_executed"}, ensure_ascii=False), file=sys.stderr)\n'
                '            raise SystemExit(2)\n')
    if '# lifecycle-extension-v1: invalid management input never falls through' not in s:
        if s.count(old_call) != 1: raise ValueError('CLI parse call changed; manual merge required')
        s = s.replace(old_call,new_call,1)
    texts['scripts/parse_invocation.py'] = s
    compile(s, 'scripts/parse_invocation.py', 'exec')
    planned = []
    for rel,text in texts.items():
        data=text.encode('utf-8')
        if data != old[rel]: planned.append((rel,old[rel],data))
    for rel in COPY_FILES:
        source=(PACKAGE/rel).read_bytes()
        destination=_safe_path(target,rel)
        previous=destination.read_bytes() if destination.exists() else None
        if previous is not None and previous != source:
            raise ValueError(f'New extension file already differs; preserve and merge manually: {rel}')
        if previous != source: planned.append((rel,previous,source))
    return target,planned


def _atomic_write(path, data, mode=0o644):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.'+path.name+'.', dir=str(path.parent))
    try:
        with os.fdopen(fd,'wb') as out:
            out.write(data);out.flush();os.fsync(out.fileno())
        os.chmod(name,mode)
        os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)


def install(target, apply=False, backup_root=None):
    target,plan=plan_changes(target)
    report={'target':str(target),'apply':apply,'changes':[
        {'path':rel,'operation':'create' if before is None else 'edit',
         'before_sha256':sha(before) if before is not None else None,'after_sha256':sha(after)}
        for rel,before,after in plan], 'host_operations':'not_executed'}
    if not apply or not plan: return report
    backup_root=Path(backup_root or Path.home()/'.continuous-development/backups').expanduser().resolve()
    if backup_root == target or target in backup_root.parents:
        raise ValueError('Backups must be outside the skill directory')
    backup=backup_root/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8])
    backup.mkdir(parents=True,mode=0o700)
    modes={}
    for rel,before,_ in plan:
        p=_safe_path(target,rel)
        modes[rel]=stat.S_IMODE(p.stat().st_mode) if p.exists() else 0o644
        if before is not None:
            dest=backup/rel;dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(before);dest.chmod(0o600)
    (backup/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (backup/'manifest.json').chmod(0o600)
    applied=[]
    try:
        for rel,before,after in plan:
            p=_safe_path(target,rel)
            current=p.read_bytes() if p.exists() else None
            if current != before: raise ValueError(f'File changed since preflight: {rel}')
            _atomic_write(p,after,modes[rel]);applied.append((rel,before,after))
    except Exception:
        # Restore only our unchanged writes; never overwrite concurrent user changes.
        for rel,before,after in reversed(applied):
            p=target/rel
            if p.exists() and p.read_bytes() == after:
                if before is None: p.unlink()
                else: _atomic_write(p,before,modes[rel])
        raise
    report['backup']=str(backup)
    report['installed_files']=len(plan)
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--target',required=True,help='Existing continuous-development directory')
    ap.add_argument('--apply',action='store_true',help='Actually merge after successful preflight; otherwise dry-run')
    ap.add_argument('--backup-root',help='Optional backup parent, outside target')
    args=ap.parse_args()
    try:
        print(json.dumps(install(args.target,args.apply,args.backup_root),ensure_ascii=False,indent=2))
        return 0
    except (OSError,ValueError,UnicodeError,IndexError,SyntaxError) as exc:
        print(json.dumps({'error':str(exc),'host_operations':'not_executed'},ensure_ascii=False),file=sys.stderr)
        return 2

if __name__=='__main__': raise SystemExit(main())
