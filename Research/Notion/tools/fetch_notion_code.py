"""独立 Notion 验证码收取器 —— 纯 HTTP 直连微软，无浏览器、无第三方依赖。
用法:
  python fetch_notion_code.py <email>            # 轮询收码（默认180秒）
  python fetch_notion_code.py <email> --once     # 只查一次
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import httpx

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
ROOT = Path(__file__).resolve().parents[3]
TOKEN_URL = 'https://login.microsoftonline.com/consumers/oauth2/v2.0/token'
GRAPH = 'https://graph.microsoft.com/v1.0'
CODE_CTX = re.compile(r'(code|验证码|校验码|passcode|otp)', re.I)
CODE_RE = re.compile(r'\b(\d{6})\b')


def load_account(email):
    email = email.strip().lower()
    for filename in ['Outlook_37_Account.txt', 'Hotmail_37_Account.txt']:
        path = ROOT / filename
        if not path.exists():
            continue
        with path.open(encoding='utf-8-sig') as stream:
            for line in stream:
                parts = line.strip().split('----')
                if len(parts) >= 4 and parts[0].strip().lower() == email:
                    return {'email': parts[0], 'client_id': parts[2], 'refresh_token': parts[3]}
    return None


def get_access_token(account):
    """刷新 token。失败时带具体微软错误码返回，便于分辨风控/失效。"""
    body = {
        'client_id': account['client_id'],
        'grant_type': 'refresh_token',
        'refresh_token': account['refresh_token'],
        'scope': 'https://graph.microsoft.com/Mail.Read offline_access',
    }
    with httpx.Client(timeout=20, trust_env=False) as client:
        resp = client.post(TOKEN_URL, data=body)
    if resp.status_code != 200:
        try:
            err = resp.json()
            detail = f"{err.get('error')}:{err.get('error_description', '')[:120]}"
        except Exception:
            detail = resp.text[:120]
        raise RuntimeError(f'TOKEN_REFRESH_FAILED http={resp.status_code} {detail}')
    return resp.json()['access_token']


def list_messages(token, folder='inbox', top=10):
    path = 'mailfolders/inbox/messages' if folder == 'inbox' else 'mailfolders/junkemail/messages'
    url = f'{GRAPH}/me/{path}?$top={top}&$select=subject,receivedDateTime,from,bodyPreview'
    with httpx.Client(timeout=20, trust_env=False) as client:
        resp = client.get(url, headers={'Authorization': f'Bearer {token}'})
    if resp.status_code == 401:
        raise RuntimeError('GRAPH_401_UNAUTHORIZED token 无效或权限不足')
    if resp.status_code == 429:
        raise RuntimeError('GRAPH_429_THROTTLED 微软限流')
    if resp.status_code != 200:
        raise RuntimeError(f'GRAPH_ERROR http={resp.status_code} {resp.text[:120]}')
    return resp.json().get('value', [])


def extract_code(subject, preview):
    text = f'{subject or ""}\n{preview or ""}'
    if not CODE_CTX.search(text):
        return None
    m = CODE_RE.search(text)
    return m.group(1) if m else None


def check_once(account, since_iso):
    """返回 (code, debug_info)。每一步失败都直报原因。"""
    info = {'checkedAt': datetime.now(timezone.utc).isoformat()}
    token = get_access_token(account)
    info['token'] = 'ok'
    result = None
    for folder in ['inbox', 'junk']:
        try:
            messages = list_messages(token, folder)
        except RuntimeError as exc:
            info[folder] = f'error: {exc}'
            continue
        info[folder] = f'{len(messages)} msgs'
        for m in messages:
            received = m.get('receivedDateTime', '')
            if received < since_iso:
                continue
            sender = str((m.get('from') or {}).get('emailAddress', {}).get('address', ''))
            if 'notion' not in sender.lower() and 'notion' not in str(m.get('subject', '')).lower():
                continue
            code = extract_code(m.get('subject'), m.get('bodyPreview'))
            if code:
                result = {'email': account['email'], 'folder': folder, 'receivedAt': received,
                          'code': code, 'subject': m.get('subject')}
                break
        if result:
            break
    info['result'] = 'found' if result else 'no_match'
    return result, info


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('email')
    parser.add_argument('--once', action='store_true', help='只查一次不轮询')
    parser.add_argument('--wait', type=int, default=180, help='轮询秒数')
    parser.add_argument('--since', default=None, help='只看此 ISO 时间后的邮件，默认当前时间减5分钟')
    args = parser.parse_args()

    account = load_account(args.email)
    if not account:
        print('ERROR=ACCOUNT_NOT_FOUND 账号不在本地文件中')
        sys.exit(2)

    since = args.since or datetime.now(timezone.utc).isoformat(timespec='seconds')
    print(f'POLLING email={account["email"]} since={since} mode={"once" if args.once else str(args.wait) + "s"}', flush=True)

    deadline = time.time() + (1 if args.once else args.wait)
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            result, info = check_once(account, since)
            print(f'ATTEMPT={attempt} ' + json.dumps(info, ensure_ascii=False), flush=True)
            if result:
                out = ROOT / 'Research/Notion/captures/manual/latest-code.private.json'
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
                print('CODE_FOUND=' + result['code'])
                print('CODE_SAVED=' + str(out))
                sys.exit(0)
        except RuntimeError as exc:
            print(f'ATTEMPT={attempt} FATAL={exc}', flush=True)
            sys.exit(3)
        if not args.once:
            time.sleep(10)
    print('CODE_NOT_FOUND 轮询结束无新验证码')
    sys.exit(1)


if __name__ == '__main__':
    main()
