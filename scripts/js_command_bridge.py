#!/usr/bin/env python3
"""Pre-route arrow aliases and read-only completions. No model, Git or scheduler writes."""
from pathlib import Path
import json
import math
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PREFIX = re.compile(r'^[@$]?continuous-development(?=\s|$)\s*')
BUILTINS = {'task','always','run','status','stop','help','h','open','handoff','watch','sessions','sync','subagent'}


def _registry_path():
    user = ROOT / 'commands' / 'shortcuts.js'
    return user if user.is_file() else ROOT / 'commands' / 'shortcuts.example.js'


def _request(text, action='inspect', cursor=None):
    exe = shutil.which('node')
    if not exe:
        raise ValueError('JS command support requires a local Node.js executable; nothing was executed')
    req = {'action':action,'text':text,'registryPath':str(_registry_path())}
    if cursor is not None:
        req['cursor']=cursor
    try:
        p = subprocess.run([exe,str(ROOT/'scripts'/'js_commands.cjs')],
            input=json.dumps(req,ensure_ascii=False),text=True,capture_output=True,timeout=5,
            check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f'JS parser unavailable: {exc}') from exc
    try:
        result=json.loads(p.stdout)
    except (ValueError,TypeError) as exc:
        raise ValueError('JS parser returned invalid output; nothing was executed') from exc
    if p.returncode or result.get('kind')=='error':
        raise ValueError(result.get('error','JS parser failed'))
    return result


def _lower(step):
    """Validate the complete intent before returning ANY action to the caller."""
    from watch_policy import parse_watch
    from lifecycle_policy import parse_lifecycle
    name,args=step['command'],step['args']
    if name in {'watch','sessions','sync'}:
        if args and isinstance(args[0],dict):
            options=args[0]
            if any(not isinstance(k,str) or not k.isidentifier() for k in options):
                raise ValueError('Invalid option name')
            syntax=name+'('+', '.join(k+'='+repr(v) for k,v in options.items())+')'
        else:
            syntax=name+'('+', '.join(repr(v) for v in args)+')'
        intent=parse_watch(syntax) if name=='watch' else parse_lifecycle(syntax)
    elif name in {'open','handoff'}:
        syntax=name+'('+', '.join(repr(v) for v in args)+')'
        intent=parse_lifecycle(syntax)
    elif name=='task':
        intent={'command':'task','objective':args[0],'read_only':False,'execution':'not_executed'}
    elif name=='subagent':
        names=args[0] if args else None
        if names is not None and not (isinstance(names,str) and names.strip()) and not (isinstance(names,list) and names and all(isinstance(n,str) and n.strip() for n in names)):
            raise ValueError('subagent() expects a nonempty name/list, or no argument for all')
        intent={'command':'Sub-agent','selection':names,'requires_runtime_resolution':True,'read_only':True,'execution':'not_executed'}
    elif name=='run':
        interval=args[0] if args else '1h'
        if isinstance(interval,bool) or not isinstance(interval,(str,int,float)):
            raise ValueError('Invalid run interval')
        if isinstance(interval,(int,float)):
            if not math.isfinite(interval) or interval<=0:raise ValueError('Interval must be positive and finite')
        elif not re.fullmatch(r'[1-9]\d*[smh]',interval):
            raise ValueError('Use run("1h") or positive numeric hours')
        intent={'command':'run','interval':interval,'requires_scheduler_capability':True,'read_only':False,'execution':'not_executed'}
    else:
        intent={'command':name,'read_only':name in {'help','status'},'execution':'not_executed'}
    return {**step,'intent':intent}


def parse_js(raw):
    """Return None for legacy commands; error / suggestions / static plan otherwise."""
    if not isinstance(raw,str) or len(raw)>16384:
        raise ValueError('Command must be text of at most 16384 characters')
    from lifecycle_policy import _split_objective
    text=PREFIX.sub('',raw.strip(),count=1)
    body,objective=_split_objective(text)
    first=re.match(r'^([A-Za-z_$][A-Za-z0-9_$]*)',body)
    name=first.group(1) if first else ''
    # Existing help expressions keep their old semantics.
    if re.match(r'^(help|h)(?:\s|\(|$)',body):
        return None
    path=_registry_path()
    if path.stat().st_size>262144:raise ValueError('Alias registry too large')
    names=set(re.findall(r'\bconst\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=',path.read_text(encoding='utf8')))
    plain=bool(re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*',body))
    incomplete=bool(first and name in BUILTINS|names and '(' in body and not body.rstrip().endswith(')'))
    js_object=bool(re.match(r'^(watch|sync|sessions)\s*\(\s*\{',body))
    routed=name in {'const','suggest','commands'} or plain or name in names or incomplete or js_object
    if not routed:return None
    result=_request(body if objective else raw)
    if result['kind']=='plan':
        result['steps']=[_lower(s) for s in result['steps']]
        # Preserve existing standalone management restrictions after macro expansion.
        mutable=[s for s in result['steps'] if s['command'] in {'watch','sessions','sync'} and not s['intent']['read_only']]
        if mutable and len(result['steps'])>1:
            raise ValueError('A write-management command must be the only step in an alias')
        result['read_only']=all(s['intent']['read_only'] for s in result['steps'])
        if result['read_only'] and objective:
            raise ValueError('Read-only aliases cannot carry a development objective')
    elif objective:
        raise ValueError('Suggestions/definitions are read-only; do not append a development objective')
    result['objective']=objective
    return result
