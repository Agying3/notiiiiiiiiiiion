"""Identity bookkeeping for repeatable manual capture runs; no proxy passwords saved here."""

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 tujue
import hashlib
import json
from pathlib import Path


def host_from_legacy(line):
    return line.strip().split('|', 1)[0].split(':', 1)[0]


def fingerprint_seed(proxy_index, host, port):
    key = f'notion-manual:{proxy_index}:{host}:{port}'.encode()
    return 100000000 + int(hashlib.sha256(key).hexdigest()[:12], 16) % 900000000


def used_hosts_and_ips(root):
    # Earlier sessions predate the registry. Explicitly include both observed exits.
    used: set[str] = set()
    legacy = root / 'used_proxies.txt'
    if legacy.exists():
        for line in legacy.read_text(encoding='utf-8-sig').splitlines():
            if line.strip():
                used.add(host_from_legacy(line))
                parts = line.split('|')
                if len(parts) >= 3:
                    used.add(parts[2].strip())
    registry = root / 'Research' / 'Notion' / 'local' / 'used-proxies.private.jsonl'
    if registry.exists():
        for line in registry.read_text(encoding='utf-8').splitlines():
            if line.strip():
                item = json.loads(line)
                used.update([item['host'], item['exitIp']])
    return used


def reserve_identity(root, host, port, exit_ip, proxy_index, label):
    registry = root / 'Research' / 'Notion' / 'local' / 'used-proxies.private.jsonl'
    registry.parent.mkdir(parents=True, exist_ok=True)
    with registry.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps({'host': host, 'port': port, 'exitIp': exit_ip,
            'proxyIndex': proxy_index, 'label': label}, ensure_ascii=False) + '\n')
