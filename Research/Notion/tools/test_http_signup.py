"""Offline tests. MockTransport prevents network, browsers and real account creation."""
import argparse
import contextlib
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import httpx
import http_signup as app


class HttpSignupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.ev = app.Evidence(self.root / 'run')
        self.clients = []

    def tearDown(self):
        for client in self.clients:
            client.close()
        self.temp.cleanup()

    def wire(self, handler, service='notion'):
        client = httpx.Client(transport=httpx.MockTransport(handler))
        self.clients.append(client)
        return app.Wire(client, self.ev, time.monotonic() + 30, service)

    def test_redaction(self):
        data = {'password': '<code>', 'loginOptionsToken': 'secret', 'csrfState': 'state',
                'nested': {'authorization': 'Bearer x'}, 'text': 'user@example.com <code> v02:abc:def'}
        text = json.dumps(app.redact(data))
        for secret in ('<code>', 'secret', 'user@example.com', 'v02:abc:def', 'Bearer x'):
            self.assertNotIn(secret, text)

    def test_encoded_email_redaction(self):
        value = "https://graph.microsoft.com/$metadata#users('user%40example.com')"
        self.assertNotIn('user%40example.com', app.redact(value))

    def test_wire_redacts_request_response(self):
        wire = self.wire(lambda r: httpx.Response(200, json={'token_v2': '[REDACTED_COOKIE]'}))
        wire.json('POST', app.APP + '/test', json={'password': '<code>'})
        text = (self.ev.directory / 'events.jsonl').read_text()
        self.assertNotIn('<code>', text)
        self.assertNotIn('server-secret', text)

    def test_rate_limit_stops_after_one_request(self):
        calls = []
        wire = self.wire(lambda r: (calls.append(r) or httpx.Response(429, headers={'Retry-After': '60'}, json={})))
        with self.assertRaises(app.StopRun) as caught:
            wire.json('POST', app.APP + '/test', json={})
        self.assertEqual(caught.exception.reason, 'RATE_LIMITED')
        self.assertEqual(len(calls), 1)

    def test_transport_timeout_never_replays(self):
        calls = []
        def fail(request):
            calls.append(request)
            raise httpx.ReadTimeout('private connection string', request=request)
        wire = self.wire(fail)
        with self.assertRaises(app.StopRun):
            wire.request('POST', app.APP + '/api/v3/createSpace', json={})
        self.assertEqual(len(calls), 1)
        self.assertNotIn('private connection string', (self.ev.directory / 'events.jsonl').read_text())

    def test_deadline_before_request(self):
        wire = self.wire(lambda r: self.fail('deadline must prevent network'))
        wire.deadline = time.monotonic() - 1
        with self.assertRaises(app.StopRun) as caught:
            wire.request('GET', app.APP)
        self.assertEqual(caught.exception.reason, 'DEADLINE_EXCEEDED')

    def test_reject_existing_account_file_mismatch(self):
        account_file = self.root / 'accounts.txt'
        account_file.write_text('user@example.com----pw----client----refresh----aux----pw\n')
        account = app.load_account('USER@example.com', [account_file])
        self.assertEqual(account['client_id'], 'client')
        self.assertNotIn('password', account)
        with self.assertRaises(app.StopRun):
            app.load_account('other@example.com', [account_file])

    def test_graph_identity_mismatch_stops(self):
        def handler(request):
            if request.url.host == 'login.microsoftonline.com':
                return httpx.Response(200, json={'access_token': 'access'})
            return httpx.Response(200, json={'mail': 'wrong@example.com'})
        mailbox = app.GraphMailbox({'email': 'user@example.com', 'client_id': 'client', 'refresh_token': 'rt'}, self.wire(handler, 'microsoft'))
        with self.assertRaises(app.StopRun) as caught:
            mailbox.authorize()
        self.assertEqual(caught.exception.reason, 'MAIL_IDENTITY_MISMATCH')

    def test_sender_must_be_notion_domain(self):
        message = {'from': {'emailAddress': {'address': 'attacker@example.com'}},
                   'subject': 'Notion signup code <code>', 'bodyPreview': ''}
        self.assertIsNone(app.GraphMailbox.extract(message))
        message['from']['emailAddress']['address'] = 'notify@makenotion.com'
        self.assertEqual(app.GraphMailbox.extract(message), '<code>')
        message['from']['emailAddress']['address'] = 'notify@makenotion.com.attacker.test'
        self.assertIsNone(app.GraphMailbox.extract(message))

    def test_timezone_comparison(self):
        self.assertEqual(app.parse_time('2026-10-18T02:14:09Z'),
                         app.parse_time('2026-10-18T10:14:09+08:00'))
        with self.assertRaises(ValueError):
            app.parse_time('2026-10-18T02:14:09')

    def test_graph_ordering_baseline_and_new_code(self):
        queries = []
        mailbox = app.GraphMailbox({'email': 'user@example.com', 'client_id': 'c', 'refresh_token': 'r'}, self.wire(lambda r: httpx.Response(200, json={})))
        mailbox.authorize = lambda: None
        mailbox.token = 'access'
        count = [0]
        def handler(request):
            if request.url.path.endswith('/me/mailFolders'):
                return httpx.Response(200, json={'value': [{'id': 'inbox-id', 'displayName': 'Inbox'}]})
            if request.url.path.endswith('/childFolders'):
                return httpx.Response(200, json={'value': []})
            queries.append(request.url)
            count[0] += 1
            messages = [{'id': 'old', 'receivedDateTime': '2026-10-18T02:14:09Z',
                'from': {'emailAddress': {'address': 'notify@makenotion.com'}},
                'subject': 'Your signup code <code>'}]
            if count[0] > 1:
                messages.insert(0, {'id': 'new', 'receivedDateTime': '2026-10-18T02:14:10Z',
                    'from': {'emailAddress': {'address': 'notify@makenotion.com'}},
                    'subject': 'Your signup code <code>'})
            return httpx.Response(200, json={'value': messages})
        mailbox.wire = self.wire(handler, 'microsoft')
        mailbox.baseline()
        result = mailbox.wait(app.parse_time('2026-10-18T02:14:09Z'), 1, 1)
        self.assertEqual(result, '<code>')
        self.assertTrue(all(url.params['$orderby'] == 'receivedDateTime desc' for url in queries))
        self.assertNotIn('<code>', (self.ev.directory / 'events.jsonl').read_text())

    def test_code_from_full_body_when_preview_truncated(self):
        message = {'id': 'm1', 'receivedDateTime': '2026-10-18T02:14:10Z',
                   'from': {'emailAddress': {'address': 'updates.notion.com'.join(['', ''])[:0] or 'notify@makenotion.com'}},
                   'subject': 'Your Notion signup code', 'bodyPreview': 'Enter this code to continue...'}
        self.assertIsNone(app.GraphMailbox.extract(message))
        html = '<html><body><p>Enter this code:</p><div><span>98</span><span>7654</span></div></body></html>'
        mailbox = app.GraphMailbox({'email': 'u@example.com'},
                                   self.wire(lambda r: httpx.Response(200, json={'body': {'content': html}}), 'microsoft'))
        mailbox.token = 'access'
        plain = mailbox.body_text('m1')
        self.assertEqual(app.GraphMailbox.extract_from(message, plain), '987654')

    def test_code_extraction_rejects_foreign_sender_body(self):
        message = {'id': 'm2', 'from': {'emailAddress': {'address': 'evil@example.com'}},
                   'subject': 'Your code', 'bodyPreview': ''}
        self.assertIsNone(app.GraphMailbox.extract_from(message, 'code <code>'))

    def test_mail_folder_discovery_covers_children_and_dedups(self):
        calls = []
        def handler(request):
            calls.append(request.url.path)
            if request.url.path.endswith('/me/mailFolders'):
                return httpx.Response(200, json={'value': [
                    {'id': 'inbox-id', 'displayName': 'Inbox'},
                    {'id': 'archive-id', 'displayName': 'Archive'}]})
            if request.url.path.endswith('/mailFolders/inbox-id/childFolders'):
                return httpx.Response(200, json={'value': [{'id': 'sub-id', 'displayName': 'Notion'}]})
            if request.url.path.endswith('/childFolders'):
                return httpx.Response(200, json={'value': []})
            message = {'id': 'm1', 'receivedDateTime': '2026-10-18T02:14:10Z',
                       'from': {'emailAddress': {'address': 'notify@makenotion.com'}},
                       'subject': 'Your code 333333', 'bodyPreview': 'code 333333'}
            if request.url.path.endswith('/mailFolders/archive-id/messages'):
                message = dict(message, id='m2')
            return httpx.Response(200, json={'value': [message]})
        mailbox = app.GraphMailbox({'email': 'user@example.com'}, self.wire(handler, 'microsoft'))
        mailbox.authorize = lambda: None
        mailbox.token = 'access'
        # inbox 与子文件夹返回同一 ID 时去重，archive 的邮件独立计数。
        self.assertEqual(len(mailbox.messages()), 2)
        self.assertTrue(any('archive-id' in path for path in calls))
        self.assertTrue(any('sub-id' in path for path in calls))
        mailbox.messages()
        self.assertEqual(sum(1 for path in calls if path.endswith('/me/mailFolders')), 1)

    def test_graph_failure_is_not_empty_mailbox(self):
        mailbox = app.GraphMailbox({}, self.wire(lambda r: httpx.Response(403, json={'error': 'forbidden'}), 'microsoft'))
        mailbox.authorize = lambda: None
        with self.assertRaises(app.StopRun):
            mailbox.messages()

    def test_live_tokens_not_replayed(self):
        bodies = []
        def handler(request):
            bodies.append(json.loads(request.content))
            if request.url.path.endswith('getLoginOptions'):
                return httpx.Response(200, json={'loginOptionsToken': 'fresh-login-token', 'authFlowId': 'fresh-flow', 'challengeProvider': 'hcaptcha'})
            return httpx.Response(200, json={'csrfState': 'fresh-state'})
        notion = app.NotionSignup(self.wire(handler), 'device')
        self.assertEqual(notion.send('user@example.com'), 'fresh-state')
        self.assertEqual(bodies[1]['loginOptionsToken'], 'fresh-login-token')
        self.assertNotIn('challengeToken', bodies[1])
        self.assertNotIn('fresh-login-token', (self.ev.directory / 'events.jsonl').read_text())

    def test_captcha_rejection_stops_no_solver_or_rotation(self):
        calls = []
        def handler(request):
            calls.append(request.url.path)
            if request.url.path.endswith('getLoginOptions'):
                return httpx.Response(200, json={'loginOptionsToken': 't', 'authFlowId': 'f', 'challengeProvider': 'hcaptcha'})
            return httpx.Response(400, json={'message': 'Signup is not allowed.'})
        notion = app.NotionSignup(self.wire(handler), 'device')
        with self.assertRaises(app.StopRun) as caught:
            notion.send('user@example.com')
        self.assertEqual(caught.exception.reason, 'SIGNUP_BLOCKED_OR_CHALLENGE')
        self.assertEqual(len(calls), 2)

    def test_onboard_work_role_skipped_no_payment(self):
        requests = []
        def handler(request):
            endpoint = request.url.path.rsplit('/', 1)[-1]
            payload = json.loads(request.content)
            requests.append((endpoint, payload))
            if endpoint == 'validateUserCanCreateWorkspace':
                return httpx.Response(200, json={'canUserCreateSpace': True})
            if endpoint == 'createSpace':
                return httpx.Response(200, json={'spaceId': 'space'})
            if endpoint == 'completeCurrentUserOnboarding':
                return httpx.Response(200, json={'recordMap': {'notion_user': {'user': {'value': {'value': {'onboarding_completed': True}}}}}})
            return httpx.Response(200, json={})
        notion = app.NotionSignup(self.wire(handler), 'device')
        notion.user_id = 'user'
        space, _ = notion.onboard('Example')
        self.assertEqual(space, 'space')
        creation = next(body for endpoint, body in requests if endpoint == 'createSpace')
        self.assertEqual(creation['planSelection'], 'team')
        self.assertEqual(creation['initialPersona'], 'unfilled')
        self.assertNotIn('Sales', json.dumps(requests))
        self.assertFalse(any('checkout' in endpoint.lower() or 'subscribe' in endpoint.lower() for endpoint, _ in requests))

    def test_partial_creation_saved_on_offer_failure(self):
        def handler(request):
            endpoint = request.url.path.rsplit('/', 1)[-1]
            if endpoint == 'validateUserCanCreateWorkspace':
                return httpx.Response(200, json={'canUserCreateSpace': True})
            if endpoint == 'createSpace':
                return httpx.Response(200, json={'spaceId': 'created-before-error'})
            if endpoint == 'getPossibleOffers':
                return httpx.Response(500, json={})
            return httpx.Response(200, json={})
        notion = app.NotionSignup(self.wire(handler), 'device')
        with self.assertRaises(app.StopRun):
            notion.onboard('Example')
        self.assertEqual(notion.space_id, 'created-before-error')
        self.assertEqual(json.loads((self.ev.directory / 'progress.json').read_text())['spaceId'], 'created-before-error')

    def test_limits_and_explicit_network_mode(self):
        p = app.parser()
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                p.parse_args(['--email', 'user@example.com'])
            with self.assertRaises(SystemExit):
                p.parse_args(['--email', 'user@example.com', '--direct', '--send-attempts', '4'])
        args = p.parse_args(['--email', 'user@example.com', '--direct'])
        self.assertEqual(args.send_attempts, 1)

    def test_execute_full_flow_and_cleanup(self):
        self.run_execute_fixture(preflight=False)

    def test_execute_preflight_never_sends_code(self):
        self.run_execute_fixture(preflight=True)

    def test_execute_hybrid_handoff_no_http_resend(self):
        self.run_execute_fixture(preflight=False, hybrid=True)

    def run_execute_fixture(self, preflight, hybrid=False):
        account_file = self.root / 'accounts.txt'
        account_file.write_text('user@example.com----pw----client----refresh----aux----pw\n')
        requests = []
        sent = [False]
        created_clients = []
        def handler(request):
            requests.append(request)
            host, path = request.url.host, request.url.path
            if host == 'api.ipify.org':
                return httpx.Response(200, json={'ip': '203.0.113.7'})
            if host == 'login.microsoftonline.com':
                return httpx.Response(200, json={'access_token': 'access', 'expires_in': 3600})
            if host == 'graph.microsoft.com':
                if path.endswith('/me'):
                    return httpx.Response(200, json={'mail': 'user@example.com'})
                if path.endswith('/mailFolders'):
                    return httpx.Response(200, json={'value': [
                        {'id': 'inbox-id', 'displayName': 'Inbox'},
                        {'id': 'junk-id', 'displayName': 'Junk Email'}]})
                if path.endswith('/childFolders'):
                    return httpx.Response(200, json={'value': []})
                messages = []
                if sent[0]:
                    messages = [{'id': 'new', 'receivedDateTime': app.iso(app.now()),
                        'from': {'emailAddress': {'address': 'notify@makenotion.com'}},
                        'subject': 'Your signup code <code>', 'bodyPreview': 'code <code>'}]
                return httpx.Response(200, json={'value': messages})
            if path == '/signup':
                return httpx.Response(200, text='<html>23.13.20261017.2209</html>')
            endpoint = path.rsplit('/', 1)[-1]
            data = {
                'getLoginOptions': {'loginOptionsToken': 'fresh-token', 'authFlowId': 'flow',
                                    **({'challengeProvider': 'hcaptcha'} if hybrid else {})},
                'sendTemporaryPassword': {'csrfState': 'fresh-state'},
                'loginWithEmail': {'isNewSignup': True, 'userId': 'user'},
                'validateUserCanCreateWorkspace': {'canUserCreateSpace': True},
                'createSpace': {'spaceId': 'space'},
                'completeCurrentUserOnboarding': {'recordMap': {'notion_user': {'user': {'value': {'value': {'onboarding_completed': True}}}}}},
            }.get(endpoint, {})
            if endpoint == 'sendTemporaryPassword':
                sent[0] = True
            headers = {'set-cookie': 'token_v2=[REDACTED_COOKIE]; Path=/; Secure; HttpOnly'} if endpoint == 'loginWithEmail' else {}
            return httpx.Response(200, json=data, headers=headers)
        original_client = httpx.Client
        def factory(**kwargs):
            client = original_client(transport=httpx.MockTransport(handler), **kwargs)
            created_clients.append(client)
            return client
        args = app.parser().parse_args(['--email', 'user@example.com', '--direct'] + (['--preflight-only'] if preflight else []))
        args.account_file = [account_file]
        args.human_verification = hybrid
        import human_verification as bridge
        def manual_handoff(**kwargs):
            sent[0] = True
            kwargs['evidence'].event('browser_opened')
            kwargs['evidence'].event('browser_closed', context=True, browser=True, driver=True)
            return bridge.VerificationResult('fresh-state', 'Real Edge', 'current', app.iso(app.now()), [
                {'name': 'notion_browser_id', 'value': kwargs['device_id'], 'domain': 'app.notion.com', 'path': '/', 'secure': True}])
        with patch.object(app.httpx, 'Client', side_effect=factory), \
             patch.object(bridge, 'verify_and_send', side_effect=manual_handoff) as handoff, \
             contextlib.redirect_stdout(io.StringIO()):
            result = app.execute(args, self.ev)
        self.assertEqual(handoff.call_count, 1 if hybrid else 0)
        self.assertEqual(result['status'], 'preflight_ok' if preflight else 'completed')
        self.assertTrue(all(c.is_closed for c in created_clients))
        sends = [r for r in requests if r.url.path.endswith('sendTemporaryPassword')]
        self.assertEqual(len(sends), 0 if preflight or hybrid else 1)
        text = (self.ev.directory / 'events.jsonl').read_text()
        for secret in ('<code>', 'session-secret', 'fresh-token', 'fresh-state', 'user@example.com'):
            self.assertNotIn(secret, text)
        if not preflight:
            state = json.loads((self.ev.directory / 'session.private.json').read_text())
            self.assertTrue(any(c['name'] == 'token_v2' and c['value'] == 'session-secret' for c in state['cookies']))
            self.assertEqual(result['spaceId'], 'space')

    def test_no_browser_import_or_process_launch(self):
        import ast
        tree = ast.parse(Path(app.__file__).read_text(encoding='utf-8'))
        forbidden = {'playwright', 'selenium', 'cloakbrowser', 'subprocess', 'webbrowser'}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertFalse(any(alias.name.split('.')[0] in forbidden for alias in node.names))
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn((node.module or '').split('.')[0], forbidden)


if __name__ == '__main__':
    unittest.main()
