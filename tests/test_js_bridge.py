import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from js_command_bridge import parse_js

class JSBridgeTests(unittest.TestCase):
    def test_bare_prefix_readonly(self):
        r=parse_js('@continuous-development a')
        self.assertTrue(r['read_only']); self.assertEqual(r['execution'],'not_executed')
    def test_alias_goals(self):
        r=parse_js('@continuous-development a("修复登录","测试")')
        self.assertEqual([s['intent']['objective'] for s in r['steps']],['修复登录','测试'])
    def test_alias_status(self):
        self.assertTrue(parse_js('@continuous-development b()')['read_only'])
    def test_alias_open(self):
        self.assertEqual(parse_js('@continuous-development c("ecom")')['steps'][0]['intent']['params']['target'],'ecom')
    def test_auto_normalizes_to_existing_policy(self):
        r=parse_js('@continuous-development auto()')
        self.assertEqual(r['steps'][0]['intent']['params']['every_seconds'],60)
    def test_bad_watch_retry(self):
        with self.assertRaises(ValueError):parse_js('@continuous-development watch({retry:999})')
    def test_bad_watch_threshold(self):
        with self.assertRaises(ValueError):parse_js('@continuous-development auto("60s",101)')
    def test_native_python_untouched(self):
        self.assertIsNone(parse_js('@continuous-development watch(every="60s", retry=3)'))
    def test_old_list_pipeline_untouched(self):
        self.assertIsNone(parse_js('@continuous-development[a,b,c(),d(1)]'))
    def test_help_untouched(self):
        self.assertIsNone(parse_js('@continuous-development help Sub-agent'))
    def test_incomplete_args(self):
        r=parse_js('@continuous-development a("x",')
        self.assertEqual(r['signature']['activeParameter'],1)
    def test_preview_not_saved(self):
        r=parse_js('@continuous-development const foo=()=>status();')
        self.assertFalse(r['registered'])
    def test_suggest(self):
        r=parse_js('@continuous-development suggest("wa")')
        self.assertEqual(r['items'][0]['name'],'watch')
    def test_invalid_js_never_falls_through(self):
        with self.assertRaises(ValueError):parse_js('@continuous-development const x=()=>process.exit();')
    def test_closed_unknown_stays_legacy(self):
        self.assertIsNone(parse_js('@continuous-development other(1)'))
    def test_no_objective_on_readonly_alias(self):
        with self.assertRaises(ValueError):parse_js('@continuous-development b() -- 修改代码')
    def test_task_can_carry_objective(self):
        r=parse_js('@continuous-development a("x","y") -- 不提交')
        self.assertEqual(r['objective'],'不提交')

if __name__=='__main__': unittest.main()
