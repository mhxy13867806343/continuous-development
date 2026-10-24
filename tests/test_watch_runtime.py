import json, os, sys, subprocess, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import watch_runtime as w
from watch_rpc import CodexAdapter
FIX=Path(__file__).parent/'fixtures'/'fake_app_server.py'

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name).resolve(); self.repo=self.base/'repo'; self.repo.mkdir()
        for cmd in [['git','init','-q'],['git','config','user.name','Test'],['git','config','user.email','test@example.invalid']]:
            subprocess.run(cmd,cwd=self.repo,check=True,stdout=subprocess.DEVNULL)
        (self.repo/'file.txt').write_text('initial')
        subprocess.run(['git','add','file.txt'],cwd=self.repo,check=True)
        subprocess.run(['git','commit','-qm','initial'],cwd=self.repo,check=True)
        self.job=self.base/'private'/'job'; self.job.mkdir(parents=True)
    def init(self,scenario='done'):
        workspace,branch=w.prepare_workspace(self.repo,self.job)
        config={'project':str(self.repo),'workspace':str(workspace),'branch':branch,'every_seconds':1,
                'retry':2,'threshold':1,'objective':'Test fixture only','codex':'/not-used',
                'skill_path':str(Path(__file__).resolve().parents[1]/'SKILL.md')}
        w.atomic_json(self.job/'config.json',config)
        w.atomic_json(self.job/'control.json',{'enabled':True})
        def factory(argv,cwd): return CodexAdapter([sys.executable,str(FIX),scenario],cwd)
        return factory
    def test_worktree_source_preserved(self):
        workspace,branch=w.prepare_workspace(self.repo,self.job)
        self.assertTrue((workspace/'file.txt').exists()); self.assertTrue(branch.startswith('cd-watch/'))
        self.assertEqual(subprocess.check_output(['git','status','--porcelain'],cwd=self.repo),b'')
    def test_dirty_repo_refused(self):
        (self.repo/'file.txt').write_text('user edit')
        with self.assertRaises(ValueError): w.prepare_workspace(self.repo,self.job)
        self.assertEqual((self.repo/'file.txt').read_text(),'user edit')
    def test_atomic_private_file(self):
        w.atomic_json(self.job/'x.json',{'enabled':False})
        self.assertEqual(w.read_json(self.job/'x.json',{}),{'enabled':False})
        self.assertEqual((self.job/'x.json').stat().st_mode & 0o777,0o600)
    def test_lock(self):
        with w.job_lock(self.job/'worker.lock'):
            self.assertTrue(w.is_locked(self.job/'worker.lock'))
        self.assertFalse(w.is_locked(self.job/'worker.lock'))
    def test_job_identity(self): self.assertEqual(w.project_info(self.repo)['id'],w.project_info(self.repo/'.')['id'])
    def test_plist(self):
        self.init(); p=w.launch_agent(self.job,'test.label')
        self.assertEqual(p['KeepAlive'],{'SuccessfulExit':False}); self.assertEqual(p['WorkingDirectory'],str(self.job))
        self.assertNotIn('OPENAI_API_KEY',p['EnvironmentVariables'])
    def test_done(self):
        factory=self.init(); w.run_job(self.job,adapter_factory=factory,sleep_fn=lambda *_:None,max_cycles=2)
        s=w.read_json(self.job/'state.json',{}); self.assertEqual(s['phase'],'done'); self.assertEqual(s['rounds_completed'],1)
    def test_stopped_no_restart(self):
        factory=self.init(); w.atomic_json(self.job/'control.json',{'enabled':False})
        w.run_job(self.job,adapter_factory=lambda *_:self.fail('must not connect'),sleep_fn=lambda *_:None,max_cycles=1)
        self.assertEqual(w.read_json(self.job/'state.json',{})['phase'],'stopped')
    def test_quota_no_model(self):
        factory=self.init('quota'); w.run_job(self.job,adapter_factory=factory,sleep_fn=lambda *_:None,max_cycles=1)
        s=w.read_json(self.job/'state.json',{}); self.assertEqual(s['phase'],'quota_wait'); self.assertIsNone(s.get('thread_id'))
    def test_retry_cap(self):
        factory=self.init('transient'); w.run_job(self.job,adapter_factory=factory,sleep_fn=lambda *_:None,max_cycles=5)
        s=w.read_json(self.job/'state.json',{}); self.assertEqual(s['phase'],'needs_user'); self.assertEqual(s['failure_count'],3)
    def test_unknown_disconnect_no_blind_retry(self):
        factory=self.init('disconnect'); w.run_job(self.job,adapter_factory=factory,sleep_fn=lambda *_:None,max_cycles=3)
        self.assertEqual(w.read_json(self.job/'state.json',{})['phase'],'ambiguous')
    def test_active_snapshot_not_restarted(self):
        self.init(); w.atomic_json(self.job/'state.json',{'phase':'running','active_turn':'turn-old'})
        w.run_job(self.job,adapter_factory=lambda *_:self.fail('must not reconnect'),sleep_fn=lambda *_:None,max_cycles=1)
        self.assertEqual(w.read_json(self.job/'state.json',{})['phase'],'ambiguous')
    def test_invalid_report_pauses(self):
        factory=self.init('invalid'); w.run_job(self.job,adapter_factory=factory,sleep_fn=lambda *_:None,max_cycles=2)
        self.assertEqual(w.read_json(self.job/'state.json',{})['phase'],'needs_user')
    def test_interrupted_pauses(self):
        factory=self.init('interrupted'); w.run_job(self.job,adapter_factory=factory,sleep_fn=lambda *_:None,max_cycles=2)
        self.assertEqual(w.read_json(self.job/'state.json',{})['phase'],'needs_user')
    def test_no_progress_guard(self):
        factory=self.init('continue'); w.run_job(self.job,adapter_factory=factory,sleep_fn=lambda *_:None,max_cycles=5)
        s=w.read_json(self.job/'state.json',{}); self.assertEqual(s['phase'],'needs_user'); self.assertEqual(s['no_change_count'],3)
    def test_terminal_state_not_reopened(self):
        self.init(); w.atomic_json(self.job/'state.json',{'phase':'done','active_turn':None})
        w.run_job(self.job,adapter_factory=lambda *_:self.fail('must not reconnect'),sleep_fn=lambda *_:None,max_cycles=1)
        self.assertEqual(w.read_json(self.job/'state.json',{})['phase'],'done')

