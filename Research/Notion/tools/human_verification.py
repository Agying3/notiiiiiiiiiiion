"""Optional, user-operated official signup verification; no challenge solving.

Only this module imports Playwright, lazily after explicit CLI selection.
The official page owns the challenge and one send request; HTTP owns login.
"""

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 YG
from __future__ import annotations

from dataclasses import dataclass
from http.cookiejar import Cookie
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid
from urllib.parse import urlsplit, unquote

APP = 'https://app.notion.com'
SEND_PATH = '/api/v3/sendTemporaryPassword'
BLOCKED_BROWSER_PATHS = {
    '/api/v3/loginWithEmail', '/api/v3/createSpace',
    '/api/v3/completeCurrentUserOnboarding',
}


class HumanVerificationError(Exception):
    def __init__(self, reason, help_text, exit_code=3):
        super().__init__(reason)
        self.reason, self.help_text, self.exit_code = reason, help_text, exit_code


@dataclass
class VerificationResult:
    state: str
    user_agent: str
    client_version: str
    sent_at: str
    browser_cookies: list[dict]
    device_id: str = ''


def notion_domain(domain: str) -> bool:
    return domain.lstrip('.').lower() in {'app.notion.com', 'notion.com', 'notion.so', 'www.notion.so'}


def export_cookies(client) -> list[dict]:
    result = []
    for cookie in client.cookies.jar:
        if not notion_domain(cookie.domain):
            continue
        item = {'name': cookie.name, 'value': cookie.value, 'domain': cookie.domain,
                'path': cookie.path or '/', 'secure': cookie.secure,
                'httpOnly': any(k.lower() == 'httponly' for k in cookie._rest),
                'sameSite': 'Lax'}
        if cookie.expires and cookie.expires > time.time():
            item['expires'] = cookie.expires
        result.append(item)
    return result


def import_cookies(client, browser_cookies: list[dict]) -> None:
    # {意图：浏览器发码后的 Cookie 是本轮最新状态；按域替换，避免旧值与新值并存。}
    for cookie in list(client.cookies.jar):
        if notion_domain(cookie.domain):
            client.cookies.jar.clear(cookie.domain, cookie.path, cookie.name)
    for item in browser_cookies:
        domain = item.get('domain', '')
        if not notion_domain(domain):
            continue
        expiry = item.get('expires', -1)
        expires = int(expiry) if expiry and expiry > 0 else None
        client.cookies.jar.set_cookie(Cookie(
            version=0, name=item['name'], value=item['value'], port=None, port_specified=False,
            domain=domain, domain_specified=domain.startswith('.'), domain_initial_dot=domain.startswith('.'),
            path=item.get('path', '/'), path_specified=True, secure=bool(item.get('secure')),
            expires=expires, discard=expires is None, comment=None, comment_url=None,
            rest={'HttpOnly': None} if item.get('httpOnly') else {}, rfc2109=False))


def proxy_options(proxy_url: str | None) -> dict | None:
    if not proxy_url:
        return None
    parsed = urlsplit(proxy_url)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or not parsed.port:
        raise HumanVerificationError('BROWSER_PROXY_UNSUPPORTED', '人工验证仅支持显式 HTTP/HTTPS 代理；未启动浏览器。', 2)
    hostname = '[' + parsed.hostname + ']' if ':' in parsed.hostname else parsed.hostname
    result = {'server': f'{parsed.scheme}://{hostname}:{parsed.port}'}
    if parsed.username is not None:
        result['username'] = unquote(parsed.username)
    if parsed.password is not None:
        result['password'] = unquote(parsed.password)
    return result


