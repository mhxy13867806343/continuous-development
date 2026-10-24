import json
import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from watch_policy import parse_watch, quota_gate, retry_delay, classify_failure, validate_report

class WatchParserTests(unittest.TestCase):
    def test_default(self):
        p=parse_watch('@continuous-development watch()')
        self.assertEqual(p['action'],'start'); self.assertEqual(p['params']['every_seconds'],60)
        self.assertEqual(p['params']['retry'],3); self.assertEqual(p['params']['threshold'],1)
        self.assertEqual(p['execution'],'not_executed')
    def test_parameters(self):
        p=parse_watch('$continuous-development watch(every="30s", retry=2, threshold=5) -- 修复已有错误')
        self.assertEqual(p['params']['every_seconds'],30); self.assertEqual(p['objective'],'修复已有错误')
    def test_actions(self):
        for action in ['status','doctor','stop','resume']:
            with self.subTest(action=action): self.assertEqual(parse_watch(f'watch("{action}")')['action'],action)
    def test_help(self):
        self.assertEqual(parse_watch('@continuous-development help watch')['action'],'help')
    def test_mixed_watch_must_not_fall_back(self):
        for s in ['always() watch()', 'always()+watch()', 'lambda(watch())']:
            with self.subTest(s=s), self.assertRaises(ValueError): parse_watch(s)
    def test_watch_inside_quoted_text_is_not_a_call(self):
        self.assertIsNone(parse_watch('open("watch()")'))
    def test_not_ours(self):
        for s in ['open()', 'always()', 'Sub-agent(a)', 'sync("status")']:
            self.assertIsNone(parse_watch(s))
    def test_reject_bad(self):
        for s in ['watch(x=1)','watch("delete")','watch(retry=-1)','watch(retry=True)',
                  'watch(threshold=100)','watch(every="0s")','watch(every="-1s")',
                  'watch(every="30d")','watch(retry=3.5)','watch(retry=100)',
                  'watch(__import__("os"))','watch() run()','watch("stop") -- do work',
                  'watch("status", retry=1)','watch(foo.bar)','watch(**{})']:
            with self.subTest(s=s), self.assertRaises(ValueError): parse_watch(s)
    def test_subseconds_not_allowed(self):
        with self.assertRaises(ValueError): parse_watch('watch(every="0.1s")')
    def test_h_never_steals_threshold(self):
        from parse_invocation import InvocationParser
        self.assertEqual(InvocationParser().parse('watch(threshold=1)')['command'],'watch')

class QuotaTests(unittest.TestCase):
    def sample(self, used): return {'rateLimits':{'limitId':'codex','primary':{'usedPercent':used},'secondary':None}}
    def test_normal(self): self.assertEqual(quota_gate(self.sample(50),1)['status'],'ok')
    def test_boundary(self): self.assertEqual(quota_gate(self.sample(99),1)['status'],'low')
    def test_multiple(self):
        d=self.sample(50); d['rateLimits']['secondary']={'usedPercent':100}
        self.assertEqual(quota_gate(d,1)['remaining'],0)
    def test_unknown(self):
        for x in [{},{'rateLimits':None},self.sample(None),self.sample('99'),self.sample(float('nan'))]:
            self.assertEqual(quota_gate(x,1)['status'],'unknown')
    def test_reset_not_assumed(self):
        d=self.sample(100); d['rateLimits']['primary']['resetsAt']=1
        self.assertEqual(quota_gate(d,1)['status'],'low')
    def test_reached(self):
        d=self.sample(50); d['rateLimits']['rateLimitReachedType']='weekly'
        self.assertEqual(quota_gate(d,1)['status'],'low')
    def test_multi_bucket(self):
        d={'rateLimitsByLimitId':{'codex':self.sample(98)['rateLimits'],'other':self.sample(100)['rateLimits']}}
        self.assertEqual(quota_gate(d,1)['status'],'low')

class RecoveryTests(unittest.TestCase):
    def test_backoff(self): self.assertEqual([retry_delay(i,60) for i in [1,2,3]], [60,120,240])
    def test_unknown_errors_pause(self): self.assertEqual(classify_failure({'message':'something stopped'}),'needs_user')
    def test_no_text_matching_for_quota(self): self.assertEqual(classify_failure({'message':'quota maybe'}),'needs_user')
    def test_network(self): self.assertEqual(classify_failure({'codexErrorInfo':'responseStreamDisconnected'}),'retry')
    def test_limit(self): self.assertEqual(classify_failure({'codexErrorInfo':'usageLimitExceeded'}),'quota')
    def test_report(self):
        p={'state':'continue','summary':'fix','next_task':'run tests','progress_made':True,'evidence':['tests passed']}
        self.assertEqual(validate_report(json.dumps(p))['state'],'continue')
    def test_invalid_report(self):
        for p in ['all done','{}', json.dumps({'state':'continue','summary':'x','next_task':'','progress_made':False,'evidence':[]})]:
            with self.assertRaises(ValueError): validate_report(p)

if __name__=='__main__': unittest.main()
