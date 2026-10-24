#!/usr/bin/env python3
"""Parse lifecycle commands and calculate safe decisions; NEVER execute actions.

Python >= 3.9, standard library only. No network, file writes, scheduler setup,
subprocess development, model requests, archiving, or Git operations are performed.
The caller must supply live inventory/quota evidence and enforce locks/permissions.
"""
import argparse
import ast
import json
import math
import re
import sys
from typing import Any, Dict, List, Optional

COMMANDS = {'sessions', 'handoff', 'open', 'sync'}
PREFIX = re.compile(r'^[@$]?continuous-development(?=\s|$)\s*')


def _number(value: Any, name: str, low: float, high: Optional[float] = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or (isinstance(value, float) and not math.isfinite(value)):
        raise ValueError(f'{name} must be a finite number')
    if value < low or (high is not None and value > high):
        raise ValueError(f'{name} is outside the allowed range')
    return value


def _integer(value: Any, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return value


def _literal(node: ast.AST) -> Any:
    # Bare names are literal selectors, NOT variables looked up or executed.
    if isinstance(node, ast.Name) and node.id not in {'True', 'False', 'None'}:
        return node.id
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError, RecursionError) as exc:
        raise ValueError('Only literal arguments are permitted; no calls or executable expressions') from exc


def _split_objective(text: str):
    quote = None
    escape = False
    depth = 0
    for i, char in enumerate(text):
        if quote:
            if escape:
                escape = False
            elif char == '\\':
                escape = True
            elif char == quote:
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
        elif char in '([{':
            depth += 1
        elif char in ')]}':
            depth -= 1
        elif depth == 0 and text[i:i + 4] == ' -- ':
            return text[:i].strip(), text[i + 4:].strip()
    return text.strip(), ''


def _target(value: Any) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 for c in value):
        raise ValueError('target must be a non-empty name, ID, path or URL string')
    return value.strip()


