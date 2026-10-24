#!/usr/bin/env python3
"""watch() local runner, Python >=3.9. macOS LaunchAgent + Codex App Server.

The monitor only owns its private Git worktree and its own background thread.
It never attaches to arbitrary GUI conversations. All commands default to a
preview unless --apply is specified. No purchase, provider fallback or push.
"""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import signal
import subprocess
import sys
import time
import uuid

from watch_policy import parse_watch, retry_delay
from watch_rpc import CodexAdapter, NeedUser, LostConnection, RpcError, QuotaPause, TerminalFailure

TERMINAL={'done','needs_user','ambiguous','blocked','stopped','install_failed'}


def atomic_json(path,data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    temp=path.with_name(path.name+'.tmp-'+uuid.uuid4().hex)
    fd=os.open(temp,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(data,f,ensure_ascii=False,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.replace(temp,path)
    finally:
        if temp.exists(): temp.unlink()


def read_json(path,default):
    try:
        with open(path,encoding='utf-8') as f: value=json.load(f)
    except FileNotFoundError: return default
    if not isinstance(value,dict): raise ValueError('Invalid state file: '+str(path))
    return value


@contextlib.contextmanager
def job_lock(path):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd=os.open(path,os.O_CREAT|os.O_RDWR,0o600)
    try:
        try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as e: raise ValueError('This project is already managed by another worker') from e
        yield
    finally: os.close(fd)


def is_locked(path):
    p=Path(path)
    if not p.exists(): return False
    try:
        with job_lock(p): return False
    except ValueError: return True


def git(project,*args):
    result=subprocess.run(['git','-C',str(project),*args],capture_output=True,text=True,
                          env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'},timeout=30)
    if result.returncode: raise ValueError('Git check failed: '+result.stderr.strip()[:1000])
    return result.stdout.strip()


def project_info(path):
    p=Path(path).expanduser().resolve(strict=True)
    root=Path(git(p,'rev-parse','--show-toplevel')).resolve()
    common=Path(git(root,'rev-parse','--git-common-dir'))
    if not common.is_absolute(): common=root/common
    common=common.resolve()
    key=hashlib.sha256(str(common).encode()).hexdigest()[:20]
    return {'project':str(root),'id':key,'git_common':str(common)}


def prepare_workspace(project,job):
    """Snapshot committed work only; never stage, stash, reset or copy secrets."""
    if git(project,'status','--porcelain'):
        raise ValueError('Source repository has local changes. Save a reviewed checkpoint first; watcher will not auto-commit/stash them.')
    git(project,'rev-parse','--verify','HEAD')
    workspace=Path(job)/'workspace'
    if workspace.exists(): raise ValueError('Workspace already exists; inspect it instead of overwriting')
    branch='cd-watch/'+Path(job).name+'-'+uuid.uuid4().hex[:8]
    git(project,'worktree','add','-b',branch,str(workspace),'HEAD')
    return workspace,branch


def fingerprint(project):
    """Hash repository state without writing its contents into monitor logs."""
    parts=[git(project,'rev-parse','HEAD'),git(project,'diff','HEAD','--'),git(project,'status','--porcelain')]
    # Include safe untracked regular files; only their digest is retained.
    names=subprocess.check_output(['git','-C',str(project),'ls-files','--others','--exclude-standard','-z'])
    for name in names.split(b'\0'):
        if not name: continue
        path=Path(project)/os.fsdecode(name)
        if path.is_symlink() or not path.is_file(): continue
        h=hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda:f.read(65536),b''): h.update(chunk)
        parts.append(os.fsdecode(name)+':'+h.hexdigest())
    return hashlib.sha256('\0'.join(parts).encode()).hexdigest()


def enabled(job):
    return read_json(Path(job)/'control.json',{'enabled':False}).get('enabled') is True


def worker_prompt(config,state):
    return '''$continuous-development
You are the sole worker of a user-enabled local watch() job, in an isolated Git worktree.
These explicit watch constraints override the generic continuous-loop/Git rules:
- Perform ONE coherent, safe round toward the objective, verify it, then return the requested JSON report.
- Do not call watch(), always(), run(), sessions(), sync(), or install another monitor.
- Do not spawn child agents or detached/background commands in this first watch adapter; all work must finish within this turn.
- Respect repository AGENTS.md, preserve existing work, do not invent features to remain busy.
- Never commit, push, merge, deploy, purchase credits, switch provider, run paid external tools or destructive operations.
- Never edit monitor state outside the workspace. Do not claim to be operating the user's GUI thread.
- For ambiguity or approvals return needs_user; no executable backlog means done.
- Set continue only with an actual next task, verified evidence, and progress_made=true.
- A short final summary is not itself evidence of progress. All tests/claims must be truthful.
- After any previous interruption inspect the current diff before modifying anything again.
Objective: '''+config['objective']+'\nPrevious checkpoint: '+json.dumps(state.get('last_report',{}),ensure_ascii=False)


def run_job(job,adapter_factory=CodexAdapter,sleep_fn=time.sleep,max_cycles=None):
    job=Path(job).resolve()
    with job_lock(job/'worker.lock'):
        state=read_json(job/'state.json',{})
        state.setdefault('rounds_completed',0); state.setdefault('failure_count',0); state.setdefault('no_change_count',0)
        state['worker_pid']=os.getpid()
        stop_signal=[False]
        def sigstop(*_): stop_signal[0]=True
        old_handlers={}
        # signal setup only runs on the main thread; tests use this function directly.
        import threading
        if threading.current_thread() is threading.main_thread():
            for sig in (signal.SIGTERM,signal.SIGINT): old_handlers[sig]=signal.signal(sig,sigstop)
        def stopped(): return stop_signal[0] or not enabled(job)
        def save(phase=None):
            if phase is not None: state['phase']=phase
            state['heartbeat_at']=time.time(); atomic_json(job/'state.json',state)
        def wait(seconds):
            state['next_check_at']=time.time()+seconds; save()
            if sleep_fn is not time.sleep:
                sleep_fn(seconds); return
            end=time.monotonic()+seconds
            while time.monotonic()<end and not stopped(): time.sleep(min(1,end-time.monotonic()))
        adapter=None; cycles=0
        try:
            if stopped(): save('stopped'); return
            if state.get('phase') in TERMINAL: save(); return
            if state.get('active_turn'):
                state['reason']='Previous worker ended during a turn; verify no orphan work before watch("resume").'
                save('ambiguous'); return
            old_server=state.get('server_pid')
            if isinstance(old_server,int) and old_server>0:
                try: os.kill(old_server,0)
                except ProcessLookupError: pass
                except PermissionError:
                    state['reason']='Prior app-server ownership cannot be verified'; save('ambiguous'); return
                else:
                    state['reason']='Prior app-server PID still exists; do not spawn a duplicate'; save('ambiguous'); return
            while not stopped() and (max_cycles is None or cycles<max_cycles):
                cycles+=1
                config=read_json(job/'config.json',{})
                interval=config['every_seconds']
                try:
                    if adapter is None:
                        argv=[config['codex'],'-c','model_provider="openai"','app-server']
                        adapter=adapter_factory(argv,config['workspace'])
                        save('connecting'); adapter.connect()
                        state['server_pid']=adapter.rpc.proc.pid; save()
                    q=adapter.read_quota(config['threshold'])
                    state['quota']={**q,'observed_at':time.time()}
                    # Resume a low-quota pause only with a small positive margin.
                    if q['status']!='ok' or (state.get('phase')=='quota_wait' and q['remaining']<=config['threshold']+1):
                        state['reason']='Waiting for confirmed allowance above threshold'
                        save('quota_wait'); wait(max(60,interval)); continue
                    if stopped(): break
                    tid=adapter.ensure_thread(state.get('thread_id'))
                    state['thread_id']=tid; save('ready')
                    before=fingerprint(config['workspace'])
                    # Persist before sending turn/start: lost acknowledgement must not cause a duplicate.
                    state['active_turn']='pending-start'; save('starting_turn')
                    def on_state(phase,turn):
                        state['active_turn']=turn; save(phase)
                    report=adapter.run_turn(tid,worker_prompt(config,state),config['threshold'],stopped,on_state,
                                            skill_path=config.get('skill_path'))
                    state['last_report']=report; state['rounds_completed']+=1; state['failure_count']=0
                    state['reason']=report['summary']; state['active_turn']=None
                    after=fingerprint(config['workspace'])
                    state['no_change_count']=state['no_change_count']+1 if before==after else 0
                    # Private durable handoff; intentionally not committed into the user's project.
                    atomic_json(job/'last-report.json',report)
                    if report['state']=='done': save('done'); break
                    if report['state'] in {'needs_user','blocked'}: save(report['state']); break
                    if state['no_change_count']>=3:
                        state['reason']='Three continuation rounds without repository change; review to avoid busy loops'
                        save('needs_user'); break
                    save('waiting'); wait(interval)
                except QuotaPause as e:
                    state['active_turn']=None; state['reason']=str(e); save('quota_wait'); wait(max(60,interval))
                except TerminalFailure as e:
                    state['active_turn']=None; state['reason']=str(e)
                    if e.policy=='quota': save('quota_wait'); wait(max(60,interval)); continue
                    state['failure_count']+=1
                    if e.policy!='retry' or state['failure_count']>config['retry']:
                        save('needs_user'); break
                    save('retry_wait'); wait(retry_delay(state['failure_count'],max(60,interval)))
                except LostConnection as e:
                    state['reason']=str(e)
                    if state.get('active_turn'):
                        save('ambiguous'); break
                    state['failure_count']+=1
                    if adapter: adapter.close(); adapter=None
                    state['server_pid']=None
                    if state['failure_count']>config['retry']: save('needs_user'); break
                    save('retry_wait'); wait(retry_delay(state['failure_count'],max(60,interval)))
                except (NeedUser,RpcError,ValueError,OSError) as e:
                    state['reason']=str(e)[:1000]; save('stopped' if stopped() else 'needs_user'); break
            if stopped(): state['reason']='Explicit stop or system shutdown signal'; save('stopped')
        finally:
            if adapter:
                if adapter.active_turn: adapter.interrupt()
                adapter.close()
            state['server_pid']=None; state['worker_pid']=None; save()
            for sig,handler in old_handlers.items(): signal.signal(sig,handler)


def launch_agent(job,label):
    job=Path(job).resolve()
    return {
        'Label':label,
        'ProgramArguments':[str(Path(sys.executable).resolve()),str(Path(__file__).resolve()),'--worker',str(job)],
        'WorkingDirectory':str(job),'RunAtLoad':True,'KeepAlive':{'SuccessfulExit':False},'ThrottleInterval':30,
        'EnvironmentVariables':{'PATH':os.environ.get('PATH','/usr/bin:/bin'),
             'HOME':str(Path.home()),'CODEX_HOME':os.environ.get('CODEX_HOME',str(Path.home()/'.codex')),
             'CONTINUOUS_WATCH_WORKER':'1'},
        'StandardOutPath':str(job/'service.out.log'),'StandardErrorPath':str(job/'service.err.log'),
    }


def service_status(label):
    if sys.platform!='darwin': return {'supported':False,'registered':False}
    p=subprocess.run(['launchctl','print',f'gui/{os.getuid()}/{label}'],capture_output=True,text=True,timeout=10)
    return {'supported':True,'registered':p.returncode==0}


def receipt(job,label):
    job=Path(job)
    return {'job_dir':str(job),'enabled':enabled(job), 'worker_lock_held':is_locked(job/'worker.lock'),
            'service':service_status(label),'state':read_json(job/'state.json',{}),
            'config':read_json(job/'config.json',{})}


def register_service(job,label):
    agents=Path.home()/'Library'/'LaunchAgents'; agents.mkdir(parents=True,exist_ok=True)
    path=agents/(label+'.plist')
    if path.is_symlink(): raise ValueError('Refusing symlink LaunchAgent path')
    plist=launch_agent(job,label)
    data=plistlib.dumps(plist)
    fd=os.open(path,os.O_CREAT|os.O_TRUNC|os.O_WRONLY,0o600)
    with os.fdopen(fd,'wb') as f: f.write(data)
    if not service_status(label)['registered']:
        p=subprocess.run(['launchctl','bootstrap',f'gui/{os.getuid()}',str(path)],capture_output=True,text=True,timeout=15)
        if p.returncode: raise ValueError('launchctl bootstrap failed: '+p.stderr.strip())
    else:
        p=subprocess.run(['launchctl','kickstart',f'gui/{os.getuid()}/{label}'],capture_output=True,text=True,timeout=15)
        if p.returncode: raise ValueError('launchctl kickstart failed: '+p.stderr.strip())
    if not service_status(label)['registered']: raise ValueError('LaunchAgent read-back did not confirm registration')


def default_home():
    return Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))/'continuous-development'/'watch'


def dispatch(raw,project,apply=False):
    intent=parse_watch(raw)
    if intent is None: raise ValueError('Expected watch() management method')
    action=intent['action']
    if action=='help':
        return {'methods':['watch()','watch(every="60s", retry=3, threshold=1)',
                           'watch("doctor")','watch("status")','watch("stop")','watch("resume")'],
                'scope':'macOS local Codex worker in an isolated worktree; not GUI takeover'}
    info=project_info(project); job=default_home()/info['id']; label='local.continuous-development.watch.'+info['id']
    if action=='status': return receipt(job,label)
    binary=shutil.which('codex')
    if action=='doctor':
        result={'platform':sys.platform,'macos_service_supported':sys.platform=='darwin','codex_found':bool(binary),
                'git_clean':not bool(git(info['project'],'status','--porcelain')),
                'model_requests_sent':0,'auth_type':None,'quota':{'status':'unknown','remaining':None}}
        if binary:
            a=CodexAdapter([str(Path(binary).resolve()),'-c','model_provider="openai"','app-server'],info['project'])
            try:
                a.connect(); result['auth_type']=a.account_type; result['quota']=a.read_quota(1)
            except (NeedUser,LostConnection,RpcError,OSError) as e: result['error']=str(e)
            finally: a.close()
        return result
    if not apply:
        return {'execution':'not_executed','preview':intent,'project':info['project'],
                'note':'--apply enables/disables the real local service; it does not guarantee GUI control.'}
    if os.environ.get('CONTINUOUS_WATCH_WORKER')=='1': raise ValueError('A watcher worker cannot install or reconfigure a watcher')
    if sys.platform!='darwin': raise ValueError('Automatic service installation is implemented for macOS only')
    # Never register state inside the source repository (avoid exposing private records in Git).
    root=Path(info['project']).resolve(); home=default_home().resolve()
    if home==root or root in home.parents: raise ValueError('Watcher state directory must be outside the source repository')
    if action in {'resume','stop'} and not (job/'config.json').exists(): return {'execution':'not_executed','reason':'No watcher registered for this repository'}
    job.mkdir(parents=True,exist_ok=True,mode=0o700); os.chmod(job,0o700)
    with job_lock(job/'manager.lock'):
        if action=='stop':
            atomic_json(job/'control.json',{'enabled':False,'stopped_at':time.time()})
            deadline=time.monotonic()+12
            while is_locked(job/'worker.lock') and time.monotonic()<deadline: time.sleep(.2)
            if not is_locked(job/'worker.lock'):
                subprocess.run(['launchctl','bootout',f'gui/{os.getuid()}/{label}'],capture_output=True,timeout=10)
                path=Path.home()/'Library'/'LaunchAgents'/(label+'.plist')
                if path.exists() and not path.is_symlink(): path.unlink()
            r=receipt(job,label); r['stop_requested']=True; return r
        if is_locked(job/'worker.lock'): return receipt(job,label)
        if action=='start' and (job/'config.json').exists():
            r=receipt(job,label); r['note']='Existing job retained; use watch("resume") to resume a stopped job. Settings were not overwritten.'; return r
        if not binary: raise ValueError('codex executable not found in PATH; install/authenticate it before enabling watch')
        if action=='start':
            # Probe auth/capabilities before writing Git worktree or service config.
            probe=CodexAdapter([str(Path(binary).resolve()),'-c','model_provider="openai"','app-server'],info['project'])
            try: probe.connect(); probe.read_quota(intent['params']['threshold'])
            finally: probe.close()
            workspace,branch=prepare_workspace(info['project'],job)
            config={**intent['params'],'project':info['project'],'workspace':str(workspace),'branch':branch,
                    'codex':str(Path(binary).resolve()),'objective':intent['objective'] or 'Continue the repository existing explicit backlog, verify changes; do not invent new features.',
                    'skill_path':str(Path(__file__).resolve().parents[1]/'SKILL.md')}
            atomic_json(job/'config.json',config)
            state={'phase':'ready','active_turn':None,'thread_id':None,'rounds_completed':0,'failure_count':0,'no_change_count':0}
        else:
            state=read_json(job/'state.json',{})
            if state.get('phase')=='done': raise ValueError('Task is marked done; no automatic restart without a new scoped objective')
            state.update({'phase':'ready','active_turn':None,'failure_count':0,'no_change_count':0})
        atomic_json(job/'state.json',state)
        atomic_json(job/'control.json',{'enabled':True,'enabled_at':time.time()})
        try: register_service(job,label)
        except (ValueError,OSError,subprocess.TimeoutExpired) as e:
            atomic_json(job/'control.json',{'enabled':False})
            state.update({'phase':'install_failed','reason':str(e)}); atomic_json(job/'state.json',state)
            raise
        r=receipt(job,label); r['execution']='service_registered'; return r


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--worker',type=Path,help=argparse.SUPPRESS)
    p.add_argument('--project',default=os.getcwd())
    p.add_argument('--invocation',default='watch("status")')
    p.add_argument('--apply',action='store_true')
    args=p.parse_args()
    try:
        if args.worker:
            run_job(args.worker); return 0
        result=dispatch(args.invocation,args.project,args.apply)
        print(json.dumps(result,ensure_ascii=False,indent=2)); return 0
    except Exception as e:
        print(json.dumps({'error':str(e),'execution':'not_completed'},ensure_ascii=False),file=sys.stderr)
        return 2

if __name__=='__main__': raise SystemExit(main())
