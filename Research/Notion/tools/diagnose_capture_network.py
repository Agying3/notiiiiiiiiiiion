"""Read-only sidecar checks. Never attaches to or changes the active capture session."""

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 tujue
import json
from datetime import datetime
from pathlib import Path
import sys
import httpx
from browser_launch import launch_persistent_context, HAVE_CLOAKBROWSER
from capture_identity import used_hosts_and_ips, reserve_identity, fingerprint_seed

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
root = Path(__file__).resolve().parents[3]
out = root / 'Research/Notion/captures/manual' / ('network-diagnostic-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
out.mkdir(parents=True)
used = used_hosts_and_ips(root)
sdk = 'https://js.hcaptcha.com/1/api.js?render=explicit&onload=__hcaptchaOnLoad'
proxy = None
for index, line in enumerate((root / 'proxies.txt').read_text(encoding='utf-8-sig').splitlines(), 1):
    if not line.strip():
        continue
    host, port, user, password = line.strip().split(':', 3)
    if host in used:
        continue
    try:
        candidate = str(httpx.URL('http://' + host + ':' + port, username=user, password=password))
        with httpx.Client(proxy=candidate, timeout=15) as client:
            ip_response = client.get('https://api.ipify.org?format=json')
            ip_response.raise_for_status()
            ip = ip_response.json()['ip']
            if ip in used:
                continue
            sdk_response = client.get(sdk)
            http_status = sdk_response.status_code
        proxy = candidate
        break
    except Exception as exc:
        print('PREFLIGHT_ERROR=' + type(exc).__name__)
if proxy is None:
    raise RuntimeError('No fresh diagnostic proxy available')
reserve_identity(root, host, port, ip, index, out.name)
seed = fingerprint_seed(index, host, port)
result = {'scope': 'Isolated read-only GET tests; active registration capture untouched',
          'proxyExitIp': ip, 'fingerprintSeed': seed, 'httpxSdkStatus': http_status, 'tests': []}
print('DIAGNOSTIC_DIR=' + str(out))
print('DIAGNOSTIC_IP=' + ip)
for name, flags in [('baseline', []), ('transport-compatibility', ['--disable-quic', '--disable-features=EncryptedClientHello'])]:
    context = None
    item = {'name': name, 'flags': flags}
    try:
        context = launch_persistent_context(str(out / (name + '-profile.private')),
            headless=True, proxy=proxy, args=[f'--fingerprint={seed}', *flags,
            '--log-net-log=' + str(out / (name + '-netlog.private.json'))])
        page = context.new_page()
        page.on('requestfailed', lambda request: print('DIAGNOSTIC_REQUEST_FAILED=' + request.failure))
        r = page.goto(sdk, wait_until='domcontentloaded', timeout=25000)
        item['status'] = r.status if r else None
        item['url'] = page.url
        item['bodyLength'] = len(r.body()) if r else 0
    except Exception as exc:
        item['error'] = str(exc)
    finally:
        if context:
            try:
                context.close()
            except Exception:
                pass
    result['tests'].append(item)
    (out / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(item, ensure_ascii=False))
print('READ_ONLY_DIAGNOSTICS_DONE')
