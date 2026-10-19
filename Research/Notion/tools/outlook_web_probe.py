"""Read an Outlook.com mailbox through the real web UI (fallback when Graph is doubted).

Uses a plain Edge window attached over CDP so the session is a normal browser
session, then prints the newest messages. Credentials come from the local pool
file and are never printed.
"""

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 tujue
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import human_verification as bridge

ROOT = Path(__file__).resolve().parents[3]


def account(email_prefix: str) -> tuple[str, str]:
    for name in ('Hotmail_37_Account.txt', 'Outlook_37_Account.txt'):
        path = ROOT / name
        if not path.exists():
            continue
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            fields = [x.strip() for x in line.split('----')]
            if len(fields) >= 4 and fields[0].lower().startswith(email_prefix.lower()):
                return fields[0], fields[1]
    raise SystemExit('ACCOUNT_NOT_FOUND')


def read_inbox(prefix: str, headless_timeout: int = 120) -> list[dict]:
    email, password = account(prefix)
    profile = ROOT / 'Research/Notion/local/manual-browser/web-probe-profile'
    port = 9412
    process = bridge.launch_plain_edge(profile, port, None)
    driver = None
    messages: list[dict] = []
    try:
        from playwright.sync_api import sync_playwright
        driver = sync_playwright().start()
        browser = bridge.connect_plain_edge(driver, port, timeout=30)
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()
        from urllib.parse import quote
        login_url = ('https://login.live.com/login.srf?wa=wsignin1.0&rpsnv=13&rver=7.5.6737.0'
                     '&wp=MBI_SSL&wreply=' + quote('https://outlook.live.com/owa/', safe='')
                     + '&id=292841&CBCXT=out&lw=1&fl=dob%2Cflname%2Cwld&c1=condition'
                     '&username=' + quote(email, safe=''))
        page.goto(login_url, wait_until='domcontentloaded', timeout=60000)
        time.sleep(3)
        print('LOGIN_URL=' + page.url[:100], flush=True)
        print('HAS_EMAIL_INPUT=' + str(page.locator('input[name="loginfmt"], input[type="email"]').count()), flush=True)
        print('HAS_PASSWORD_INPUT=' + str(page.locator('input[name="passwd"], input[type="password"]').count()), flush=True)
        # Email step
        try:
            box = page.locator('input[name="loginfmt"], input[type="email"]').first
            box.wait_for(state='visible', timeout=30000)
            box.fill(email)
            print('EMAIL_FILLED', flush=True)
            box.press('Enter')
            print('EMAIL_SUBMITTED', flush=True)
        except Exception as exc:
            print('EMAIL_STEP=' + type(exc).__name__, flush=True)
        time.sleep(3)
        # Password step
        try:
            pw = page.locator('input[name="passwd"], input[type="password"]').first
            pw.wait_for(state='visible', timeout=30000)
            pw.fill(password)
            print('PASSWORD_FILLED', flush=True)
            pw.press('Enter')
            print('PASSWORD_SUBMITTED', flush=True)
        except Exception as exc:
            print('PASSWORD_STEP=' + type(exc).__name__, flush=True)
        time.sleep(5)
        # Optional "stay signed in"
        for label in ('否', 'No', 'No, sign me out'):
            try:
                page.get_by_role('button', name=label, exact=True).first.click(timeout=4000)
                break
            except Exception:
                continue
        page.wait_for_timeout(8000)
        if 'outlook.live.com' not in page.url:
            page.goto('https://outlook.live.com/mail/0/', wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(8000)
        print('URL=' + page.url, flush=True)
        print('TITLE=' + page.title()[:80], flush=True)
        body = page.inner_text('body')
        Path(ROOT / 'Research/Notion/local/manual-browser/last-inbox.txt').write_text(
            body, encoding='utf-8')
        for line in body.splitlines():
            text = line.strip()
            if not text:
                continue
            low = text.lower()
            if 'notion' in low or '验证码' in text or 'code' in low:
                messages.append({'line': text[:120]})
        return messages
    finally:
        try:
            if driver is not None:
                driver.stop()
        except Exception:
            pass
        try:
            process.terminate()
            process.wait(timeout=10)
        except Exception:
            pass


if __name__ == '__main__':
    prefix = sys.argv[1] if len(sys.argv) > 1 else 'lk'
    found = read_inbox(prefix)
    print('MATCHES=' + json.dumps(found, ensure_ascii=False), flush=True)
