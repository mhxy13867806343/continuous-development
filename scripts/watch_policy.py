#!/usr/bin/env python3
"""Safe watch() intent parsing and pure recovery policy. No actions on import."""
import ast
import io
import tokenize
import json
import math
import re

PREFIX = re.compile(r'^[@$]?continuous-development(?=\s|$)\s*')
REPORT_SCHEMA = {
    'type':'object',
    'properties':{
        'state':{'type':'string','enum':['continue','done','needs_user','blocked']},
        'summary':{'type':'string'}, 'next_task':{'type':'string'},
        'progress_made':{'type':'boolean'},
        'evidence':{'type':'array','items':{'type':'string'}},
    },
    'required':['state','summary','next_task','progress_made','evidence'],
    'additionalProperties':False,
}

def parse_watch(raw):
    if not isinstance(raw,str) or len(raw)>16384:
        raise ValueError('Command must be a string of at most 16384 characters')
    text=PREFIX.sub('',raw.strip(),count=1)
    if re.fullmatch(r'(help|h|help\(\))\s+watch',text):
        return {'command':'watch','action':'help','params':{},'read_only':True,'objective':'','execution':'not_executed'}
    if not re.match(r'^watch\b',text):
        # Reserve watch calls even in unsupported compositions. Never let the
        # legacy regex reinterpret them as normal development or help.
        from lifecycle_policy import _split_objective
        candidate, _ = _split_objective(text)
        try:
            tokens=list(tokenize.generate_tokens(io.StringIO(candidate).readline))
        except (tokenize.TokenError,IndentationError):
            tokens=[]
        for i,t in enumerate(tokens[:-1]):
            if t.type==tokenize.NAME and t.string=='watch' and tokens[i+1].string=='(':
                raise ValueError('watch() must be standalone; do not chain or nest management commands')
        return None
    # Use the lifecycle splitter so -- inside a quoted objective/argument is not executable syntax.
    from lifecycle_policy import _split_objective
    body,objective=_split_objective(text)
    try: node=ast.parse(body,mode='eval').body
    except (SyntaxError,RecursionError) as e: raise ValueError('Use a single watch(...) command') from e
    if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Name) or node.func.id!='watch' or len(node.args)>1:
        raise ValueError('Expected one direct watch(...) call')
    try:
        args=[ast.literal_eval(x) for x in node.args]
        kw={}
        for k in node.keywords:
            if k.arg is None or k.arg in kw: raise ValueError('No **kwargs or duplicate keys')
            kw[k.arg]=ast.literal_eval(k.value)
    except (ValueError,TypeError,SyntaxError,RecursionError) as e:
        raise ValueError('Only literal parameters are allowed') from e
    action=args[0] if args else 'start'
    if not isinstance(action,str) or action not in {'start','status','doctor','stop','resume'}:
        raise ValueError('Supported actions: start, status, doctor, stop, resume')
    if action!='start' and (kw or objective):
        raise ValueError('Status/doctor/stop/resume must be standalone actions')
    if set(kw)-{'every','retry','threshold'}: raise ValueError('Allowed parameters: every, retry, threshold')
    p={'every':'60s','retry':3,'threshold':1,**kw}
    m=re.fullmatch(r'([1-9]\d*)([smh])',p['every']) if isinstance(p['every'],str) else None
    if not m: raise ValueError('every must be a positive duration such as "60s" or "5m"')
    p['every_seconds']=int(m.group(1))*{'s':1,'m':60,'h':3600}[m.group(2)]
    if p['every_seconds']>3600: raise ValueError('every must be between 1s and 1h')
    if isinstance(p['retry'],bool) or not isinstance(p['retry'],int) or not 0<=p['retry']<=10:
        raise ValueError('retry must be an integer from 0 to 10')
    t=p['threshold']
    if isinstance(t,bool) or not isinstance(t,(int,float)) or not math.isfinite(t) or not 0<=t<100:
        raise ValueError('threshold is remaining allowance percent, from 0 inclusive to 100 exclusive')
    return {'schema':'continuous-development.watch-intent.v1','command':'watch','action':action,
            'params':p if action=='start' else {},'read_only':action in {'status','doctor'},
            'objective':objective,'execution':'not_executed'}

def quota_gate(result,threshold=1):
    """Conservatively use the lowest known remaining applicable allowance window."""
    buckets=[]
    if isinstance(result,dict):
        b=result.get('rateLimitsByLimitId')
        if isinstance(b,dict) and b: buckets=list(b.values())
        elif isinstance(result.get('rateLimits'),dict): buckets=[result['rateLimits']]
    vals=[]; reached=False; resets=[]
    for b in buckets:
        if not isinstance(b,dict): return {'status':'unknown','remaining':None}
        reached=reached or bool(b.get('rateLimitReachedType'))
        found=False
        for key in ['primary','secondary']:
            w=b.get(key)
            if w is None: continue
            found=True
            v=w.get('usedPercent') if isinstance(w,dict) else None
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=100:
                return {'status':'unknown','remaining':None}
            vals.append(100-v)
            r=w.get('resetsAt')
            if isinstance(r,(int,float)) and not isinstance(r,bool): resets.append(r)
        if not found: return {'status':'unknown','remaining':None}
    if not vals: return {'status':'unknown','remaining':None}
    remaining=min(vals)
    return {'status':'low' if reached or remaining<=threshold else 'ok','remaining':remaining,'resets_at':resets}

def retry_delay(attempt,base=60):
    return min(3600,max(5,base)*(2**min(10,max(0,attempt-1))))

def classify_failure(error):
    info=error.get('codexErrorInfo') if isinstance(error,dict) else None
    if isinstance(info,dict): info=next(iter(info),'unknown')
    if info in {'usageLimitExceeded','rateLimitExceeded'}: return 'quota'
    if info in {'responseStreamDisconnected','httpConnectionFailed','responseStreamConnectionFailed',
                'connectionFailed','serverError','internalServerError'}: return 'retry'
    return 'needs_user'

def validate_report(text):
    try: report=json.loads(text)
    except (ValueError,TypeError) as e: raise ValueError('Worker did not return a valid JSON report') from e
    if not isinstance(report,dict) or set(report)!=set(REPORT_SCHEMA['required']):
        raise ValueError('Unexpected worker report fields')
    if report['state'] not in REPORT_SCHEMA['properties']['state']['enum']: raise ValueError('Invalid state')
    if not isinstance(report['summary'],str) or not isinstance(report['next_task'],str): raise ValueError('Invalid report text')
    if not isinstance(report['progress_made'],bool): raise ValueError('Invalid progress_made')
    if not isinstance(report['evidence'],list) or any(not isinstance(x,str) for x in report['evidence']): raise ValueError('Invalid evidence')
    if report['state']=='continue' and (not report['next_task'].strip() or not report['progress_made'] or not report['evidence']):
        raise ValueError('Continuation requires a real next task, progress and evidence')
    return report
