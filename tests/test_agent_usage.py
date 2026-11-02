from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from agent_usage import collect_usage

NOW = datetime(2026, 10, 30, 12, tzinfo=timezone.utc)
RECENT = '2026-10-30T10:00:00Z'
OLD = '2026-08-01T10:00:00Z'


class AgentUsageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.claude = self.root / 'claude'
        self.codex = self.root / 'codex'

    def log(self, root, name, rows):
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('\n'.join(json.dumps(r) for r in rows) + '\n')

    def collect(self):
        return collect_usage(self.claude, self.codex, days=30, now=NOW,
                             known_skills={'ad-ticket', 'ad-work-prep', 'tdd'})

    def test_codex_counts_only_user_invocation_and_filters_record_time(self):
        def message(text, timestamp=RECENT, role='user', **extra):
            return dict(timestamp=timestamp, type='response_item',
                        payload={'type': 'message', 'role': role,
                                 'content': [{'type': 'input_text', 'text': text}]}, **extra)
        # The directory's date is old; the resumed session's records are recent.
        self.log(self.codex, '2026/08/01/resumed.jsonl', [
            message('$ad-ticket actual task'), message('$ad-work-prep old', OLD),
            message('# AGENTS.md\nAvailable skills: $ad-work-prep\n$HOME'),
            message('$ad-work-prep example', role='assistant'),
            message('$ad-work-prep inherited', metadata={'inherited_user_message': True}),
            message('$ad-work-prep injected', metadata={'client_authored': False}),
            message('$HOME not a skill'), message('Explain `$ad-work-prep`, do not run it'),
        ])
        stats = self.collect()['codex']
        self.assertEqual(stats['skill_hits'], {'ad-ticket': 1})
        self.assertEqual(stats['last']['ad-ticket'], '2026-10-30')

    def test_codex_retained_user_source_is_real_input_and_revisions_are_not_new_calls(self):
        def row(revision):
            return {'timestamp': RECENT, 'type': 'response_item', 'payload': {
                'type': 'message', 'role': 'user', 'id': revision,
                'content': [{'type': 'input_text', 'text': '# AGENTS.md instructions'},
                            {'type': 'input_text', 'text': '$ad-ticket actual task'}]},
                'metadata': {'client_authored': False, 'retained_source': {
                    'id': {'message_id': 'original-user-message', 'role': 'user'}, 'revision': revision}}}
        self.log(self.codex, 'one.jsonl', [row('snapshot-1'), row('snapshot-2')])
        self.log(self.codex, 'copy.jsonl', [row('snapshot-3')])
        self.assertEqual(self.collect()['codex']['skill_hits'], {'ad-ticket': 1})

    def test_codex_prefers_user_events_without_double_counting_message_mirror(self):
        self.log(self.codex, 'session.jsonl', [
            {'timestamp': RECENT, 'type': 'event_msg', 'payload': {'type': 'user_message', 'message': '$tdd implement'}},
            {'timestamp': RECENT, 'type': 'response_item', 'payload': {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': '$tdd implement'}]}},
        ])
        self.assertEqual(self.collect()['codex']['skill_hits'], {'tdd': 1})

    def test_native_codex_requests_are_deduplicated_and_cache_is_subset(self):
        native = {'timestamp': RECENT, 'type': 'token_usage_record', 'payload': {
            'response_id': 'response-1', 'usage': {'input_tokens': 100, 'cached_input_tokens': 80, 'output_tokens': 10}}}
        fallback = {'timestamp': RECENT, 'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {
            'last_token_usage': {'input_tokens': 100, 'cached_input_tokens': 80, 'output_tokens': 10},
            'total_token_usage': {'input_tokens': 100, 'output_tokens': 10, 'total_tokens': 110}}}}
        self.log(self.codex, 'session.jsonl', [native, native, fallback])
        stats = self.collect()['codex']
        self.assertEqual(stats['usage_requests'], 1)
        self.assertEqual(stats['avg_context_tokens'], 100)
        self.assertEqual(stats['tokens']['input_tokens'], 100)
        self.assertEqual(stats['tokens']['cached_input_tokens'], 80)

    def test_legacy_codex_deduplicates_unchanged_totals_but_counts_identical_requests(self):
        def event(total, timestamp=RECENT):
            return {'timestamp': timestamp, 'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {
                'last_token_usage': {'input_tokens': 100, 'cached_input_tokens': 50, 'output_tokens': 5},
                'total_token_usage': {'input_tokens': total, 'output_tokens': total // 20, 'total_tokens': total + total // 20}}}}
        self.log(self.codex, 'session.jsonl', [event(100, OLD), event(100), event(200), event(200), event(300)])
        stats = self.collect()['codex']
        self.assertEqual(stats['usage_requests'], 2)
        self.assertEqual(stats['avg_context_tokens'], 100)

    def test_claude_usage_is_per_response_and_includes_all_input_cache_categories(self):
        def response(identity, usage, content=None):
            return {'timestamp': RECENT, 'type': 'assistant', 'sessionId': 'session-1',
                    'message': {'id': identity, 'role': 'assistant', 'usage': usage, 'content': content or []}}
        usage = {'input_tokens': 20, 'cache_read_input_tokens': 70, 'cache_creation_input_tokens': 10, 'output_tokens': 2}
        tool = {'type': 'tool_use', 'id': 'call-1', 'name': 'Read', 'input': {'file_path': '/repo/a.py'}}
        self.log(self.claude, 'proj/session.jsonl', [response('msg-1', usage, [tool]),
            response('msg-1', dict(usage, output_tokens=5), [tool]),
            response('msg-2', {'input_tokens': 200, 'output_tokens': 3})])
        stats = self.collect()['claude']
        self.assertEqual(stats['usage_requests'], 2)
        self.assertEqual(stats['avg_context_tokens'], 150)
        self.assertEqual(stats['tokens']['output_tokens'], 8)
        self.assertEqual(stats['tool_calls'], {'Read': 1})

    def test_claude_skill_mentions_and_tool_results_are_not_invocations(self):
        self.log(self.claude, 'proj/session.jsonl', [
            {'timestamp': RECENT, 'type': 'user', 'message': {'content': '<command-name>/ad:ticket</command-name> task'}},
            {'timestamp': RECENT, 'type': 'assistant', 'message': {'content': [
                {'type': 'text', 'text': '<command-name>/ad:work-prep</command-name>'},
                {'type': 'tool_use', 'id': 'skill-1', 'name': 'Skill', 'input': {'skill': 'ad:work-prep'}}]}},
            {'timestamp': RECENT, 'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': 'other', 'content': '<command-name>/ad:work-prep</command-name>'}]}},
        ])
        stats = self.collect()['claude']
        self.assertEqual(stats['skill_hits'], {'ad-ticket': 1, 'ad-work-prep': 1})
        self.assertEqual(stats['skill_sources'], {'user': {'ad-ticket': 1}, 'model': {'ad-work-prep': 1}})

    def test_claude_generated_command_message_prefix_is_a_real_invocation(self):
        self.log(self.claude,'one.jsonl',[{'timestamp':RECENT,'type':'user','uuid':'u1','message':{
            'content':'<command-message>ad:ticket</command-message>\n<command-name>/ad:ticket</command-name>\n<command-args>task</command-args>'}}])
        self.assertEqual(self.collect()['claude']['skill_hits'],{'ad-ticket':1})

    def test_codex_tool_calls_and_results_are_measured_separately_from_requests(self):
        self.log(self.codex, 'session.jsonl', [
            {'timestamp': RECENT, 'type': 'response_item', 'payload': {'type': 'function_call', 'name': 'exec_command', 'call_id': 'c1', 'arguments': '{"cmd":"cd /repo"}'}},
            {'timestamp': '2026-10-30T10:00:02Z', 'type': 'response_item', 'payload': {'type': 'function_call_output', 'call_id': 'c1', 'output': 'ok'}},
            {'timestamp': RECENT, 'type': 'response_item', 'payload': {'type': 'custom_tool_call', 'name': 'apply_patch', 'call_id': 'c2', 'input': 'patch'}},
        ])
        stats = self.collect()['codex']
        self.assertEqual(stats['tool_calls'], {'exec_command': 1, 'apply_patch': 1})
        self.assertEqual(stats['tool_result_chars']['exec_command'], 2)
        self.assertEqual(stats['tool_latency']['exec_command'], [2.0])
        self.assertIsNone(stats['avg_context_tokens'])
        self.assertEqual(stats['usage_requests'], 0)

    def test_tool_ids_in_different_sessions_do_not_collide(self):
        for name in ['a', 'b']:
            self.log(self.claude, name + '.jsonl', [{'timestamp': RECENT, 'sessionId': name, 'type': 'assistant', 'message': {
                'content': [{'type': 'tool_use', 'id': 'same', 'name': 'Read', 'input': {'file_path': '/repo/a'}}]}}])
        self.assertEqual(self.collect()['claude']['tool_calls'], {'Read': 2})

    def test_native_transition_preserves_prior_legacy_request(self):
        self.log(self.codex, 'mixed.jsonl', [
            {'timestamp': RECENT, 'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {
                'total_token_usage': {'input_tokens': 100}, 'last_token_usage': {'input_tokens': 100}}}},
            {'timestamp': RECENT, 'type': 'token_usage_record', 'payload': {'response_id': 'new', 'usage': {'input_tokens': 300}}},
            {'timestamp': RECENT, 'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {
                'total_token_usage': {'input_tokens': 400}, 'last_token_usage': {'input_tokens': 300}}}},
        ])
        stats=self.collect()['codex']
        self.assertEqual(stats['usage_requests'],2)
        self.assertEqual(stats['tokens']['input_tokens'],400)

    def test_event_and_item_formats_can_represent_different_requests(self):
        self.log(self.codex, 'mixed.jsonl', [
            {'timestamp': RECENT, 'type': 'event_msg', 'payload': {'type': 'user_message','message':'$ad-ticket one'}},
            {'timestamp': RECENT, 'type': 'response_item', 'payload': {'type':'message','role':'user','content':[{'type':'input_text','text':'$ad-work-prep two'}]}},
        ])
        self.assertEqual(self.collect()['codex']['skill_hits'],{'ad-ticket':1,'ad-work-prep':1})

    def test_user_mirror_pairing_respects_stable_ids(self):
        def event(identity):
            return {'timestamp':RECENT,'type':'event_msg','payload':{'type':'user_message','id':identity,'message':'$ad-ticket task'}}
        def item(identity,t=RECENT):
            return {'timestamp':t,'type':'response_item','payload':{'type':'message','role':'user','id':identity,'content':[{'type':'input_text','text':'$ad-ticket task'}]}}
        self.log(self.codex,'one.jsonl',[event('first'),item('different')])
        self.assertEqual(self.collect()['codex']['skill_hits'],{'ad-ticket':2})
        self.log(self.codex,'one.jsonl',[event('same'),item('same','2026-10-30T10:00:01Z')])
        self.assertEqual(self.collect()['codex']['skill_hits'],{'ad-ticket':1})

    def test_native_response_ids_are_scoped_to_session(self):
        for name,amount in [('one',100),('two',300)]:
            self.log(self.codex,name+'.jsonl',[{'timestamp':RECENT,'type':'session_meta','payload':{'id':name}},
                {'timestamp':RECENT,'type':'token_usage_record','payload':{'response_id':'same','usage':{'input_tokens':amount}}}])
        stats=self.collect()['codex']
        self.assertEqual(stats['usage_requests'],2)
        self.assertEqual(stats['tokens']['input_tokens'],400)

    def test_retained_block_position_is_not_invocation_identity(self):
        def rec(padding):
            return {'timestamp':RECENT,'type':'response_item','payload':{'type':'message','role':'user','content':
                [{'type':'input_text','text':'# Instructions'}]*padding + [{'type':'input_text','text':'$ad-ticket task'}]},
                'metadata':{'client_authored':False,'retained_source':{'id':{'message_id':'stable','role':'user'}}}}
        self.log(self.codex,'one.jsonl',[rec(1),rec(2)])
        self.assertEqual(self.collect()['codex']['skill_hits'],{'ad-ticket':1})

    def test_legacy_cache_detail_updates_are_not_new_requests(self):
        rows=[{'timestamp':RECENT,'type':'event_msg','payload':{'type':'token_count','info':{
            'total_token_usage':{'input_tokens':100,'output_tokens':5,'cached_input_tokens':cached},
            'last_token_usage':{'input_tokens':100,'output_tokens':5,'cached_input_tokens':cached}}}} for cached in [0,50]]
        self.log(self.codex,'one.jsonl',rows)
        stats=self.collect()['codex']
        self.assertEqual(stats['usage_requests'],1)
        self.assertEqual(stats['tokens']['cached_input_tokens'],50)

    def test_legacy_counter_reset_does_not_merge_new_request_with_old_total(self):
        rows=[{'timestamp':RECENT,'type':'event_msg','payload':{'type':'token_count','info':{
            'total_token_usage':{'input_tokens':total},'last_token_usage':{'input_tokens':100}}}} for total in [100,200,100]]
        self.log(self.codex,'one.jsonl',rows)
        self.assertEqual(self.collect()['codex']['usage_requests'],3)

    def test_empty_and_malformed_logs_are_explicitly_unknown(self):
        self.log(self.codex, 'broken.jsonl', [{'timestamp': 'bad', 'type': 'token_usage_record'}, []])
        p=self.claude/'broken.jsonl';p.parent.mkdir(exist_ok=True);p.write_text('broken\n')
        for stats in self.collect().values():
            self.assertIsNone(stats['avg_context_tokens'])
            self.assertEqual(stats['usage_requests'], 0)


if __name__ == '__main__':
    unittest.main()
