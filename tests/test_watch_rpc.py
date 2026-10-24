import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from watch_rpc import JsonRpc, CodexAdapter, NeedUser, LostConnection, QuotaPause, TerminalFailure
FIX=Path(__file__).parent/'fixtures'/'fake_app_server.py'

class ProtocolTests(unittest.TestCase):
    def adapter(self,scenario):
        a=CodexAdapter([sys.executable,str(FIX),scenario],str(Path.cwd()))
        self.addCleanup(a.close)
        a.connect()
        return a
    def test_handshake(self):
        a=self.adapter('done'); self.assertEqual(a.account_type,'chatgpt')
    def test_quota(self): self.assertEqual(self.adapter('quota').read_quota(1)['status'],'low')
    def test_no_apikey_fallback(self):
        with self.assertRaises(NeedUser): self.adapter('apikey')
    def test_thread_and_report(self):
        a=self.adapter('done'); t=a.ensure_thread(None)
        result=a.run_turn(t,'fixture task',1,lambda:False,lambda *_:None)
        self.assertEqual(result['state'],'done')
    def test_resume_exact_thread(self):
        a=self.adapter('done'); self.assertEqual(a.ensure_thread('owned-test-thread'),'owned-test-thread')
    def test_continue(self):
        a=self.adapter('continue'); t=a.ensure_thread(None)
        self.assertEqual(a.run_turn(t,'fixture',1,lambda:False,lambda *_:None)['state'],'continue')
    def test_invalid_report_pauses(self):
        a=self.adapter('invalid'); t=a.ensure_thread(None)
        with self.assertRaises(NeedUser): a.run_turn(t,'fixture',1,lambda:False,lambda *_:None)
    def test_approval_never_granted(self):
        a=self.adapter('approval'); t=a.ensure_thread(None)
        with self.assertRaises(NeedUser): a.run_turn(t,'fixture',1,lambda:False,lambda *_:None)
    def test_disconnect_is_ambiguous(self):
        a=self.adapter('disconnect'); t=a.ensure_thread(None)
        with self.assertRaises(LostConnection): a.run_turn(t,'fixture',1,lambda:False,lambda *_:None)
    def test_transient_terminal_failure(self):
        a=self.adapter('transient'); t=a.ensure_thread(None)
        with self.assertRaises(TerminalFailure) as c: a.run_turn(t,'fixture',1,lambda:False,lambda *_:None)
        self.assertEqual(c.exception.policy,'retry')
    def test_user_interruption_pauses(self):
        a=self.adapter('interrupted'); t=a.ensure_thread(None)
        with self.assertRaises(NeedUser): a.run_turn(t,'fixture',1,lambda:False,lambda *_:None)
    def test_foreign_thread_ignored(self):
        a=self.adapter('out_of_order'); t=a.ensure_thread(None)
        self.assertEqual(a.run_turn(t,'fixture',1,lambda:False,lambda *_:None)['state'],'done')
    def test_quota_midturn_interrupt(self):
        a=self.adapter('quota_midturn'); t=a.ensure_thread(None)
        with self.assertRaises(QuotaPause): a.run_turn(t,'fixture',1,lambda:False,lambda *_:None)
    def test_stop_during_turn(self):
        a=self.adapter('hold'); t=a.ensure_thread(None)
        calls=[0]
        def stopping(): calls[0]+=1; return calls[0]>1
        with self.assertRaises(NeedUser): a.run_turn(t,'fixture',1,stopping,lambda *_:None)

if __name__=='__main__': unittest.main()
