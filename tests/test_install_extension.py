from pathlib import Path
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('installer',ROOT/'install_extension.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

FIXTURE={
'SKILL.md':'---\nname: continuous-development\ndescription: Use current skill\n---\n9. `subagents.md`\n\n## Command routing takes precedence\nold\n',
'invocation.md':'# Invocation\n\n## Supported commands\nold\n',
'orchestration.md':'# Orchestration\n\n## Dynamic workstreams\nold\n',
'quota-safety.md':'# Quota\n\n## Usage / quota rules\nold\n',
'git.md':'# Git\n\n## Review before commit\nold\n',
'documentation.md':'# Documentation\n\n## Discover existing conventions\nold\n',
'README.md':'# User README\nDo not lose this.\n',
'scripts/parse_invocation.py':'''import json
import sys
class InvocationParser:
    def parse(self, raw_input: str) -> dict:
        return {"legacy":raw_input}
def main():
    parser = InvocationParser()
    if len(sys.argv)>1:
        expr = " ".join(sys.argv[1:])
        result = parser.parse(expr)
        print(json.dumps(result))
if __name__ == '__main__': main()
'''
}

class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.target=self.root/'skill';self.target.mkdir()
        for name,text in FIXTURE.items():
            p=self.target/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
    def tearDown(self): self.tmp.cleanup()
    def test_dry_run_no_write(self):
        out=m.install(self.target)
        self.assertGreater(len(out['changes']),0)
        self.assertFalse((self.target/'session-lifecycle.md').exists())
        self.assertEqual((self.target/'SKILL.md').read_text(),FIXTURE['SKILL.md'])
    def test_apply_backups_and_preservation(self):
        out=m.install(self.target,True,self.root/'backups')
        self.assertEqual((Path(out['backup'])/'SKILL.md').read_text(),FIXTURE['SKILL.md'])
        self.assertIn('Do not lose this.',(self.target/'README.md').read_text())
        self.assertTrue((self.target/'scripts/lifecycle_policy.py').exists())
    def test_idempotent(self):
        m.install(self.target,True,self.root/'backups')
        self.assertEqual(m.install(self.target,True,self.root/'backups')['changes'],[])
    def test_new_file_conflict_blocks_all(self):
        (self.target/'handoff.md').write_text('user modification')
        with self.assertRaises(ValueError):m.install(self.target,True,self.root/'backups')
        self.assertEqual((self.target/'SKILL.md').read_text(),FIXTURE['SKILL.md'])
    def test_ambiguous_anchor_blocks(self):
        (self.target/'invocation.md').write_text('## Supported commands\n## Supported commands\n')
        with self.assertRaises(ValueError):m.install(self.target)
    def test_symlink_blocks(self):
        (self.target/'git.md').unlink()
        outside=self.root/'other.md';outside.write_text('## Review before commit\n')
        (self.target/'git.md').symlink_to(outside)
        with self.assertRaises(ValueError):m.install(self.target)
    def test_live_parser_routes_new_and_preserves_old(self):
        m.install(self.target,True,self.root/'backups')
        script=str(self.target/'scripts/parse_invocation.py')
        a=subprocess.run([sys.executable,script,'handoff()'],text=True,capture_output=True)
        self.assertEqual(json.loads(a.stdout)['command'],'handoff')
        b=subprocess.run([sys.executable,script,'always()'],text=True,capture_output=True)
        self.assertIn('legacy',json.loads(b.stdout))
    def test_malformed_command_cli_exits_no_fallback(self):
        m.install(self.target,True,self.root/'backups')
        a=subprocess.run([sys.executable,str(self.target/'scripts/parse_invocation.py'),'sessions(limit=0)'],text=True,capture_output=True)
        self.assertEqual(a.returncode,2)
        self.assertEqual(json.loads(a.stderr)['execution'],'not_executed')
    def test_failure_rolls_back_written_files(self):
        original=m._atomic_write
        calls=[0]
        def fail_once(path,data,mode=0o644):
            calls[0]+=1
            if calls[0]==3:raise OSError('simulated disk failure')
            return original(path,data,mode)
        with patch.object(m,'_atomic_write',fail_once), self.assertRaises(OSError):
            m.install(self.target,True,self.root/'backups')
        for name,text in FIXTURE.items():self.assertEqual((self.target/name).read_text(),text)
    def test_wrong_target_rejected(self):
        (self.target/'SKILL.md').write_text('---\nname: another-skill\n---\n')
        with self.assertRaises(ValueError):m.install(self.target)

if __name__=='__main__':unittest.main()
