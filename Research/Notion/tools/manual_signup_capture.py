"""Headed manual signup capture. Local raw files contain private session data."""

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 YG
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import time
from datetime import datetime, timezone

import httpx
from browser_launch import launch, HAVE_CLOAKBROWSER

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
ROOT = Path(__file__).resolve().parent
stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
OUT = ROOT / 'notion-captures' / ('run3-questionnaire-' + stamp)
OUT.mkdir(parents=True)
for folder in ['00-session', '01-requests', '02-bodies', '03-screenshots', '04-storage']:
    (OUT / folder).mkdir()

def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')

def log(kind, **data):
    with (OUT / '01-requests' / 'events.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps({'utc': datetime.now(timezone.utc).isoformat(), 'kind': kind, **data}, ensure_ascii=False) + '\n')

print('CAPTURE_DIR=' + str(OUT), flush=True)
proxy_url = None
exit_ip = None
# Skip the proxy used by the earlier test. Credentials stay in the source list.
lines = (ROOT / 'proxies.txt').read_text(encoding='utf-8-sig').splitlines()
for line in lines[1:7]:
    try:
        host, port, user, password = line.strip().split(':', 3)
        candidate = httpx.URL('http://' + host + ':' + port, username=user, password=password)
        with httpx.Client(proxy=str(candidate), timeout=18) as client:
            response = client.get('https://api.ipify.org?format=json')
            response.raise_for_status()
            ip = response.json()['ip']
        if ip == '<ip>':
            continue
        proxy_url = str(candidate)
        exit_ip = ip
        break
    except Exception as exc:
        print('PROXY_TEST_FAILED=' + type(exc).__name__, flush=True)
if not proxy_url:
    raise RuntimeError('No new working proxy found; no direct connection fallback.')
seed = secrets.randbelow(900000000) + 100000000
save(OUT / '00-session' / 'environment.json', {
    'createdUtc': datetime.now(timezone.utc).isoformat(), 'browser': 'CloakBrowser',
    'fingerprintSeed': seed, 'verifiedProxyExitIp': exit_ip,
    'previousTestExitIp': '<ip>', 'freshBrowserProcess': True,
    'freshContext': True, 'proxyCredentialsSaved': False,
    'purpose': 'Manual signup: questionnaire choices and trial offer display. No checkout confirmation.',
})
print('NEW_PROXY_EXIT_IP=' + exit_ip, flush=True)
browser = launch(headless=False, humanize=False, proxy=proxy_url,
                 args=[f'--fingerprint={seed}'])
context = browser.new_context(record_har_path=str(OUT / 'full-network.har'),
    record_har_content='embed', record_har_mode='full', viewport=None)
context.tracing.start(screenshots=True, snapshots=True, sources=False)
requests = {}
counter = [0]

def attach_request(req):
    counter[0] += 1
    rid = counter[0]
    requests[req] = rid
    try:
        body = req.post_data_buffer
        record = {'id': rid, 'url': req.url, 'method': req.method,
                  'resourceType': req.resource_type, 'headers': req.all_headers(),
                  'postBodyBase64': base64.b64encode(body).decode() if body is not None else None,
                  'postBodyText': body.decode('utf-8', errors='replace') if body is not None else None}
        save(OUT / '01-requests' / f'{rid:06d}-request.json', record)
        log('request', id=rid, url=req.url, method=req.method)
    except Exception as exc:
        log('request_export_error', id=rid, error=str(exc))

def attach_response(resp):
    rid = requests.get(resp.request, 0)
    try:
        save(OUT / '01-requests' / f'{rid:06d}-response.json', {
            'id': rid, 'url': resp.url, 'status': resp.status,
            'headers': resp.all_headers(), 'statusText': resp.status_text})
        log('response', id=rid, url=resp.url, status=resp.status)
    except Exception as exc:
        log('response_export_error', id=rid, error=str(exc))

def finished(req):
    rid = requests.get(req, 0)
    try:
        resp = req.response()
        if resp:
            body = resp.body()
            (OUT / '02-bodies' / f'{rid:06d}-response.bin').write_bytes(body)
            log('body_saved', id=rid, bytes=len(body), sha256=hashlib.sha256(body).hexdigest(), timing=req.timing)
    except Exception as exc:
        log('body_unavailable', id=rid, url=req.url, error=str(exc))

def page_setup(page):
    page.on('console', lambda msg: log('console', level=msg.type, text=msg.text))
    page.on('pageerror', lambda exc: log('pageerror', error=str(exc)))
    page.on('framenavigated', lambda frame: log('navigation', url=frame.url))
    page.on('websocket', websocket_setup)

def websocket_setup(ws):
    log('websocket_open', url=ws.url)
    def frame(kind, payload):
        log(kind, url=ws.url, data=base64.b64encode(payload).decode() if isinstance(payload, bytes) else payload,
            encoding='base64' if isinstance(payload, bytes) else 'text')
    ws.on('framesent', lambda p: frame('ws_sent', p))
    ws.on('framereceived', lambda p: frame('ws_received', p))
    ws.on('socketerror', lambda e: log('ws_error', url=ws.url, error=str(e)))

context.on('request', attach_request)
context.on('response', attach_response)
context.on('requestfinished', finished)
context.on('requestfailed', lambda r: log('request_failed', id=requests.get(r), url=r.url, error=r.failure))
context.on('page', page_setup)
page = context.new_page()
try:
    page.goto('https://api.ipify.org?format=json', wait_until='domcontentloaded', timeout=60000)
    browser_ip = json.loads(page.locator('body').inner_text())['ip']
    if browser_ip != exit_ip:
        raise RuntimeError('Browser proxy verification mismatch')
    log('browser_proxy_verified', exitIp=browser_ip)
    page.goto('https://app.notion.com/signup', wait_until='domcontentloaded', timeout=90000)
    page.screenshot(path=str(OUT / '03-screenshots' / '000-signup-ready.png'))
    print('SIGNUP_READY=' + page.url, flush=True)
    print('RECORDING_ACTIVE; manual registration only. Window remains open until STOP file or browser closure.', flush=True)
    last_snapshot = 0
    while context.pages and not (OUT / 'STOP').exists():
        live = context.pages[-1]
        live.wait_for_timeout(500)
        if time.time() - last_snapshot > 20:
            last_snapshot = time.time()
            save(OUT / '00-session' / 'status.json', {
                'updatedUtc': datetime.now(timezone.utc).isoformat(),
                'state': 'recording', 'requestCount': counter[0],
                'pages': [p.url for p in context.pages], 'proxyExitIp': exit_ip})
            try:
                live.screenshot(path=str(OUT / '03-screenshots' / (datetime.now().strftime('%H%M%S') + '.png')))
            except Exception as exc:
                log('snapshot_error', error=str(exc))
except Exception as exc:
    log('recorder_error', error=str(exc))
    print('RECORDER_ERROR=' + str(exc), flush=True)
finally:
    try:
        context.storage_state(path=str(OUT / '04-storage' / 'final-state.private.json'))
        context.tracing.stop(path=str(OUT / 'playwright-trace.zip'))
    except Exception as exc:
        log('finalize_error', error=str(exc))
    try:
        context.close()
        browser.close()
    except Exception:
        pass
    save(OUT / '00-session' / 'final-summary.json', {'requestCount': counter[0], 'harExists': (OUT / 'full-network.har').exists()})
    print('CAPTURE_FINALIZED=' + str(OUT), flush=True)