class SendGuard:
    def __init__(self, email: str, device_id: str, evidence, utc_now, allow_native_device=False):
        self.email, self.device_id, self.evidence, self.utc_now = email, device_id, evidence, utc_now
        self.allow_native_device = allow_native_device
        self.sent = False
        self.state = ''
        self.sent_at = ''
        self.user_agent = ''
        self.client_version = ''
        self.failure = None
        self.request_object = None

    def route(self, route, request) -> None:
        url = urlsplit(request.url)
        if url.scheme != 'https' or url.netloc != 'app.notion.com':
            route.continue_()
            return
        if url.path in BLOCKED_BROWSER_PATHS:
            self.evidence.event('browser_action_blocked', endpoint=url.path)
            route.abort()
            return
        if url.path != SEND_PATH:
            route.continue_()
            return
        if self.sent or self.failure:
            self.evidence.event('browser_duplicate_send_blocked')
            route.abort()
            return
        try:
            payload = request.post_data_json
        except Exception:
            payload = None
        if request.method != 'POST' or not isinstance(payload, dict):
            self.fail('BROWSER_SEND_INVALID', '官方发码请求结构变化，已停止。')
            route.abort()
            return
        if str(payload.get('email', '')).casefold() != self.email.casefold():
            self.fail('BROWSER_EMAIL_MISMATCH', '浏览器提交邮箱与本轮邮箱不同；已阻止发码。')
            route.abort()
            return
        if payload.get('deviceId') != self.device_id:
            try:
                native_device = str(uuid.UUID(str(payload.get('deviceId', ''))))
            except ValueError:
                native_device = ''
            if not self.allow_native_device or not native_device:
                self.fail('BROWSER_DEVICE_MISMATCH', '页面设备 ID 缺失或格式异常；已阻止发码。')
                route.abort()
                return
            self.evidence.event('browser_native_device_adopted',
                note='Official page generated a UUID distinct from the seed cookie; preserve its unmodified request')
            self.device_id = native_device
        self.sent = True
        self.request_object = request
        self.sent_at = self.utc_now()
        self.user_agent = request.headers.get('user-agent', '')
        self.client_version = request.headers.get('notion-client-version', '')
        self.evidence.event('browser_send_request', email=self.email, deviceId=self.device_id,
                            challengePresent=bool(payload.get('challengeToken')),
                            sentAt=self.sent_at)
        route.continue_()

    def response(self, response) -> None:
        if response.request is not self.request_object:
            return
        try:
            data = response.json()
        except Exception:
            data = None
        self.evidence.event('browser_send_response', status=response.status,
                            content=data if isinstance(data, dict) else {'nonJson': True})
        if response.status == 429:
            self.fail('RATE_LIMITED', '浏览器发码返回限流；已停止，不继续重发。')
        elif response.status >= 400 or not isinstance(data, dict) or not data.get('csrfState') or data.get('isNotionError'):
            self.fail('BROWSER_SEND_REJECTED', '官方页面本次发码未被接受；已停止，请查看脱敏响应。')
        else:
            self.state = data['csrfState']
            self.evidence.secrets.append(self.state)

    def request_failed(self, request) -> None:
        if request is self.request_object:
            self.fail('BROWSER_SEND_UNCONFIRMED', '发码连接中断，服务端是否已接受尚不确定；停止以免重复发码。')

    def fail(self, reason, help_text) -> None:
        if self.failure is None:
            self.failure = HumanVerificationError(reason, help_text)


