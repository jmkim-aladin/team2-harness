from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from harness_context_audit import build_report, hooks, resident_budget
from skill_usage_report import skill_rows


class AuditReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo, self.claude, self.codex, self.agents = [self.base / n for n in ('repo', 'claude', 'codex', 'agents')]
        for p in (self.repo, self.claude, self.codex, self.agents): p.mkdir()

    def test_resident_estimates_separate_engines_and_deduplicate_imports(self):
        (self.repo / 'CLAUDE.md').write_text('cccc')
        (self.repo / 'AGENTS.md').write_text('aaaaa')
        (self.claude / 'CLAUDE.md').write_text('@base.md\n@base.md\n')
        (self.claude / 'base.md').write_text('abc')
        (self.claude / 'unrelated.md').write_text('not loaded' * 100)
        (self.codex / 'AGENTS.md').write_text('codex')
        kwargs=dict(harness=self.repo, claude_home=self.claude, codex_home=self.codex, agents_home=self.agents)
        c=resident_budget('claude', **kwargs);x=resident_budget('codex', **kwargs)
        self.assertNotIn(str(self.repo / 'AGENTS.md'), c)
        self.assertNotIn(str(self.repo / 'CLAUDE.md'), x)
        self.assertNotIn(str(self.claude / 'unrelated.md'), c)
        self.assertEqual(c[str(self.claude / 'base.md')], 3)
        self.assertEqual(set(x), {str(self.repo / 'AGENTS.md'), str(self.codex / 'AGENTS.md')})

    def test_empty_logs_report_unknown_not_zero_and_cover_both_engines(self):
        report=build_report(harness=self.repo,claude_home=self.claude,codex_home=self.codex,agents_home=self.agents)
        self.assertEqual(set(report['engines']), {'codex','claude'})
        for stats in report['engines'].values():
            self.assertIsNone(stats['avg_context_tokens'])
            self.assertIsNone(stats['bash_share'])
        json.dumps(report)

    def test_hooks_never_include_command_secrets(self):
        (self.claude / 'settings.json').write_text(json.dumps({'hooks': {'PreToolUse': [{'hooks': [
            {'command': 'TOKEN=secretvalue curl --header private-token'}, {'command': 'bash script --token anothersecret'}]}]}}))
        out=json.dumps(hooks('claude', harness=self.repo,claude_home=self.claude,codex_home=self.codex))
        self.assertNotIn('secretvalue',out)
        self.assertNotIn('private-token',out)
        self.assertNotIn('anothersecret',out)

    def test_skill_table_and_context_audit_use_identical_observations(self):
        cmd=self.repo / '.claude/commands/ad';cmd.mkdir(parents=True);(cmd/'ticket.md').write_text('---\ndescription: ticket\n---\n')
        logs=self.codex / 'sessions';logs.mkdir()
        (logs/'current.jsonl').write_text(json.dumps({'timestamp':'2026-10-30T10:00:00Z','type':'response_item','payload':{'type':'message','role':'user','content':[{'type':'input_text','text':'$ad-ticket request'}]}})+'\n')
        report=build_report(days=30,now=datetime(2026,10,30,12,tzinfo=timezone.utc),harness=self.repo,claude_home=self.claude,codex_home=self.codex,agents_home=self.agents)
        rows=skill_rows(report['engines'], {'ad-ticket'})
        self.assertEqual(rows,[dict(skill='ad:ticket',user=0,model=0,codex=1,total=1,last='2026-10-30')])


    def test_both_command_lines_share_usage_and_skill_counts(self):
        cmd=self.repo/'.claude/commands/ad';cmd.mkdir(parents=True);(cmd/'ticket.md').write_text('---\ndescription: ticket\n---\n')
        timestamp=datetime.now(timezone.utc).isoformat()
        claude_logs=self.claude/'projects';codex_logs=self.codex/'sessions'
        claude_logs.mkdir();codex_logs.mkdir()
        response={'timestamp':timestamp,'type':'assistant','sessionId':'s','message':{'id':'m','usage':{'input_tokens':20,'cache_read_input_tokens':70,'cache_creation_input_tokens':10,'output_tokens':5},'content':[]}}
        (claude_logs/'one.jsonl').write_text('\n'.join(json.dumps(r) for r in [response,response,{'timestamp':timestamp,'type':'user','message':{'content':'<command-name>/ad:ticket</command-name>'}}]))
        (codex_logs/'one.jsonl').write_text('\n'.join(json.dumps(r) for r in [
            {'timestamp':timestamp,'type':'token_usage_record','payload':{'response_id':'r','usage':{'input_tokens':100,'cached_input_tokens':80,'output_tokens':5}}},
            {'timestamp':timestamp,'type':'response_item','payload':{'type':'message','role':'user','content':[{'type':'input_text','text':'$ad-ticket task'}]}}]))
        env=dict(os.environ,HOME=str(self.base),CODEX_HOME=str(self.codex),TEAM2_HARNESS_PATH=str(self.repo))
        tools=Path(__file__).resolve().parents[1]/'tools'
        audit=subprocess.run([sys.executable,str(tools/'harness_context_audit.py'),'--json','--days','30','--claude-root',str(claude_logs),'--codex-root',str(codex_logs)],env=env,capture_output=True,text=True,check=True)
        data=json.loads(audit.stdout)
        for engine in ('claude','codex'):
            self.assertEqual(data['engines'][engine]['usage_requests'],1)
            self.assertEqual(data['engines'][engine]['avg_context_tokens'],100)
        skills=subprocess.run([sys.executable,str(tools/'skill_usage_report.py'),'--json','--days','30','--root',str(claude_logs),'--codex-root',str(codex_logs)],env=env,capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(skills.stdout)['rows'][0]['total'],2)
        text=subprocess.run([sys.executable,str(tools/'harness_context_audit.py'),'--engine','codex','--days','30','--claude-root',str(claude_logs),'--codex-root',str(codex_logs)],env=env,capture_output=True,text=True,check=True)
        self.assertIn('## codex',text.stdout)
        self.assertNotIn('## claude',text.stdout)
        bad=subprocess.run([sys.executable,str(tools/'harness_context_audit.py'),'--days','-1'],env=env,capture_output=True,text=True)
        self.assertEqual(bad.returncode,2)


if __name__ == '__main__': unittest.main()
