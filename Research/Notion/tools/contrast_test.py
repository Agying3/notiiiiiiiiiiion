"""Contrast driver: isolates one variable per group (email vs exit IP).

Each group runs http_signup in a child process with a single send attempt and a
fixed mail wait, then records the redacted summary. Reasons to keep it: groups
must not share HTTP state, and the per-group budget must be enforceable.

Usage: python contrast_test.py A B C
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / 'Research/Notion/tools'
PRIVATE = ROOT / 'Research/Notion/local/http-signup'
PROXIES = ROOT / 'proxies.txt'
ACCOUNTS = ('Outlook_37_Account.txt', 'Hotmail_37_Account.txt')
MAIL_WAIT = 150
DEADLINE = 260
LONG_WAIT = 600
LONG_DEADLINE = 780


def used_emails() -> set[str]:
    seen: set[str] = set()
    for path in PRIVATE.glob('*/session.private.json'):
        try:
            seen.add(json.loads(path.read_text(encoding='utf-8'))['email'].lower())
        except (ValueError, KeyError, KeyboardInterrupt):
            continue
    for path in PRIVATE.glob('*reservations.private.jsonl'):
        for line in path.read_text(encoding='utf-8').splitlines():
            try:
                seen.add(json.loads(line)['email'].lower())
            except (ValueError, KeyError):
                continue
    return seen


def fresh_email() -> str:
    used = used_emails()
    for name in ACCOUNTS:
        for line in reversed((ROOT / name).read_text(encoding='utf-8-sig').splitlines()):
            fields = [x.strip() for x in line.strip().split('----')]
            if len(fields) >= 4 and fields[0].lower() not in used:
                return fields[0]
    raise SystemExit('NO_UNUSED_EMAIL')


def proxy_line(index: int) -> tuple[str, str, str, str]:
    lines = PROXIES.read_text(encoding='utf-8-sig').splitlines()
    host, port, user, password = lines[index - 1].strip().split(':', 3)
    return host, port, user, password


def check_proxy(index: int) -> str | None:
    host, port, user, password = proxy_line(index)
    url = str(httpx.URL('http://' + host + ':' + port, username=user, password=password))
    try:
        with httpx.Client(proxy=url, timeout=20, trust_env=False) as client:
            response = client.get('https://api.ipify.org?format=json')
            return response.json()['ip'] if response.status_code == 200 else None
    except Exception:
        return None


LOCAL_PROXY = 'http://127.0.0.1:18081'


def mailbox_size(email: str) -> int | None:
    """Return total message count for an account, or None when credentials fail."""
    record = next((line for name in ACCOUNTS
                   for line in (ROOT / name).read_text(encoding='utf-8-sig').splitlines()
                   if line.strip().split('----')[0].strip().lower() == email.lower()), None)
    if not record:
        return None
    fields = [x.strip() for x in record.split('----')]
    account = {'email': fields[0], 'client_id': fields[2], 'refresh_token': fields[3]}
    sys.path.insert(0, str(TOOLS))
    import http_signup as app
    directory = PRIVATE / ('probe-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    evidence = app.Evidence(directory)
    try:
        with httpx.Client(trust_env=False, follow_redirects=False) as client:
            wire = app.Wire(client, evidence, __import__('time').monotonic() + 60, 'microsoft')
            mailbox = app.GraphMailbox(account, wire)
            return len(mailbox.messages())
    except Exception:
        return None


def active_email() -> str:
    """Pick an unused account whose mailbox is confirmed non-empty."""
    used = used_emails()
    for name in ACCOUNTS:
        for line in reversed((ROOT / name).read_text(encoding='utf-8-sig').splitlines()):
            fields = [x.strip() for x in line.strip().split('----')]
            if len(fields) < 4 or fields[0].lower() in used:
                continue
            size = mailbox_size(fields[0])
            print(f'PROBE {fields[0][:2]}*** size={size}', flush=True)
            if size:
                return fields[0]
    raise SystemExit('NO_ACTIVE_EMAIL')



def run_group(label: str, email: str, proxy_index: int, proxy_url: str | None = None,
              wait: int = MAIL_WAIT, deadline: int = DEADLINE) -> dict:
    environment = dict(os.environ)
    if proxy_url:
        environment['NOTION_HTTP_PROXY'] = proxy_url
        network = ['--proxy-env', 'NOTION_HTTP_PROXY']
    else:
        host, port, user, password = proxy_line(proxy_index)
        environment['NOTION_HTTP_PROXY'] = str(
            httpx.URL('http://' + host + ':' + port, username=user, password=password))
        network = ['--proxy-env', 'NOTION_HTTP_PROXY']
    command = [sys.executable, '-X', 'utf8', str(TOOLS / 'http_signup.py'),
               '--email', email, *network,
               '--human-verification', '--human-timeout', '120',
               '--send-attempts', '1', '--mail-wait', str(wait),
               '--deadline', str(deadline)]


    started = datetime.now(timezone.utc)
    print(f'GROUP_{label}_START email={email[:2]}*** proxyIndex={proxy_index}', flush=True)
    completed = subprocess.run(command, env=environment, capture_output=True, text=True,
                               timeout=deadline + 120, cwd=str(ROOT))
    evidence = ''
    for line in completed.stdout.splitlines():
        if line.startswith('EVIDENCE_DIR='):
            evidence = line.split('=', 1)[1].strip()
    summary = {}
    if evidence and Path(evidence).exists():
        summary = json.loads((Path(evidence) / 'summary.json').read_text(encoding='utf-8'))
    record = {'group': label, 'email': email, 'proxyIndex': proxy_index,
              'network': proxy_url or 'datacenter_proxy',
              'startedAt': started.isoformat(), 'exitIp': summary.get('exitIp'),
              'status': summary.get('status'), 'stage': summary.get('stage'),
              'reason': summary.get('reason'), 'browserUsed': summary.get('browserUsed'),
              'resourcesClosed': summary.get('resourcesClosed'),
              'evidenceDir': evidence, 'childExit': completed.returncode}
    print('GROUP_' + label + '_RESULT=' + json.dumps(
        {k: record[k] for k in ('status', 'stage', 'reason', 'exitIp')}, ensure_ascii=False), flush=True)
    return record


def pick_email(filename: str, require_active: bool = False) -> str:
    """Pick an unused account from one pool file, optionally requiring mail history."""
    used = used_emails()
    candidates = []
    for line in (ROOT / filename).read_text(encoding='utf-8-sig').splitlines():
        fields = [x.strip() for x in line.strip().split('----')]
        if len(fields) >= 4 and fields[0].lower() not in used:
            candidates.append(fields[0])
    if not require_active:
        if not candidates:
            raise SystemExit('NO_UNUSED_EMAIL_IN_' + filename)
        return candidates[-1]
    for email in candidates:
        size = mailbox_size(email)
        print(f'PROBE {email[:2]}*** size={size}', flush=True)
        if size:
            return email
    raise SystemExit('NO_ACTIVE_EMAIL_IN_' + filename)


def main() -> int:
    plan = sys.argv[1:] or ['A', 'B', 'C']
    previous = json.loads((PRIVATE / 'hybrid-test-reservations.private.jsonl')
                          .read_text(encoding='utf-8').splitlines()[-1])
    records = []
    for label in plan:
        proxy_url = None
        if label == 'A':
            email, index = fresh_email(), 11
        elif label == 'B':
            email, index = previous['email'], 12
        elif label == 'C':
            email, index = fresh_email(), previous['proxyIndex']
        elif label == 'D':
            email, index, proxy_url = fresh_email(), 0, LOCAL_PROXY
        elif label == 'E':
            email, index, proxy_url = active_email(), 11, None
        elif label == 'F':
            email, index, proxy_url = pick_email('Hotmail_37_Account.txt'), 0, LOCAL_PROXY
        else:
            raise SystemExit('UNKNOWN_GROUP')
        if proxy_url is None and not check_proxy(index):
            records.append({'group': label, 'status': 'proxy_dead', 'proxyIndex': index,
                            'email': email})
            print('GROUP_' + label + '_RESULT=proxy_dead', flush=True)
            continue
        wait, deadline = (LONG_WAIT, LONG_DEADLINE) if label == 'E' else (MAIL_WAIT, DEADLINE)
        records.append(run_group(label, email, index, proxy_url, wait, deadline))

        with (PRIVATE / 'contrast-runs.private.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(records[-1], ensure_ascii=False) + '\n')
    print('CONTRAST_DONE=' + json.dumps(
        [{k: r.get(k) for k in ('group', 'status', 'reason', 'exitIp')} for r in records],
        ensure_ascii=False), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
