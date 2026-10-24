#!/usr/bin/env python3
"""Local Codex App Server adapter. No sockets, credentials, model calls at import.

Uses the documented stdio JSON-RPC wire format. All incoming approval/input
requests are refused and cause a human-review pause; never grant permissions.
"""
from collections import deque
import json
import os
import queue
import subprocess
import threading
import time
from watch_policy import REPORT_SCHEMA, quota_gate, validate_report, classify_failure

class NeedUser(RuntimeError): pass
class LostConnection(RuntimeError): pass
class QuotaPause(RuntimeError): pass
class RpcError(RuntimeError): pass
class TerminalFailure(RuntimeError):
    def __init__(self,error):
        self.policy=classify_failure(error)
        super().__init__(json.dumps(error,ensure_ascii=False)[:1000])

class JsonRpc:
    def __init__(self,argv,cwd,stderr=None):
        env=os.environ.copy()
        # Do not silently replace a ChatGPT login with a billable API key.
        for k in ['OPENAI_API_KEY','CODEX_API_KEY']: env.pop(k,None)
        self.proc=subprocess.Popen(argv,cwd=cwd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                   stderr=stderr if stderr is not None else subprocess.DEVNULL,
                                   text=True,encoding='utf-8',bufsize=1,env=env)
        self.inbox=queue.Queue(maxsize=4096)
        self.events=deque(); self.replies={}; self.seq=0; self.closed=False
        self.reader=threading.Thread(target=self._reader,daemon=True)
        self.reader.start()
    def _put(self,message):
        while not self.closed:
            try: self.inbox.put(message,timeout=.1); return
            except queue.Full: continue
    def _reader(self):
        try:
            while not self.closed:
                line=self.proc.stdout.readline(8*1024*1024+1)
                if not line: break
                if len(line)>8*1024*1024:
                    self._put(LostConnection('App-server line exceeded safety limit')); return
                try: m=json.loads(line)
                except ValueError:
                    self._put(LostConnection('App-server returned non-JSON data')); return
                if not isinstance(m,dict):
                    self._put(LostConnection('Unexpected protocol message')); return
                # Discard huge token/command streams; keep terminal/state events.
                if 'id' not in m:
                    method=m.get('method','')
                    if method not in {'turn/completed','account/rateLimits/updated','account/updated','item/completed','error'}:
                        continue
                    if method=='item/completed' and m.get('params',{}).get('item',{}).get('type')!='agentMessage':
                        continue
                self._put(m)
        except (OSError,ValueError) as e:
            self._put(LostConnection(str(e)))
        finally: self._put(LostConnection('App-server connection closed'))
    def send(self,message):
        try:
            self.proc.stdin.write(json.dumps(message,ensure_ascii=False)+'\n'); self.proc.stdin.flush()
        except (BrokenPipeError,OSError,ValueError) as e:
            raise LostConnection('App-server stdin closed') from e
    def _get(self,timeout):
        try: m=self.inbox.get(timeout=timeout)
        except queue.Empty: return None
        if isinstance(m,Exception): raise m
        if 'method' in m and 'id' in m:
            self.send({'id':m['id'],'error':{'code':-32001,'message':'Unattended watcher cannot approve. User review required.'}})
            raise NeedUser('Server requested input or approval: '+str(m['method']))
        return m
    def request(self,method,params=None,timeout=30):
        self.seq+=1; rid=self.seq
        self.send({'id':rid,'method':method,'params':{} if params is None else params})
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            if rid in self.replies: m=self.replies.pop(rid)
            else: m=self._get(max(.001,end-time.monotonic()))
            if m is None: break
            if m.get('id')==rid:
                if 'error' in m: raise RpcError(f'{method}: '+json.dumps(m['error'],ensure_ascii=False)[:1000])
                if 'result' not in m: raise RpcError('Missing RPC result')
                return m['result']
            if 'id' in m: self.replies[m['id']]=m
            else:
                if len(self.events)>=1000: raise LostConnection('Too many pending notifications')
                self.events.append(m)
        raise LostConnection('RPC timed out: '+method)
    def notification(self,timeout=1):
        if self.events: return self.events.popleft()
        m=self._get(timeout)
        if m is not None and 'id' in m:
            self.replies[m['id']]=m; return None
        return m
    def close(self):
        if self.closed: return
        self.closed=True
        if self.proc.poll() is None:
            self.proc.terminate()
            try: self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill(); self.proc.wait(timeout=3)
        for f in [self.proc.stdin,self.proc.stdout]:
            try: f.close()
            except (OSError,ValueError): pass
        self.reader.join(timeout=1)

