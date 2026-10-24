import importlib.util
import math
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import lifecycle_policy as p

class CommandTests(unittest.TestCase):
    def test_sessions_defaults(self):
        q = p.parse_lifecycle('@continuous-development sessions()')
        self.assertEqual(q['params']['initial'], 20)
        self.assertEqual(q['params']['limit'], 15)
        self.assertEqual(q['params']['rounds'], 15)
        self.assertFalse(q['read_only'])
    def test_sessions_keywords(self):
        q = p.parse_lifecycle('$continuous-development sessions(initial=25, limit=10, rounds=30)')
        self.assertEqual(q['params'], {'initial':25, 'limit':10, 'rounds':30, 'scope':'host'})
    def test_sessions_all(self):
        self.assertEqual(p.parse_lifecycle('sessions(initial="all")')['params']['initial'], 'all')
    def test_sessions_stop(self):
        self.assertEqual(p.parse_lifecycle('sessions("stop")')['action'], 'stop')
    def test_sessions_status_readonly(self):
        self.assertTrue(p.parse_lifecycle('sessions("status")')['read_only'])
    def test_open_current(self):
        q = p.parse_lifecycle('@continuous-development open()')
        self.assertTrue(q['read_only'])
        self.assertIsNone(q['params']['target'])
    def test_open_named_target(self):
        self.assertEqual(p.parse_lifecycle('open("Rust 项目")')['params']['target'], 'Rust 项目')
    def test_open_bare_identifier(self):
        self.assertEqual(p.parse_lifecycle('open(project_a)')['params']['target'], 'project_a')
    def test_open_url(self):
        link = 'codex://threads/01a16dcd-a970-7232-a17f-4fe891230c55'
        self.assertEqual(p.parse_lifecycle(f'open("{link}")')['params']['target'], link)
    def test_handoff_is_not_help(self):
        self.assertEqual(p.parse_lifecycle('@continuous-development handoff()')['command'], 'handoff')
    def test_sync_defaults(self):
        q = p.parse_lifecycle('sync()')
        self.assertEqual(q['params']['interval_seconds'], 300)
        self.assertEqual(q['params']['threshold'], 1)
        self.assertEqual(q['params']['on_low'], 'checkpoint-push-pause')
    def test_sync_keywords(self):
        q = p.parse_lifecycle('sync(every="10m", threshold=3, remotes=["github","gitee"])')
        self.assertEqual(q['params']['interval_seconds'], 600)
        self.assertEqual(q['params']['remotes'], ['github','gitee'])
    def test_sync_stop(self):
        self.assertEqual(p.parse_lifecycle('sync("stop")')['action'], 'stop')
    def test_old_command_unclaimed(self):
        for x in ['always()', 'run(2h)', 'help', 'Sub-agent(a,b)', '$continuous-development', 'always() Sub-agent(a)']:
            with self.subTest(x=x): self.assertIsNone(p.parse_lifecycle(x))
    def test_objective_literal_separator_in_quote(self):
        q = p.parse_lifecycle('open("project -- release")')
        self.assertEqual(q['params']['target'], 'project -- release')
    def test_sessions_objective(self):
        q = p.parse_lifecycle('sessions() -- 先完成已排队任务')
        self.assertEqual(q['objective'], '先完成已排队任务')
    def test_readonly_no_objective(self):
        with self.assertRaises(ValueError): p.parse_lifecycle('open() -- 修改代码')
    def test_reject_unknown_keyword(self):
        with self.assertRaises(ValueError): p.parse_lifecycle('sessions(limt=15)')
    def test_reject_zero_negative_float_and_bool_counts(self):
        for x in ['0','-1','1.5','True']:
            with self.subTest(x=x), self.assertRaises(ValueError): p.parse_lifecycle(f'sessions(limit={x})')
    def test_reject_missing_parentheses(self):
        with self.assertRaises(ValueError): p.parse_lifecycle('sessions initial=20')
    def test_reject_bad_threshold(self):
        for v in ['-1', '101', 'True', '1e999']:
            with self.subTest(v=v), self.assertRaises(ValueError): p.parse_lifecycle(f'sync(threshold={v})')
    def test_reject_unsupported_interval(self):
        for v in ['1s', '0m', '-5m', 'five minutes']:
            with self.subTest(v=v), self.assertRaises(ValueError): p.parse_lifecycle(f'sync(every="{v}")')
    def test_reject_code_execution(self):
        for x in ['open(__import__("os").getcwd())', 'sessions(**dict(limit=15))', 'sync(remotes=[x for x in []])', 'open((1).__class__)', 'open("a"); print(123)']:
            with self.subTest(x=x), self.assertRaises(ValueError): p.parse_lifecycle(x)
    def test_reject_chained_lifecycle_commands(self):
        with self.assertRaises(ValueError): p.parse_lifecycle('sessions() sync()')
    def test_reject_duplicate_parameters(self):
        with self.assertRaises(ValueError): p.parse_lifecycle('sync(threshold=1, threshold=2)')
    def test_unhashable_values_are_controlled_errors(self):
        for x in ['sessions([])', 'sessions(scope=[])', 'sync(on_low={})']:
            with self.subTest(x=x), self.assertRaises(ValueError): p.parse_lifecycle(x)
    def test_remote_name_validation(self):
        for x in ['sync(remotes=["-evil"])', 'sync(remotes=["https://example.com/repo"])', 'sync(remotes=[])']:
            with self.subTest(x=x), self.assertRaises(ValueError): p.parse_lifecycle(x)
    def test_no_input_side_effects(self):
        q = p.parse_lifecycle('sync(every="5m")')
        self.assertEqual(q['execution'], 'not_executed')
    def test_cli_output(self):
        r = subprocess.run([sys.executable, str(ROOT/'scripts/lifecycle_policy.py'), 'open()'], capture_output=True,text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn('not_executed', r.stdout)

class PolicyTests(unittest.TestCase):
    def test_twenty_existing_no_new(self):
        self.assertEqual(p.admission_budget(20, pending_requests=20)['allowed'], 0)
    def test_fourteen_allows_one(self):
        self.assertEqual(p.admission_budget(14, pending_requests=10)['allowed'], 1)
    def test_ten_archived_allows_ten(self):
        self.assertEqual(p.admission_budget(5, pending_requests=10)['allowed'], 10)
    def test_reservations_count(self):
        self.assertEqual(p.admission_budget(14, reservations=1, pending_requests=10)['allowed'], 0)
    def test_initial_drain_barrier(self):
        self.assertEqual(p.admission_budget(5, initial_remaining=1, pending_requests=10)['allowed'], 0)
    def test_incomplete_inventory(self):
        self.assertEqual(p.admission_budget(4, inventory_complete=False)['allowed'], 0)
    def test_unknown_count(self):
        self.assertEqual(p.admission_budget(None)['allowed'], 0)
    def test_no_backlog_no_empty_churn(self):
        self.assertEqual(p.admission_budget(0, pending_requests=0)['allowed'], 0)
    def test_round_fifteen_not_task_done(self):
        self.assertEqual(p.rollover_decision(15, task_done=False), 'drain_current_task')
    def test_busy_task_wait(self):
        self.assertEqual(p.rollover_decision(15, task_done=True, busy=True), 'wait_safe_boundary')
    def test_children_wait(self):
        self.assertEqual(p.rollover_decision(20, task_done=True, children_busy=True), 'wait_safe_boundary')
    def test_finished_needs_handoff(self):
        self.assertEqual(p.rollover_decision(3, task_done=True), 'save_handoff')
    def test_no_adapter_no_archive(self):
        self.assertEqual(p.rollover_decision(15, task_done=True, checkpoint_ok=True), 'blocked_capability')
    def test_archive_ready_only(self):
        self.assertEqual(p.rollover_decision(15, task_done=True, checkpoint_ok=True, can_archive=True, can_create=True), 'archive_ready')
    def test_quota_converts_used_to_remaining(self):
        self.assertEqual(p.quota_decision([99], observed_age_seconds=1)['remaining_percent'],1)
    def test_quota_inclusive(self):
        self.assertEqual(p.quota_decision([99], observed_age_seconds=1)['decision'],'checkpoint_push_pause')
    def test_quota_multiple_buckets(self):
        self.assertEqual(p.quota_decision([50,99.5], observed_age_seconds=1)['remaining_percent'],0.5)
    def test_quota_stale_is_unknown(self):
        self.assertEqual(p.quota_decision([1], observed_age_seconds=121)['decision'],'unknown_pause_new_work')
    def test_quota_empty_is_unknown(self):
        self.assertEqual(p.quota_decision([], observed_age_seconds=0)['remaining_percent'],None)
    def test_quota_partial_unknown_is_unknown(self):
        self.assertEqual(p.quota_decision([20,None], observed_age_seconds=0)['decision'],'unknown_pause_new_work')
    def test_quota_resume_hysteresis(self):
        self.assertEqual(p.quota_decision([98.5], observed_age_seconds=0, paused=True)['decision'],'remain_paused')
        self.assertEqual(p.quota_decision([97], observed_age_seconds=0, paused=True)['decision'],'eligible_to_resume')
    def test_no_tasks_progress_unknown(self):
        self.assertIsNone(p.progress_summary([])['percent'])
    def test_progress_requires_acceptance(self):
        q=p.progress_summary([{'id':'a','status':'done','accepted':True},{'id':'b','status':'done','accepted':False}])
        self.assertEqual(q['percent'],50)
    def test_progress_weighted(self):
        q=p.progress_summary([{'id':'a','status':'done','accepted':True,'weight':1},{'id':'b','status':'in_progress','weight':3}])
        self.assertEqual(q['percent'],25)
    def test_progress_duplicate_ids_invalid(self):
        with self.assertRaises(ValueError): p.progress_summary([{'id':'a'},{'id':'a'}])

if __name__ == '__main__': unittest.main()
