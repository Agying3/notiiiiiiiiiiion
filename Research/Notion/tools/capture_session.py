"""Manual registration capture, session stays alive until STOP file.
Usage: python capture_session.py <label>
Control (without interrupting): put JSON in 00-session/commands.json, e.g.
  {"action":"mark","note":"questionnaire visible"}
  {"action":"screenshot","name":"quiz"}
  {"action":"reload"}
Commands are consumed automatically; recording never stops between them.
"""
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
from cloakbrowser import launch

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
ROOT = Path(__file__).resolve().parent
LABEL = sys.argv[1] if len(sys.argv) > 1 else 'run'
stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
OUT = ROOT / 'notion-captures' / f'{LABEL}-{stamp}'
OUT.mkdir(parents=True)
for folder in ['00-session', '01-requests', '02-bodies', '03-screenshots', '04-storage']:
    (OUT / folder).mkdir()
SESSION = OUT / '00-session'
USED = ROOT / 'used_proxies.txt'
USED.touch(exist_ok=True)
used_lines = {l.split('|')[0].strip() for l in USED.read_text(encoding='utf-8-sig').splitlines() if l.strip()}

def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')

def log(kind, **data):
    with (OUT / '01-requests' / 'events.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps({'utc': datetime.now(timezone.utc).isoformat(), 'kind': kind, **data}, ensure_ascii=False) + '\n')

print('CAPTURE_DIR=' + str(OUT), flush=True)
lines = (ROOT / 'proxies.txt').read_text(encoding='utf-8-sig').splitlines()
proxy_url = exit_ip = proxy_line = None
for line in lines:
    line = line.strip()
    if not line or line.split(':')[0] in used_lines:
        continue
    try:
        h, p, u, w = line.split(':', 3)
        candidate = str(httpx.URL('http://' + h + ':' + p, username=u, password=w))
        with httpx.Client(proxy=candidate, timeout=18) as client:
            ip = client.get('https://api.ipify.org?format=json').json()['ip']
        proxy_url, exit_ip, proxy_line = candidate, ip, line
        break
    except Exception as exc:
        print('PROXY_SKIP=' + line.split(':')[0] + ' err=' + type(exc).__name__, flush=True)
if not proxy_url:
    raise RuntimeError('no unused working proxy')
USED.open('a', encoding='utf-8').write(f'{proxy_line}|{LABEL}-{stamp}|{exit_ip}\n')
seed = secrets.randbelow(900000000) + 100000000
save(SESSION / 'environment.json', {
    'label': LABEL, 'createdUtc': datetime.now(timezone.utc).isoformat(),
    'browser': 'CloakBrowser', 'fingerprintSeed': seed, 'proxyExitIp': exit_ip,
    'freshProcess': True, 'purpose': 'Manual registration A/B: option choice vs trial offer. No checkout.',
})
print('PROXY_EXIT_IP=' + exit_ip, flush=True)
print('FINGERPRINT_SEED=' + str(seed), flush=True)
browser = launch(headless=False, humanize=False, proxy=proxy_url, args=[f'--fingerprint={seed}'])
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
        save(OUT / '01-requests' / f'{rid:06d}-request.json', {
            'id': rid, 'url': req.url, 'method': req.method,
            'resourceType': req.resource_type, 'headers': req.all_headers(),
            'postBodyBase64': base64.b64encode(body).decode() if body is not None else None,
            'postBodyText': body.decode('utf-8', errors='replace') if body is not None else None})
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
            log('body_saved', id=rid, bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
    except Exception as exc:
        log('body_unavailable', id=rid, url=req.url, error=str(exc))

def page_setup(page):
    page.on('console', lambda msg: log('console', level=msg.type, text=msg.text[:500]))
    page.on('pageerror', lambda exc: log('pageerror', error=str(exc)[:500]))
    page.on('framenavigated', lambda frame: log('navigation', url=frame.url))

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
    page.goto('https://app.notion.com/signup', wait_until='domcontentloaded', timeout=90000)
    page.screenshot(path=str(OUT / '03-screenshots' / '000-signup-ready.png'))
    log('session_event', note='signup page ready; recorder stays alive until STOP file')
    print('SIGNUP_READY=' + page.url, flush=True)
    last_shot = 0
    while context.pages and not (SESSION / 'STOP').exists():
        live = context.pages[-1]
        live.wait_for_timeout(400)
        cmd_path = SESSION / 'commands.json'
        if cmd_path.exists():
            try:
                cmd = json.loads(cmd_path.read_text(encoding='utf-8'))
                cmd_path.unlink()
                action = cmd.get('action')
                if action == 'mark':
                    log('mark', note=cmd.get('note', ''))
                    live.screenshot(path=str(OUT / '03-screenshots' / ('mark-' + datetime.now().strftime('%H%M%S') + '.png')))
                elif action == 'screenshot':
                    live.screenshot(path=str(OUT / '03-screenshots' / ((cmd.get('name') or 'shot') + '-' + datetime.now().strftime('%H%M%S') + '.png')))
                elif action == 'reload':
                    live.reload(wait_until='domcontentloaded')
                    log('session_event', note='reloaded by command')
                log('command_done', **cmd)
            except Exception as exc:
                log('command_error', error=str(exc))
        if time.time() - last_shot > 20:
            last_shot = time.time()
            save(SESSION / 'status.json', {'updatedUtc': datetime.now(timezone.utc).isoformat(),
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
        context.close(); browser.close()
    except Exception:
        pass
    save(SESSION / 'final-summary.json', {'requestCount': counter[0], 'harExists': (OUT / 'full-network.har').exists()})
    print('CAPTURE_FINALIZED=' + str(OUT), flush=True)