class CodexAdapter:
    def __init__(self,argv,cwd,stderr=None):
        self.argv=argv; self.cwd=cwd; self.stderr=stderr; self.rpc=None
        self.account_type=None; self.active_turn=None; self.thread_id=None
    def connect(self):
        self.rpc=JsonRpc(self.argv,self.cwd,self.stderr)
        self.rpc.request('initialize',{'clientInfo':{'name':'continuous_development_watch','title':'Continuous Development Watch','version':'1.0.0'}})
        self.rpc.send({'method':'initialized','params':{}})
        account=self.rpc.request('account/read',{'refreshToken':False}).get('account')
        self.account_type=account.get('type') if isinstance(account,dict) else None
        if self.account_type!='chatgpt':
            raise NeedUser('A ChatGPT-backed Codex login is required; no API-key fallback')
    def read_quota(self,threshold):
        return quota_gate(self.rpc.request('account/rateLimits/read'),threshold)
    def ensure_thread(self,thread_id):
        if thread_id:
            r=self.rpc.request('thread/resume',{'threadId':thread_id,'cwd':self.cwd})
        else:
            r=self.rpc.request('thread/start',{'cwd':self.cwd,'approvalPolicy':'on-request','sandbox':'workspaceWrite','modelProvider':'openai'})
        t=r.get('thread',{}); tid=t.get('id')
        if not isinstance(tid,str) or not tid: raise NeedUser('No thread id returned')
        if thread_id and tid!=thread_id: raise NeedUser('Resume returned a different thread')
        st=t.get('status',{})
        if isinstance(st,dict) and st.get('type')=='active': raise NeedUser('Thread is already active; will not duplicate it')
        if t.get('cwd') and os.path.realpath(t['cwd'])!=os.path.realpath(self.cwd):
            raise NeedUser('Thread belongs to another working directory')
        self.thread_id=tid
        return tid
    def interrupt(self):
        if not self.active_turn or not self.thread_id: return
        try:
            self.rpc.request('turn/interrupt',{'threadId':self.thread_id,'turnId':self.active_turn},timeout=10)
        except (RpcError,LostConnection,NeedUser): pass
    def run_turn(self,thread_id,prompt,threshold,should_stop,on_state,skill_path=None):
        self.thread_id=thread_id
        inputs=[{'type':'text','text':prompt}]
        if skill_path: inputs.append({'type':'skill','name':'continuous-development','path':str(skill_path)})
        r=self.rpc.request('turn/start',{
            'threadId':thread_id,'input':inputs,'cwd':self.cwd,
            'approvalPolicy':'on-request',
            'sandboxPolicy':{'type':'workspaceWrite','writableRoots':[self.cwd],'networkAccess':False},
            'outputSchema':REPORT_SCHEMA,
        })
        turn=r.get('turn',{}); self.active_turn=turn.get('id')
        if not self.active_turn: raise NeedUser('No active turn id returned')
        on_state('running',self.active_turn)
        text=None; last_check=time.monotonic(); stop_reason=None; stop_deadline=None
        try:
            while True:
                if stop_reason is None and should_stop():
                    stop_reason='manual'; self.interrupt(); stop_deadline=time.monotonic()+15
                if time.monotonic()-last_check>=60 and stop_reason is None:
                    q=self.read_quota(threshold); last_check=time.monotonic()
                    if q['status']!='ok':
                        stop_reason='quota'; self.interrupt(); stop_deadline=time.monotonic()+15
                if stop_deadline and time.monotonic()>stop_deadline:
                    raise NeedUser('Interruption not confirmed; reconcile this turn before restarting')
                m=self.rpc.notification(timeout=.25)
                if m is None: continue
                method=m.get('method'); p=m.get('params',{})
                if method=='account/rateLimits/updated':
                    if quota_gate(p,threshold)['status']!='ok' and stop_reason is None:
                        stop_reason='quota'; self.interrupt(); stop_deadline=time.monotonic()+15
                    continue
                if method=='account/updated' and p.get('authMode') not in {'chatgpt','chatgptAuthTokens'}:
                    raise NeedUser('Account auth mode changed; explicit recheck required')
                if p.get('threadId') not in {None,thread_id}: continue
                if method=='item/completed':
                    if p.get('turnId') not in {None,self.active_turn}: continue
                    item=p.get('item',{})
                    if item.get('type')=='agentMessage' and item.get('phase') in {None,'final_answer'}:
                        text=item.get('text')
                if method!='turn/completed': continue
                end=p.get('turn',{})
                if end.get('id')!=self.active_turn: continue
                self.active_turn=None; on_state('turn_terminal',None)
                if stop_reason=='manual': raise NeedUser('User stopped the watcher')
                if stop_reason=='quota': raise QuotaPause('Allowance unavailable or below threshold')
                status=end.get('status')
                if status=='interrupted': raise NeedUser('Turn was interrupted; automatic restart suppressed')
                if status=='failed': raise TerminalFailure(end.get('error',{}))
                if status!='completed': raise NeedUser('Unknown terminal turn status')
                if text is None:
                    for i in end.get('items',[]):
                        if i.get('type')=='agentMessage': text=i.get('text')
                try: return validate_report(text)
                except ValueError as e: raise NeedUser(str(e)) from e
        except NeedUser:
            self.interrupt()
            raise
    def close(self):
        if self.rpc: self.rpc.close()