def parse_lifecycle(raw_input: str) -> Optional[Dict[str, Any]]:
    """Return None for old commands; raise on malformed reserved new commands.

    A returned object describes intent only. It is not proof of host support or
    an execution receipt. Call before the legacy h/help regex in InvocationParser.
    One lifecycle command per message is intentional to prevent mixed read/write.
    """
    if not isinstance(raw_input, str) or len(raw_input) > 16384:
        raise ValueError('Input must be a string of at most 16384 characters')
    text = PREFIX.sub('', raw_input.strip(), count=1)
    first = re.match(r'^([A-Za-z_]\w*)', text)
    if not first or first.group(1) not in COMMANDS:
        return None
    body, objective = _split_objective(text)
    try:
        node = ast.parse(body, mode='eval').body
    except (SyntaxError, RecursionError) as exc:
        raise ValueError('Use one lifecycle call, e.g. sessions(initial=20, limit=15, rounds=15)') from exc
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id not in COMMANDS:
        raise ValueError('Expected a single direct lifecycle command')
    if len(node.args) > 1:
        raise ValueError('At most one positional selector is allowed; use named parameters')
    args = [_literal(a) for a in node.args]
    kwargs = {}
    for item in node.keywords:
        if item.arg is None or item.arg in kwargs:
            raise ValueError('Duplicate keywords and **kwargs expansion are not allowed')
        kwargs[item.arg] = _literal(item.value)
    command = node.func.id
    action = 'configure' if command in {'sessions', 'sync'} else ('inspect' if command == 'open' else 'export')
    read_only = command == 'open'
    if command in {'sessions', 'sync'} and args:
        if not isinstance(args[0], str) or args[0] not in {'stop', 'status'} or kwargs or objective:
            raise ValueError('Only standalone sessions("stop"/"status") or sync("stop"/"status") accepts a positional action')
        action = args[0]
        read_only = action == 'status'
        params = {}
    elif command == 'sessions':
        allowed = {'initial', 'limit', 'rounds', 'scope'}
        if set(kwargs) - allowed:
            raise ValueError(f'Unknown sessions parameter(s): {sorted(set(kwargs) - allowed)}')
        params = {'initial':20, 'limit':15, 'rounds':15, 'scope':'host', **kwargs}
        if params['initial'] != 'all':
            _integer(params['initial'], 'initial', 1)
        _integer(params['limit'], 'limit', 1)
        _integer(params['rounds'], 'rounds', 1)
        if not isinstance(params['scope'], str) or params['scope'] not in {'host', 'project'}:
            raise ValueError('scope must be host or project')
    elif command in {'open', 'handoff'}:
        if set(kwargs) - {'target'} or (args and 'target' in kwargs):
            raise ValueError('Use either one selector or target=..., not both')
        params = {'target':_target(args[0] if args else kwargs.get('target'))}
        if command == 'open' and objective:
            raise ValueError('open() is read-only and cannot carry a development objective')
    else:
        allowed = {'every', 'threshold', 'on_low', 'remotes'}
        if set(kwargs) - allowed:
            raise ValueError(f'Unknown sync parameter(s): {sorted(set(kwargs) - allowed)}')
        params = {'every':'5m','threshold':1,'on_low':'checkpoint-push-pause','remotes':None, **kwargs}
        interval = params['every']
        if not isinstance(interval, str) or not re.fullmatch(r'[1-9]\d*[mh]', interval):
            raise ValueError('every must use positive minute/hour syntax, e.g. "5m" or "1h"')
        seconds = int(interval[:-1]) * (60 if interval.endswith('m') else 3600)
        if seconds > 86400:
            raise ValueError('every must be no more than 24h')
        params['interval_seconds'] = seconds
        _number(params['threshold'], 'threshold', 0, 100)
        if not isinstance(params['on_low'], str) or params['on_low'] not in {'checkpoint-push-pause','checkpoint-pause','pause','notify'}:
            raise ValueError('Unsupported on_low action')
        remotes = params['remotes']
        if remotes is not None:
            if not isinstance(remotes, list) or not remotes:
                raise ValueError('remotes must be a non-empty list of existing remote names')
            if any(not isinstance(r, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+', r) or r.startswith('-') for r in remotes):
                raise ValueError('Invalid remote name; URLs must be resolved from existing Git configuration')
            params['remotes'] = list(dict.fromkeys(remotes))
    return {'schema':'continuous-development.lifecycle-intent.v1', 'command':command,
            'action':action, 'read_only':read_only, 'params':params,
            'objective':objective, 'execution':'not_executed'}


def admission_budget(open_count: Optional[int], limit: int = 15, reservations: int = 0,
                     pending_requests: int = 1, initial_remaining: int = 0,
                     inventory_complete: bool = True) -> Dict[str, Any]:
    """Pure admission calculation. Caller must atomically reserve slots separately."""
    _integer(limit, 'limit', 1)
    for name, value in [('reservations',reservations),('pending_requests',pending_requests),('initial_remaining',initial_remaining)]:
        _integer(value, name)
    if open_count is not None:
        _integer(open_count, 'open_count')
    if open_count is None or not inventory_complete:
        return {'allowed':0,'free':None,'reason':'inventory_unknown'}
    free = max(0, limit - open_count - reservations)
    if initial_remaining:
        return {'allowed':0,'free':free,'reason':'draining_initial_batch'}
    return {'allowed':min(free,pending_requests),'free':free,
            'reason':'capacity_limit' if free == 0 else ('no_pending_work' if pending_requests == 0 else 'capacity_available')}


def rollover_decision(rounds: Optional[int], task_done: bool, limit: int = 15,
                      busy: bool = False, children_busy: bool = False,
                      checkpoint_ok: bool = False, can_archive: bool = False,
                      can_create: bool = False) -> str:
    """No host operations. task_done must be verified business completion, not a turn end."""
    _integer(limit, 'limit', 1)
    if rounds is not None:
        _integer(rounds, 'rounds')
    due = task_done or (rounds is not None and rounds >= limit)
    if busy or children_busy:
        return 'wait_safe_boundary' if due else 'continue_current_task'
    if not task_done:
        return 'drain_current_task' if due else 'continue_current_task'
    if not checkpoint_ok:
        return 'save_handoff'
    if not (can_archive and can_create):
        return 'blocked_capability'
    return 'archive_ready'


def quota_decision(used_percentages: List[Optional[float]], observed_age_seconds: Optional[float],
                   threshold: float = 1, paused: bool = False, max_age_seconds: float = 120,
                   resume_margin: float = 1) -> Dict[str, Any]:
    """Inputs are applicable, authoritative included-allowance windows, not context usage."""
    _number(threshold,'threshold',0,100)
    _number(max_age_seconds,'max_age_seconds',0)
    _number(resume_margin,'resume_margin',0)
    unknown = {'remaining_percent':None,'decision':'unknown_pause_new_work'}
    if not used_percentages or observed_age_seconds is None:
        return unknown
    _number(observed_age_seconds,'observed_age_seconds',0)
    if observed_age_seconds > max_age_seconds or any(v is None for v in used_percentages):
        return unknown
    for v in used_percentages:
        _number(v,'usedPercent',0,100)
    remaining = min(100 - v for v in used_percentages)
    if remaining <= threshold:
        decision = 'checkpoint_push_pause'
    elif paused and remaining <= min(100, threshold + resume_margin):
        decision = 'remain_paused'
    elif paused:
        decision = 'eligible_to_resume'
    else:
        decision = 'continue'
    return {'remaining_percent':remaining,'decision':decision}


def progress_summary(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """A backlog metric only. No claims about the whole product's completion."""
    total_weight = done_weight = 0
    done = 0
    ids = set()
    for task in tasks:
        tid = task.get('id')
        if not isinstance(tid,str) or not tid or tid in ids:
            raise ValueError('Tasks must have unique non-empty string IDs')
        ids.add(tid)
        weight = task.get('weight',1)
        _number(weight,'weight',0)
        if weight == 0:
            raise ValueError('weight must be greater than zero')
        total_weight += weight
        if task.get('status') == 'done' and task.get('accepted') is True:
            done += 1
            done_weight += weight
    return {'done':done,'total':len(tasks),
            'percent':round(100*done_weight/total_weight,2) if tasks else None,
            'basis':'accepted tasks in supplied backlog snapshot; not total-product progress'}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('invocation', help='Quoted invocation string; validates intent only')
    options = ap.parse_args()
    try:
        result = parse_lifecycle(options.invocation)
        if result is None:
            result = {'handled':False,'execution':'not_executed','reason':'legacy_or_other_command'}
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    except (ValueError,TypeError) as exc:
        print(json.dumps({'error':str(exc),'execution':'not_executed'},ensure_ascii=False), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