if __name__=='__main__': unittest.main()

class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name).resolve(); self.repo=self.base/'repo'; self.repo.mkdir()
        subprocess.run(['git','init','-q'],cwd=self.repo,check=True)
        self.home=self.base/'private-home'
        self.patch=patch.dict(os.environ,{'CODEX_HOME':str(self.home)})
        self.patch.start(); self.addCleanup(self.patch.stop)
    def test_preview_no_writes(self):
        result=w.dispatch('watch()',self.repo,False)
        self.assertEqual(result['execution'],'not_executed'); self.assertFalse(self.home.exists())
    def test_status_without_install_no_writes(self):
        result=w.dispatch('watch("status")',self.repo)
        self.assertFalse(result['enabled']); self.assertFalse(self.home.exists())
    def test_help_without_repo(self):
        self.assertIn('watch()', w.dispatch('help watch','/does/not/exist')['methods'])
    def test_unsupported_platform_fail_closed(self):
        with patch.object(sys,'platform','linux'), self.assertRaises(ValueError): w.dispatch('watch()',self.repo,True)
        self.assertFalse(self.home.exists())
    def test_recursive_enable_blocked(self):
        with patch.dict(os.environ,{'CONTINUOUS_WATCH_WORKER':'1'}), self.assertRaises(ValueError):
            w.dispatch('watch()',self.repo,True)
    def test_no_reserved_chain(self):
        from parse_invocation import InvocationParser
        with self.assertRaises(ValueError): InvocationParser().parse('always() watch()')