def edge_executable() -> str:
    for candidate in (r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
                      r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'):
        if Path(candidate).exists():
            return candidate
    raise HumanVerificationError('EDGE_NOT_FOUND', '未找到 Microsoft Edge，可改用 --direct 或安装 Edge。', 2)


def launch_plain_edge(profile_dir: Path, port: int, proxy_url: str | None):
    """Start Edge as a normal process: no --enable-automation, no webdriver flag.

    Playwright's own launch injects automation switches that sites can detect.
    Attaching over CDP keeps the window indistinguishable from a user-started one
    apart from the debugging port itself.
    """
    profile_dir.mkdir(parents=True, exist_ok=True)
    command = [edge_executable(),
               f'--remote-debugging-port={port}',
               f'--user-data-dir={profile_dir}',
               '--remote-allow-origins=*',
               '--no-first-run', '--no-default-browser-check',
               '--disable-features=msEdgeFirstRunExperience',
               'about:blank']
    if proxy_url:
        parsed = urlsplit(proxy_url)
        if parsed.hostname and parsed.port:
            command.insert(1, f'--proxy-server={parsed.hostname}:{parsed.port}')
    else:
        command.insert(1, '--no-proxy-server')
    return subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def connect_plain_edge(driver, port: int, timeout: float = 20.0):
    """Poll the CDP endpoint until the plain Edge window is reachable."""
    end = time.monotonic() + timeout
    last = None
    while time.monotonic() < end:
        try:
            return driver.chromium.connect_over_cdp(f'http://127.0.0.1:{port}')
        except Exception as exc:
            last = exc
            time.sleep(0.5)
    raise HumanVerificationError('BROWSER_ATTACH_FAILED', f'普通 Edge 启动后无法附着调试端口：{type(last).__name__}')


def verify_and_send(*, email, device_id, client, evidence, proxy_url, expected_ip,
                    deadline, timeout, utc_now, manager_factory=None,
                    plain_edge: bool = False, profile_dir: Path | None = None) -> VerificationResult:
    """Wait for a person to use the official page; never click or solve a challenge."""
    options = proxy_options(proxy_url)
    if manager_factory is None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise HumanVerificationError('BROWSER_DEPENDENCY_MISSING', '请安装可选 playwright 依赖；纯 HTTP 模式仍可使用。', 2) from exc
        manager_factory = sync_playwright
    until = min(deadline, time.monotonic() + timeout)
    guard = SendGuard(email, device_id, evidence, utc_now, allow_native_device=True)
    browser = context = manager = driver = None
    edge_process = None
    closed = {'context': True, 'browser': True, 'driver': True}
    result = None
    def budget_ms():
        remaining = until - time.monotonic()
        if remaining <= 0:
            raise HumanVerificationError('HUMAN_VERIFICATION_TIMEOUT', '人工验证达到时限；临时浏览器将关闭，本轮停止。', 4)
        return max(1, min(20000, int(remaining * 1000)))
    try:
        manager = manager_factory()
        driver = manager.start()
        closed['driver'] = False
        budget_ms()
        if plain_edge:
            port = 9000 + (os.getpid() % 500)
            target_profile = profile_dir or (Path(tempfile.gettempdir()) / f'plain-edge-{port}')
            edge_process = launch_plain_edge(target_profile, port, proxy_url)
            browser = connect_plain_edge(driver, port)
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            evidence.event('browser_launch_mode', mode='plain_edge_cdp',
                           note='No automation switches; attached over CDP')
        else:
            browser = driver.chromium.launch(channel='msedge', headless=False, proxy=options,
                args=['--no-proxy-server'] if options is None else [], timeout=budget_ms())
            context = None
        closed['browser'] = False
        if not plain_edge:
            context = browser.new_context(locale='zh-CN', service_workers='block')
        closed['context'] = False
        context.set_default_timeout(budget_ms())
        context.add_cookies(export_cookies(client))
        device_cookies = [c for c in context.cookies(APP) if c['name'] == 'notion_browser_id']
        if len(device_cookies) != 1 or device_cookies[0]['value'] != device_id:
            raise HumanVerificationError('BROWSER_DEVICE_MISMATCH', '临时浏览器中的设备 Cookie 未正确继承；未发码。')
        context.route('**/api/v3/**', guard.route)
        context.on('response', guard.response)
        context.on('requestfailed', guard.request_failed)
        evidence.event('browser_opened', purpose='user-operated official verification and one send request')
        page = context.pages[0] if (plain_edge and context.pages) else context.new_page()
        # Exit check must use the browser's own proxy; Playwright's request context bypasses it.
        if plain_edge:
            try:
                page.goto('https://api.ipify.org?format=json', wait_until='domcontentloaded',
                          timeout=budget_ms())
                actual_ip = json.loads(page.inner_text('body')).get('ip')
            except Exception:
                actual_ip = None
        else:
            ip_response = context.request.get('https://api.ipify.org?format=json', timeout=budget_ms())
            try:
                actual_ip = ip_response.json().get('ip') if ip_response.status == 200 else None
            except Exception:
                actual_ip = None
        if actual_ip != expected_ip:
            raise HumanVerificationError('BROWSER_EXIT_MISMATCH', '临时浏览器出口与 HTTP 出口不同或核验失败；未发码，请使用固定出口代理。')
        evidence.event('browser_exit_verified', exitIp=actual_ip)
        page.goto(APP + '/signup', wait_until='domcontentloaded', timeout=budget_ms())
        print('ACTION_REQUIRED=若临时 Edge 出现人机验证，请手动完成；不要输入邮件验证码。', flush=True)
        print('SIGNUP_EMAIL=程序会在官方页面填入本轮邮箱并提交；不操作验证题目。', flush=True)
        print('BROWSER_WILL_CLOSE=发码成功后自动关闭，再由 HTTP 收码和登录。', flush=True)
        email_input = page.locator('input[type="email"]')
        email_input.fill(email, timeout=budget_ms())
        email_input.press('Enter', timeout=budget_ms())
        evidence.event('browser_email_submitted', action='ordinary email form only; captcha remains user-operated')
        while not guard.state:
            if guard.failure:
                raise guard.failure
            budget_ms()
            if page.is_closed():
                raise HumanVerificationError('HUMAN_BROWSER_CLOSED', '临时浏览器被关闭；本轮暂停。')
            page.wait_for_timeout(min(200, budget_ms()))
        # Do not use or export hCaptcha tokens: the official page already submitted once.
        browser_cookies = context.cookies()
        user_agent = guard.user_agent or page.evaluate('navigator.userAgent')
        if not user_agent:
            raise HumanVerificationError('BROWSER_HANDOFF_INVALID', '发码已接受，但缺少后续会话参数；保留状态并停止。')
        result = VerificationResult(guard.state, user_agent, guard.client_version,
                                    guard.sent_at, browser_cookies, guard.device_id)
        evidence.write('browser-handoff.private.json', {
            'state': result.state, 'sentAt': result.sent_at, 'deviceId': result.device_id,
            'userAgent': result.user_agent, 'clientVersion': result.client_version,
            'cookies': result.browser_cookies}, private=True)
    except HumanVerificationError:
        raise
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        evidence.event('browser_error', error=type(exc).__name__)
        raise HumanVerificationError('BROWSER_ERROR', '临时浏览器遇到异常，已进入资源清理；请查看错误类型。') from exc
    finally:
        for name, resource in (('context', context), ('browser', browser)):
            if resource is not None:
                try:
                    resource.close()
                    closed[name] = True
                except Exception as exc:
                    evidence.event('browser_cleanup_error', resource=name, error=type(exc).__name__)
        if driver is not None:
            try:
                driver.stop()
                closed['driver'] = True
            except Exception as exc:
                evidence.event('browser_cleanup_error', resource='driver', error=type(exc).__name__)
        if edge_process is not None:
            try:
                edge_process.terminate()
                edge_process.wait(timeout=15)
            except Exception:
                try:
                    edge_process.kill()
                except Exception as exc:
                    evidence.event('browser_cleanup_error', resource='edge_process',
                                   error=type(exc).__name__)
        evidence.write('browser-cleanup.json', closed)
        evidence.event('browser_closed', **closed)
    if not all(closed.values()):
        raise HumanVerificationError('BROWSER_CLEANUP_FAILED', '临时浏览器释放未全部确认；暂停后续流程，请核查残留进程。')
    return result
