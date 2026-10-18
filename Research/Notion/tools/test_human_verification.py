"""Fully offline browser handoff tests: no actual Edge, requests or captcha service."""

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 YG
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

import httpx
import http_signup as app
import human_verification as bridge



class HumanVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ev = app.Evidence(Path(self.temp.name) / 'run')
        self.client = httpx.Client()
        self.client.cookies.set('notion_browser_id', 'device', domain='app.notion.com')

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def request(self, email='user@example.com', device='device', endpoint=bridge.SEND_PATH):
        return NS(url=app.APP + endpoint, method='POST',
                  post_data_json={'email': email, 'deviceId': device, 'challengeToken': 'do-not-log'},
                  headers={'user-agent': 'Real Edge', 'notion-client-version': 'current'})

    def guard(self):
        return bridge.SendGuard('user@example.com', 'device', self.ev, lambda: app.iso(app.now()))

    def test_guard_accepts_once_and_never_logs_challenge(self):
        guard = self.guard()
        route = Mock()
        request = self.request()
        guard.route(route, request)
        route.continue_.assert_called_once()
        duplicate = Mock()
        guard.route(duplicate, self.request())
        duplicate.abort.assert_called_once()
        response = NS(request=request, status=200, json=lambda: {'csrfState': 'secret-state'})
        guard.response(response)
        self.assertEqual(guard.state, 'secret-state')
        log = (self.ev.directory / 'events.jsonl').read_text()
        self.assertNotIn('do-not-log', log)
        self.assertNotIn('secret-state', log)
        self.assertIn('browser_duplicate_send_blocked', log)

    def test_official_native_uuid_can_be_adopted_without_rewriting(self):
        guard = bridge.SendGuard('user@example.com', 'seed', self.ev,
            lambda: app.iso(app.now()), allow_native_device=True)
        request = self.request(device='12345678-1234-1234-1234-123456789abc')
        route = Mock()
        guard.route(route, request)
        route.continue_.assert_called_once()
        self.assertEqual(guard.device_id, request.post_data_json['deviceId'])
        self.assertIsNone(guard.failure)

    def test_guard_blocks_other_email_and_device(self):
        for request, reason in [(self.request(email='other@example.com'), 'BROWSER_EMAIL_MISMATCH'),
                                (self.request(device='changed'), 'BROWSER_DEVICE_MISMATCH')]:
            guard = self.guard()
            route = Mock()
            guard.route(route, request)
            route.abort.assert_called_once()
            self.assertEqual(guard.failure.reason, reason)
            self.assertFalse(guard.sent)

    def test_guard_blocks_browser_login_and_create(self):
        for endpoint in bridge.BLOCKED_BROWSER_PATHS:
            route = Mock()
            self.guard().route(route, self.request(endpoint=endpoint))
            route.abort.assert_called_once()

    def test_server_rejection_stops(self):
        guard = self.guard()
        request = self.request()
        guard.route(Mock(), request)
        guard.response(NS(request=request, status=400, json=lambda: {'message': 'Signup is not allowed.'}))
        self.assertEqual(guard.failure.reason, 'BROWSER_SEND_REJECTED')
        self.assertFalse(guard.state)

    def test_request_failure_is_not_auto_retry(self):
        guard = self.guard()
        request = self.request()
        guard.route(Mock(), request)
        guard.request_failed(request)
        self.assertEqual(guard.failure.reason, 'BROWSER_SEND_UNCONFIRMED')

    def test_same_proxy_credentials_preserved(self):
        self.assertEqual(bridge.proxy_options('http://user:p%40ss@proxy.test:8000'),
                         {'server': 'http://proxy.test:8000', 'username': 'user', 'password': 'p@ss'})
        self.assertIsNone(bridge.proxy_options(None))
        with self.assertRaises(bridge.HumanVerificationError):
            bridge.proxy_options('socks5://proxy.test:8000')

    def test_cookie_handoff_retains_scope_secure_and_expires(self):
        bridge.import_cookies(self.client, [
            {'name': 'notion_browser_id', 'value': 'device', 'domain': 'app.notion.com', 'path': '/', 'secure': True},
            {'name': 'token_v2', 'value': 'private', 'domain': '.notion.com', 'path': '/', 'secure': True,
             'httpOnly': True, 'expires': 1999999999},
            {'name': 'captcha_tracking', 'value': 'must-not-import', 'domain': '.hcaptcha.com', 'path': '/'}])
        token = next(c for c in self.client.cookies.jar if c.name == 'token_v2')
        self.assertTrue(token.secure)
        self.assertTrue(token.domain_initial_dot)
        self.assertEqual(token.expires, 1999999999)
        self.assertEqual(len(list(self.client.cookies.jar)), 2)
        self.assertTrue(all(bridge.notion_domain(c['domain']) for c in bridge.export_cookies(self.client)))

    def fake_runtime(self, *, ip='203.0.113.7', page_closed=False, rejected=False, close_error=False):
        context = Mock()
        context.cookies.side_effect = lambda *a: [
            {'name': 'notion_browser_id', 'value': 'device', 'domain': 'app.notion.com', 'path': '/', 'secure': True}]
        context.request.get.return_value = NS(status=200, json=lambda: {'ip': ip})
        callbacks = {}
        context.on.side_effect = lambda event, callback: callbacks.update({event: callback})
        context.route.side_effect = lambda pattern, callback: callbacks.update({'route': callback})
        page = Mock()
        page.is_closed.return_value = page_closed
        def tick(*args):
            request = self.request()
            callbacks['route'](Mock(), request)
            callbacks['response'](NS(request=request, status=400 if rejected else 200,
                json=lambda: {'message': 'blocked'} if rejected else {'csrfState': 'browser-state'}))
        page.wait_for_timeout.side_effect = tick
        page.evaluate.return_value = 'Real Edge'
        context.new_page.return_value = page
        browser = Mock()
        browser.new_context.return_value = context
        if close_error:
            context.close.side_effect = RuntimeError('close failed')
        driver = Mock()
        driver.chromium.launch.return_value = browser
        manager = Mock()
        manager.start.return_value = driver
        return manager, driver, browser, context, page

    def run_fake(self, runtime, deadline=None):
        return bridge.verify_and_send(email='user@example.com', device_id='device', client=self.client,
            evidence=self.ev, proxy_url='http://u:p@proxy.test:8000', expected_ip='203.0.113.7',
            deadline=deadline or time.monotonic() + 20, timeout=10,
            utc_now=lambda: app.iso(app.now()), manager_factory=lambda: runtime[0])

    def check_cleanup(self, runtime):
        runtime[1].stop.assert_called_once()
        runtime[2].close.assert_called_once()
        runtime[3].close.assert_called_once()

    def test_success_closes_before_http_continues(self):
        runtime = self.fake_runtime()
        result = self.run_fake(runtime)
        self.assertEqual(result.state, 'browser-state')
        self.assertEqual(result.user_agent, 'Real Edge')
        self.check_cleanup(runtime)
        self.assertTrue(self.ev.browser_used)
        self.assertTrue(self.ev.browser_resources_closed)
        self.assertTrue((self.ev.directory / 'browser-handoff.private.json').exists())
        self.assertNotIn('browser-state', (self.ev.directory / 'events.jsonl').read_text())

    def test_proxy_exit_change_stops_before_signup(self):
        runtime = self.fake_runtime(ip='203.0.113.8')
        with self.assertRaises(bridge.HumanVerificationError) as caught:
            self.run_fake(runtime)
        self.assertEqual(caught.exception.reason, 'BROWSER_EXIT_MISMATCH')
        self.assertFalse(any('signup' in str(c) for c in runtime[4].method_calls))
        self.assertNotIn('browser_send_request', (self.ev.directory / 'events.jsonl').read_text())
        self.check_cleanup(runtime)

    def test_user_close_stops_and_cleans_up(self):
        runtime = self.fake_runtime(page_closed=True)
        with self.assertRaises(bridge.HumanVerificationError) as caught:
            self.run_fake(runtime)
        self.assertEqual(caught.exception.reason, 'HUMAN_BROWSER_CLOSED')
        self.check_cleanup(runtime)

    def test_rejection_cleans_up(self):
        runtime = self.fake_runtime(rejected=True)
        with self.assertRaises(bridge.HumanVerificationError) as caught:
            self.run_fake(runtime)
        self.assertEqual(caught.exception.reason, 'BROWSER_SEND_REJECTED')
        self.check_cleanup(runtime)

    def test_expired_budget_never_opens_edge(self):
        runtime = self.fake_runtime()
        with self.assertRaises(bridge.HumanVerificationError) as caught:
            self.run_fake(runtime, deadline=time.monotonic() - 1)
        self.assertEqual(caught.exception.reason, 'HUMAN_VERIFICATION_TIMEOUT')
        runtime[1].chromium.launch.assert_not_called()
        runtime[1].stop.assert_called_once()

    def test_navigation_error_cleans_all_resources(self):
        runtime = self.fake_runtime()
        runtime[4].goto.side_effect = RuntimeError('do-not-log-credentials')
        with self.assertRaises(bridge.HumanVerificationError):
            self.run_fake(runtime)
        self.check_cleanup(runtime)
        self.assertNotIn('do-not-log-credentials', (self.ev.directory / 'events.jsonl').read_text())

    def test_keyboard_interrupt_still_cleans(self):
        runtime = self.fake_runtime()
        runtime[4].wait_for_timeout.side_effect = KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            self.run_fake(runtime)
        self.check_cleanup(runtime)

    def test_cleanup_failure_is_not_reported_as_closed(self):
        runtime = self.fake_runtime(close_error=True)
        with self.assertRaises(bridge.HumanVerificationError) as caught:
            self.run_fake(runtime)
        self.assertEqual(caught.exception.reason, 'BROWSER_CLEANUP_FAILED')
        self.assertFalse(self.ev.browser_resources_closed)
        self.check_cleanup(runtime)

    def test_declared_provider_calls_handler_without_http_send(self):
        paths = []
        def handle(request):
            paths.append(request.url.path)
            return httpx.Response(200, json={'loginOptionsToken': 'fresh', 'authFlowId': 'flow', 'challengeProvider': 'hcaptcha'})
        with httpx.Client(transport=httpx.MockTransport(handle)) as client:
            wire = app.Wire(client, self.ev, time.monotonic() + 10, 'notion')
            handler = Mock(return_value='browser-state')
            signup = app.NotionSignup(wire, 'device', human_handler=handler)
            self.assertEqual(signup.send('user@example.com'), 'browser-state')
            handler.assert_called_once_with('user@example.com')
            self.assertEqual(paths, ['/api/v3/getLoginOptions'])


if __name__ == '__main__':
    unittest.main()
