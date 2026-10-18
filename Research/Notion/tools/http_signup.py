"""Browser-first-hybrid Notion signup helper (HTTP-first, optional user verification).

SPDX-License-Identifier: AGPL-3.0-or-later
Copyright (C) 2026 YG

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version. See LICENSE for the full text.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[3]
APP = 'https://app.notion.com'
GRAPH = 'https://graph.microsoft.com/v1.0'
TOKEN = 'https://login.microsoftonline.com/consumers/oauth2/v2.0/token'
PRIVATE_ROOT = ROOT / 'Research/Notion/local/http-signup'
SENSITIVE = re.compile(r'password|token|cookie|authorization|csrf|secret|^state$|bodypreview|^body$|authflowid', re.I)
EMAIL = re.compile(r'[\w.+-]+(?:@|%40)[\w.-]+\.[A-Za-z]{2,}')
CODE = re.compile(r'(?<!\d)(\d{6})(?!\d)')


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.isoformat(timespec='seconds')


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timestamp must include a timezone')
    return parsed.astimezone(timezone.utc)


def redact(value: Any, secrets: tuple[str, ...] = ()) -> Any:
    if isinstance(value, dict):
        return {str(k): '[REDACTED]' if SENSITIVE.search(str(k)) else redact(v, secrets)
                for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, secrets) for v in value]
    if isinstance(value, str):
        for secret in sorted((s for s in secrets if s), key=len, reverse=True):
            value = value.replace(secret, '[REDACTED]')
        value = re.sub(r'https?://[^\s/@]+:[^\s/@]+@', 'https://[REDACTED]@', value)
        value = re.sub(r'v02:[A-Za-z0-9_:.-]+|P1_[A-Za-z0-9_.-]+', '[REDACTED]', value)
        value = EMAIL.sub('[EMAIL]', value)
        return CODE.sub('[CODE]', value)
    return value


class StopRun(Exception):
    def __init__(self, reason: str, help_text: str, exit_code: int = 3):
        super().__init__(reason)
        self.reason, self.help_text, self.exit_code = reason, help_text, exit_code


class Evidence:
    def __init__(self, directory: Path):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=False)
        self.secrets: list[str] = []
        self.counter = 0
        self.browser_used = False
        self.browser_resources_closed = True

    def event(self, kind: str, **data: Any) -> None:
        if kind == 'browser_opened':
            self.browser_used = True
            self.browser_resources_closed = False
        elif kind == 'browser_closed':
            self.browser_resources_closed = all(data.get(k) is True for k in ('context', 'browser', 'driver'))
        record = redact({'utc': iso(now()), 'kind': kind, **data}, tuple(self.secrets))
        with (self.directory / 'events.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + '\n')

    def write(self, filename: str, value: Any, private: bool = False) -> None:
        if not private:
            value = redact(value, tuple(self.secrets))
        (self.directory / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


class Wire:
    def __init__(self, client: httpx.Client, evidence: Evidence, deadline: float, service: str):
        self.client, self.evidence, self.deadline, self.service = client, evidence, deadline, service

    def remaining(self) -> float:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise StopRun('DEADLINE_EXCEEDED', '已到总时限；请查看本轮状态，先检查已有账号/工作区，避免重复创建。', 4)
        return remaining

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        # {意图：写请求超时可能已在上游成功，因此停止并保留状态；不自动重放创建请求。}
        # Mutations are never retried here: an ambiguous timeout can hide success.
        remaining = self.remaining()
        self.evidence.counter += 1
        sequence = self.evidence.counter
        self.evidence.event('request', sequence=sequence, service=self.service, method=method,
                            url=url, json=kwargs.get('json'), form=kwargs.get('data'))
        timeout = min(20.0, max(0.1, remaining / 5))
        try:
            response = self.client.request(method, url, timeout=timeout, **kwargs)
        except httpx.TransportError as exc:
            self.evidence.event('transport_error', sequence=sequence, error=type(exc).__name__)
            raise StopRun('NETWORK_ERROR', '网络请求未确认完成；本轮已暂停，不自动重复创建账号或工作区。') from exc
        try:
            content = response.json()
        except ValueError:
            # HTML can contain embedded session data; keep size/hash, not raw markup.
            content = {'nonJsonBytes': len(response.content),
                       'sha256': hashlib.sha256(response.content).hexdigest()}
        self.evidence.event('response', sequence=sequence, status=response.status_code,
                            headers={k: v for k, v in response.headers.items()
                                     if k.lower() in {'content-type', 'retry-after', 'x-notion-user-id'}},
                            content=content)
        if response.status_code == 429:
            raise StopRun('RATE_LIMITED', '服务端限流；已暂停。按 Retry-After 等待后再处理，不立即换环境继续请求。')
        if response.status_code >= 500:
            raise StopRun('SERVICE_ERROR', '上游服务异常；已暂停，留痕中包含服务名和 HTTP 状态码。')
        return response

    def json(self, method: str, url: str, **kwargs: Any) -> dict:
        response = self.request(method, url, **kwargs)
        if response.status_code >= 400:
            raise StopRun('HTTP_ERROR', f'{self.service} 返回 HTTP {response.status_code}；查看脱敏响应。')
        try:
            data = response.json()
        except ValueError as exc:
            raise StopRun('NON_JSON_RESPONSE', f'{self.service} 返回非 JSON 页面，可能是登录页或验证页面；已暂停。') from exc
        if not isinstance(data, dict):
            raise StopRun('UNEXPECTED_RESPONSE', f'{self.service} 响应结构发生变化。')
        return data


class GraphMailbox:
    def __init__(self, account: dict, wire: Wire):
        self.account, self.wire = account, wire
        self.token = ''
        self.expires_at = 0.0
        self.seen: set[str] = set()
        self._folders: list[tuple[str, str]] = []

    def authorize(self) -> None:
        if self.token and time.monotonic() < self.expires_at:
            return
        data = self.wire.json('POST', TOKEN, data={
            'client_id': self.account['client_id'], 'grant_type': 'refresh_token',
            'refresh_token': self.account['refresh_token'],
            'scope': 'https://graph.microsoft.com/Mail.Read offline_access'})
        self.token = data.get('access_token', '')
        if not self.token:
            raise StopRun('MAIL_TOKEN_MISSING', '微软响应未包含 access_token。')
        self.wire.evidence.secrets.append(self.token)
        self.expires_at = time.monotonic() + max(1, int(data.get('expires_in', 3600)) - 60)
        if data.get('refresh_token'):
            self.account['refresh_token'] = data['refresh_token']
            self.wire.evidence.secrets.append(data['refresh_token'])
            self.wire.evidence.write('mail-account.private.json', self.account, private=True)
        identity = self.wire.json('GET', GRAPH + '/me', params={'$select': 'mail,userPrincipalName'},
                                  headers={'Authorization': 'Bearer ' + self.token})
        addresses = {str(identity.get(k, '')).strip().casefold() for k in ('mail', 'userPrincipalName')}
        if self.account['email'].casefold() not in addresses:
            raise StopRun('MAIL_IDENTITY_MISMATCH', 'OAuth 凭据对应的微软账号与目标邮箱不一致；先核实账号字段或别名。')

    def folder_ids(self) -> list[tuple[str, str]]:
        # {意图：只查 inbox/junkemail 会漏掉服务器端规则或分类移动后的邮件；先枚举全部文件夹及子文件夹。}
        if self._folders:
            return self._folders
        headers = {'Authorization': 'Bearer ' + self.token}
        found: list[tuple[str, str]] = []
        visited: set[str] = set()
        queue = list(self.wire.json('GET', GRAPH + '/me/mailFolders',
                                    params={'$top': '100', '$select': 'id,displayName'},
                                    headers=headers).get('value') or [])
        while queue and len(found) < 200:
            folder = queue.pop(0)
            folder_id = str(folder.get('id') or '')
            if not folder_id or folder_id in visited:
                continue
            visited.add(folder_id)
            found.append((folder_id, str(folder.get('displayName', ''))))
            queue.extend(self.wire.json('GET', GRAPH + f'/me/mailFolders/{folder_id}/childFolders',
                                        params={'$top': '100', '$select': 'id,displayName'},
                                        headers=headers).get('value') or [])
        self._folders = found
        return found

    def messages(self) -> list[dict]:
        self.authorize()
        results = []
        seen_ids: set[str] = set()
        # 全文件夹轮询含服务器端规则移动与子文件夹；浅表 inbox/junkemail 覆盖已实测会漏。
        for folder_id, name in self.folder_ids():
            url = GRAPH + f'/me/mailFolders/{folder_id}/messages'
            params = {'$top': '50', '$orderby': 'receivedDateTime desc',
                      '$select': 'id,subject,from,receivedDateTime,bodyPreview'}
            data = self.wire.json('GET', url, params=params,
                                  headers={'Authorization': 'Bearer ' + self.token})
            messages = data.get('value')
            if not isinstance(messages, list):
                raise StopRun('MAIL_RESPONSE_INVALID', '微软邮件列表缺少 value；不会将读取错误当成空收件箱。')
            fresh = [m for m in messages if m.get('id') and m['id'] not in seen_ids]
            seen_ids.update(m['id'] for m in fresh)
            self.wire.evidence.event('mail_folder', folder=name, count=len(fresh))
            results.extend(fresh)
        return results


    def baseline(self) -> None:
        # {意图：发码前先记住现有邮件 ID；后续只接受新邮件，避免历史码或邮箱时钟差造成误判。}
        self.seen = {m['id'] for m in self.messages() if m.get('id')}

    @staticmethod
    def extract(message: dict) -> str | None:
        return GraphMailbox.extract_from(message)

    @staticmethod
    def extract_from(message: dict, full_body: str = '') -> str | None:
        address = str((message.get('from') or {}).get('emailAddress', {}).get('address', ''))
        domain = address.rsplit('@', 1)[-1].casefold()
        if domain not in {'makenotion.com', 'notion.so', 'notion.com'}:
            return None
        subject = str(message.get('subject', ''))
        preview = str(message.get('bodyPreview', ''))
        full_body = full_body or ''
        if not re.search(r'code|验证码|校验码|passcode|otp', subject + '\n' + preview + '\n' + full_body, re.I):
            return None
        for text in (subject + '\n' + preview, full_body):
            match = CODE.search(text)
            if match:
                return match.group(1)
        return None

    def body_text(self, message_id: str) -> str:
        """Fetch the full body only when the preview did not expose a code."""
        data = self.wire.json('GET', GRAPH + f'/me/messages/{message_id}',
                              params={'$select': 'body'},
                              headers={'Authorization': 'Bearer ' + self.token})
        body = data.get('body') or {}
        content = str(body.get('content', ''))
        # Strip tags; markup may split one code across spans, so rejoin digits.
        plain = re.sub(r'<[^>]+>', ' ', content)
        return re.sub(r'(?<=\d)\s+(?=\d)', '', plain)

    def wait(self, since: datetime, seconds: int, poll: float) -> str | None:
        until = min(self.wire.deadline, time.monotonic() + seconds)
        while time.monotonic() < until:
            for message in self.messages():
                if not message.get('id') or message['id'] in self.seen:
                    continue
                try:
                    received = parse_time(message['receivedDateTime'])
                except (ValueError, KeyError, TypeError):
                    continue
                if received < since - timedelta(seconds=10):
                    continue
                code = self.extract(message)
                if not code and self.extract(message) is None:
                    # {意图：预览可能不含验证码；仅在发件域匹配时才拉完整正文，避免无谓请求。}
                    address = str((message.get('from') or {}).get('emailAddress', {}).get('address', ''))
                    if address.rsplit('@', 1)[-1].casefold() in {'makenotion.com', 'notion.so', 'notion.com'}:
                        try:
                            code = self.extract_from(message, self.body_text(message['id']))
                        except StopRun:
                            code = None
                if code:
                    self.wire.evidence.secrets.append(code)
                    self.seen.add(message['id'])
                    self.wire.evidence.event('code_received', receivedAt=iso(received))
                    return code
            remaining = until - time.monotonic()
            if remaining > 0:
                time.sleep(min(poll, remaining))
        return None


class NotionSignup:
    def __init__(self, wire: Wire, device_id: str, version: str = '', human_handler=None):
        self.wire, self.device_id, self.version = wire, device_id, version
        self.human_handler = human_handler
        self.user_id = ''
        self.space_id = ''
        self.wire.client.cookies.set('notion_browser_id', device_id, domain='app.notion.com', path='/')
        self.wire.client.headers.update({'Origin': APP, 'Referer': APP + '/signup',
                                         'notion-audit-log-platform': 'web'})
        if version:
            self.wire.client.headers['notion-client-version'] = version

    def api(self, name: str, payload: dict) -> dict:
        response = self.wire.request('POST', APP + '/api/v3/' + name, json=payload)
        try:
            data = response.json()
        except ValueError as exc:
            raise StopRun('NOTION_CHALLENGE_OR_HTML', 'Notion 返回 HTML 而非 API 响应；需要额外交互，HTTP 任务已暂停。') from exc
        if not isinstance(data, dict):
            raise StopRun('NOTION_SCHEMA_CHANGED', 'Notion 响应结构变化，已暂停。')
        if response.status_code >= 400 or data.get('isNotionError'):
            error_type = str((data.get('clientData') or {}).get('type', ''))
            if name == 'sendTemporaryPassword' or 'captcha' in error_type.casefold():
                raise StopRun('SIGNUP_BLOCKED_OR_CHALLENGE', '服务端未接受发码或要求交互验证；纯 HTTP 无浏览器回退。请核查脱敏响应。')
            raise StopRun('NOTION_API_ERROR', f'{name} 返回 HTTP {response.status_code}；已暂停。')
        return data

    def bootstrap(self) -> None:
        response = self.wire.request('GET', APP + '/signup')
        if response.status_code != 200:
            raise StopRun('BOOTSTRAP_BLOCKED', '注册入口未正常响应，已暂停。')
        if not self.version:
            match = re.search(r'(?<!\d)(\d{2}\.\d{2}\.\d{8}\.\d{4})(?!\d)', response.text)
            if match:
                self.version = match.group(1)
                self.wire.client.headers['notion-client-version'] = self.version
        self.wire.evidence.event('bootstrap', clientVersion=self.version or 'not_discovered')

    def send(self, email: str) -> str:
        options = self.api('getLoginOptions', {'email': email, 'requireWorkTypeEmail': False})
        if not options.get('loginOptionsToken') or not options.get('authFlowId'):
            raise StopRun('LOGIN_OPTIONS_MISSING', '登录参数缺失；不会重放历史登录令牌。')
        self.wire.evidence.event('login_options', challengeProvider=options.get('challengeProvider'),
                                  note='provider declaration alone does not prove an interactive challenge is required')
        # {意图：启用人工模式时，在官方页面提交一次发码；不先发失败请求，也不提取/重放挑战 token。}
        if options.get('challengeProvider') == 'hcaptcha' and self.human_handler:
            return self.human_handler(email)
        result = self.api('sendTemporaryPassword', {
            'email': email, 'disableLoginLink': False, 'native': False, 'isSignup': True,
            'shouldHidePasscode': False, 'loginOptionsToken': options['loginOptionsToken'],
            'authFlowId': options['authFlowId'], 'deviceId': self.device_id, 'loginRouteOrigin': 'signup'})
        state = result.get('csrfState')
        if not state:
            raise StopRun('MAIL_STATE_MISSING', '发码响应未包含 csrfState，已暂停。')
        self.wire.evidence.secrets.append(state)
        self.wire.evidence.event('mail_request_accepted', delivered=False)
        return state

    def login(self, state: str, code: str) -> dict:
        result = self.api('loginWithEmail', {'state': state, 'password': code,
                                           'appSource': 'notion', 'loginRouteOrigin': 'signup'})
        self.user_id = result.get('userId', '')
        if not self.user_id:
            raise StopRun('LOGIN_USER_MISSING', '验证码提交后缺少用户标识；不会继续创建工作区。')
        self.wire.client.headers['x-notion-active-user-header'] = self.user_id
        self.api('authValidate', {})
        return result

    def onboard(self, display_name: str) -> tuple[str, dict]:
        self.wire.client.headers['Referer'] = APP + '/onboarding'
        validation = self.api('validateUserCanCreateWorkspace', {})
        if validation.get('canUserCreateSpace') is not True:
            raise StopRun('WORKSPACE_CREATION_BLOCKED', '服务端未允许创建工作区。')
        self.api('updateCurrentUserProfile', {'name': display_name})
        # First questionnaire = Work. Skip optional job role; no fabricated Sales answer.
        result = self.api('createSpace', {'name': display_name + "'s Space", 'icon': '💼',
            'planType': 'team', 'planSelection': 'team', 'initialPersona': 'unfilled',
            'domainType': 'personal', 'deviceId': self.device_id, 'deviceType': 'web-desktop',
            'source': 'handle_root_redirect', 'createSpaceView': True})
        space_id = result.get('spaceId', '')
        if not space_id:
            raise StopRun('WORKSPACE_ID_MISSING', '创建工作区响应缺少 spaceId；请检查已有工作区，不要盲目重建。')
        self.space_id = space_id
        # Persist immediately: subsequent offer calls may fail after creation succeeded.
        self.wire.evidence.write('progress.json', {'stage': 'workspace_created', 'spaceId': space_id})
        offers = {}
        for endpoint in ('getPossibleOffers', 'getEligibleIntervalSelectCampaigns',
                         'getBillingSubscriptionBannerData', 'getSubscriptionBanner'):
            offers[endpoint] = self.api(endpoint, {'spaceId': space_id})
        completion = self.api('completeCurrentUserOnboarding', {'completion': 'standard'})
        users = completion.get('recordMap', {}).get('notion_user', {})
        user = users.get(self.user_id, {}).get('value', {})
        if isinstance(user.get('value'), dict):
            user = user['value']
        if user.get('onboarding_completed') is not True:
            raise StopRun('ONBOARDING_UNVERIFIED', '完成接口未返回 onboarding_completed=true；工作区已记录，需核实最终状态。')
        return space_id, offers


def load_account(email: str, files: list[Path]) -> dict:
    for path in files:
        if not path.exists():
            continue
        with path.open(encoding='utf-8-sig') as stream:
            for line in stream:
                fields = [v.strip() for v in line.strip().split('----')]
                if len(fields) >= 4 and fields[0].casefold() == email.casefold():
                    return {'email': fields[0], 'client_id': fields[2], 'refresh_token': fields[3]}
    raise StopRun('ACCOUNT_NOT_FOUND', '账号文件中没有该邮箱的 OAuth 字段。', 2)


def cookies(client: httpx.Client) -> list[dict]:
    return [{'name': c.name, 'value': c.value, 'domain': c.domain, 'path': c.path,
             'secure': c.secure, 'expires': c.expires, 'rest': dict(c._rest)} for c in client.cookies.jar]


def execute(args: argparse.Namespace, evidence: Evidence) -> dict:
    account = load_account(args.email, args.account_file)
    evidence.secrets.extend([account['refresh_token'], account['email']])
    proxy = None if args.direct else os.environ.get(args.proxy_env)
    if not args.direct and not proxy:
        raise StopRun('PROXY_NOT_CONFIGURED', f'请设置环境变量 {args.proxy_env}，或显式使用 --direct。', 2)
    if proxy:
        evidence.secrets.append(proxy)
    device_id = str(uuid.uuid4())
    deadline = time.monotonic() + args.deadline
    summary: dict = {'status': 'running', 'stage': 'preflight', 'deviceId': device_id,
                     'transport': 'httpx', 'networkMode': 'direct' if args.direct else 'explicit_proxy',
                     'browserUsed': False, 'questionnaire': 'work', 'jobRole': 'skipped',
                     'startedAt': iso(now()), 'maxSendAttempts': args.send_attempts}
    with httpx.Client(proxy=proxy, trust_env=False, follow_redirects=False,
                      headers={'User-Agent': 'NotionHttpSignup/1.0', 'Accept': 'application/json'}) as notion_client, \
         httpx.Client(trust_env=False, follow_redirects=False) as mail_client:
        notion_wire = Wire(notion_client, evidence, deadline, 'notion')
        mail_wire = Wire(mail_client, evidence, deadline, 'microsoft')
        notion = NotionSignup(notion_wire, device_id, args.client_version)
        mailbox = GraphMailbox(account, mail_wire)
        if args.human_verification:
            def human_handler(email):
                nonlocal device_id
                from human_verification import verify_and_send, import_cookies, HumanVerificationError
                summary['stage'] = 'human_verification'
                try:
                    result = verify_and_send(email=email, device_id=device_id,
                        client=notion_client, evidence=evidence, proxy_url=proxy,
                        expected_ip=summary['exitIp'], deadline=deadline,
                        timeout=args.human_timeout, utc_now=lambda: iso(now()),
                        plain_edge=getattr(args, 'plain_edge', False))
                except HumanVerificationError as exc:
                    raise StopRun(exc.reason, exc.help_text, exc.exit_code) from exc
                import_cookies(notion_client, result.browser_cookies)
                if result.device_id:
                    device_id = notion.device_id = result.device_id
                    summary['deviceId'] = result.device_id
                notion_client.headers['User-Agent'] = result.user_agent
                if result.client_version:
                    notion.version = result.client_version
                    notion_client.headers['notion-client-version'] = result.client_version
                evidence.secrets.append(result.state)
                evidence.event('http_handoff_ready', sentAt=result.sent_at,
                               note='Official page already sent; HTTP will not resend')
                summary['stage'] = 'send_code'
                return result.state
            notion.human_handler = human_handler
        try:
            # Verify proxy routing without browser or exposing proxy credentials.
            summary['stage'] = 'network_check'
            response = notion_wire.request('GET', 'https://api.ipify.org?format=json')
            if response.status_code != 200:
                raise StopRun('EXIT_IP_UNVERIFIED', '出口 IP 核验失败，未发码。')
            try:
                summary['exitIp'] = response.json()['ip']
            except (ValueError, KeyError, TypeError) as exc:
                raise StopRun('EXIT_IP_UNVERIFIED', '出口服务响应结构变化，未发码。') from exc
            evidence.event('identity', deviceId=device_id, exitIp=summary['exitIp'],
                           fingerprint='HTTP session only; no browser fingerprint emulation')
            summary['stage'] = 'mail_preflight'
            mailbox.baseline()
            summary['stage'] = 'notion_bootstrap'
            notion.bootstrap()
            if args.preflight_only:
                options = notion.api('getLoginOptions', {'email': account['email'], 'requireWorkTypeEmail': False})
                if not options.get('loginOptionsToken') or not options.get('authFlowId'):
                    raise StopRun('LOGIN_OPTIONS_MISSING', '登录参数缺失；联通性检查未通过。')
                summary.update(status='preflight_ok', stage='ready', sendAttempts=0,
                               challengeProvider=options.get('challengeProvider'),
                               note='Network and mailbox checked; no email sent and no account created.')
                return summary
            code = state = None
            for attempt in range(1, args.send_attempts + 1):
                summary.update(stage='send_code', sendAttempts=attempt)
                sent_at = now()
                state = notion.send(account['email'])
                evidence.write('pending-auth.private.json', {'email': account['email'], 'state': state,
                    'deviceId': device_id, 'sentAt': iso(sent_at), 'cookies': cookies(notion_client)}, private=True)
                summary['stage'] = 'wait_mail'
                print(f'STAGE=wait_mail ATTEMPT={attempt}', flush=True)
                code = mailbox.wait(sent_at, args.mail_wait, args.poll_interval)
                if code:
                    break
                evidence.event('mail_timeout', attempt=attempt,
                    note='No matching new mail observed; cause and actual delivery status remain unknown')
                if attempt < args.send_attempts:
                    remaining_cooldown = args.resend_cooldown - (now() - sent_at).total_seconds()
                    if remaining_cooldown > 0:
                        time.sleep(min(remaining_cooldown, notion_wire.remaining()))
            if not code:
                raise StopRun('MAIL_NOT_OBSERVED', '轮询时段内未见新验证码；这不等于 Notion 未发信。请核对官方邮箱与账号凭据，不自动换号继续。')
            summary['stage'] = 'login'
            login = notion.login(state, code)
            summary.update(userId=notion.user_id, isNewSignup=login.get('isNewSignup'))
            # Avoid adding a workspace to an existing account on an ambiguous address.
            if login.get('isNewSignup') is not True:
                raise StopRun('EXISTING_ACCOUNT', '登录成功，但这是已有账号；已保存会话，未额外创建工作区。')
            summary['stage'] = 'onboarding'
            space_id, offers = notion.onboard(args.name or args.email.split('@')[0])
            evidence.write('offers.json', offers)
            summary.update(status='completed', stage='completed', spaceId=space_id,
                           trialActivated=False, paymentSubmitted=False,
                           note='Offer API responses saved; no browser UI display or trial duration inferred.')
        except StopRun as exc:
            summary.update(status='paused', reason=exc.reason, help=exc.help_text, exitCode=exc.exit_code)
        finally:
            evidence.write('session.private.json', {'email': account['email'], 'deviceId': device_id,
                'userId': notion.user_id, 'clientVersion': notion.version,
                'cookies': cookies(notion_client)}, private=True)
            if notion.space_id:
                summary['spaceId'] = notion.space_id
            summary.update(finishedAt=iso(now()), requestCount=evidence.counter,
                           browserUsed=evidence.browser_used)
            evidence.write('summary.json', summary)
    return summary


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='Single-account HTTP-first signup; optional user-operated Edge verification')
    p.add_argument('--email', required=True)
    p.add_argument('--account-file', action='append', type=Path)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--direct', action='store_true')
    group.add_argument('--proxy-env', metavar='ENV_NAME', help='environment variable containing a proxy URL')
    p.add_argument('--preflight-only', action='store_true', help='check HTTP and mailbox only; do not send code or create account')
    p.add_argument('--human-verification', action='store_true', help='open ordinary Edge for user-operated official verification/send only')
    p.add_argument('--human-timeout', type=int, default=180, help='maximum seconds for manual verification, also bounded by deadline')
    p.add_argument('--plain-edge', action='store_true',
                   help='launch Edge as a normal process and attach over CDP (no automation switches)')
    p.add_argument('--name')
    p.add_argument('--client-version', default='', help='optional current version; otherwise detect from signup HTML')
    p.add_argument('--mail-wait', type=int, default=180)
    p.add_argument('--poll-interval', type=float, default=10)
    p.add_argument('--send-attempts', type=int, choices=(1, 2, 3), default=1)
    p.add_argument('--resend-cooldown', type=int, default=60)
    p.add_argument('--deadline', type=int, default=900)
    p.add_argument('--output', type=Path, default=PRIVATE_ROOT)
    return p


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    p = parser()
    args = p.parse_args(argv)
    if args.mail_wait < 1 or args.poll_interval < 1 or args.deadline < 1 or args.resend_cooldown < 60:
        p.error('positive wait/deadline and resend cooldown >= 60 seconds required')
    if args.human_timeout < 1:
        p.error('human timeout must be positive')
    if args.human_verification and args.send_attempts != 1:
        p.error('human verification requires --send-attempts 1 to prevent duplicate sends')
    args.account_file = args.account_file or [ROOT / 'Outlook_37_Account.txt', ROOT / 'Hotmail_37_Account.txt']
    directory = args.output / (now().strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
    evidence = Evidence(directory)
    print('EVIDENCE_DIR=' + str(directory), flush=True)
    try:
        result = execute(args, evidence)
    except StopRun as exc:
        result = {'status': 'paused', 'reason': exc.reason, 'help': exc.help_text, 'exitCode': exc.exit_code}
    except KeyboardInterrupt:
        result = {'status': 'paused', 'reason': 'INTERRUPTED', 'exitCode': 130}
    except Exception as exc:
        # Do not dump exception text: libraries can include full URLs or credentials.
        evidence.event('unexpected_error', error=type(exc).__name__)
        result = {'status': 'error', 'reason': 'UNEXPECTED_ERROR', 'errorType': type(exc).__name__, 'exitCode': 5}
    result['browserUsed'] = evidence.browser_used
    result['resourcesClosed'] = evidence.browser_resources_closed
    evidence.write('summary.json', result)
    print(json.dumps(redact(result, tuple(evidence.secrets)), ensure_ascii=False), flush=True)
    return 0 if result['status'] in {'completed', 'preflight_ok'} else result.get('exitCode', 3)


if __name__ == '__main__':
    raise SystemExit(main())
