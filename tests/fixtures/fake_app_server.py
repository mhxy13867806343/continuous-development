"""Protocol-only fixture. No real model, credentials, network or launchd."""
import json, sys
scenario=sys.argv[1] if len(sys.argv)>1 else 'done'
turns=0

def send(x): print(json.dumps(x),flush=True)
for line in sys.stdin:
    m=json.loads(line)
    if 'method' not in m: continue
    method=m['method']; rid=m.get('id'); p=m.get('params',{})
    if rid is None: continue
    result={}
    if method=='initialize': result={'userAgent':'fake-test-only'}
    elif method=='account/read': result={'account':{'type':'apiKey' if scenario=='apikey' else 'chatgpt'}}
    elif method=='account/rateLimits/read':
        result={'rateLimits':{'primary':{'usedPercent':100 if scenario=='quota' else 20},'secondary':None}}
    elif method in ['thread/start','thread/resume']:
        result={'thread':{'id':p.get('threadId','owned-test-thread'),'cwd':p.get('cwd'),'status':{'type':'idle'}}}
    elif method=='turn/start':
        turns+=1
        tid=f'turn-{turns}'
        result={'turn':{'id':tid,'status':'inProgress'}}
        if scenario=='out_of_order':
            send({'method':'item/completed','params':{'threadId':'wrong-thread','turnId':tid,'item':{'type':'agentMessage','text':'not ours'}}})
        send({'id':rid,'result':result})
        if scenario=='approval':
            send({'id':9876,'method':'item/commandExecution/requestApproval','params':{'threadId':p['threadId'],'turnId':tid}})
            continue
        if scenario=='disconnect': sys.exit(0)
        if scenario=='quota_midturn':
            send({'method':'account/rateLimits/updated','params':{'rateLimits':{'primary':{'usedPercent':100},'secondary':None}}})
            continue
        if scenario=='hold': continue
        if scenario=='transient':
            send({'method':'turn/completed','params':{'threadId':p['threadId'],'turn':{'id':tid,'status':'failed','error':{'codexErrorInfo':'responseStreamDisconnected','message':'test disconnected'}}}})
            continue
        if scenario=='interrupted':
            send({'method':'turn/completed','params':{'threadId':p['threadId'],'turn':{'id':tid,'status':'interrupted'}}})
            continue
        state='continue' if scenario=='continue' else 'done'
        report={'state':state,'summary':'fixture only','next_task':'next item' if state=='continue' else '', 'progress_made':True,'evidence':['fixture assertion']}
        text='BAD' if scenario=='invalid' else json.dumps(report)
        send({'method':'item/completed','params':{'threadId':p['threadId'],'turnId':tid,'item':{'type':'agentMessage','text':text,'phase':'final_answer'}}})
        send({'method':'turn/completed','params':{'threadId':p['threadId'],'turn':{'id':tid,'status':'completed'}}})
        continue
    elif method=='turn/interrupt':
        send({'id':rid,'result':{}})
        send({'method':'turn/completed','params':{'threadId':p['threadId'],'turn':{'id':p['turnId'],'status':'interrupted'}}})
        continue
    send({'id':rid,'result':result})
