"""Compare online viewer inbox with local result for the current signup mailbox."""

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 tujue
import json
import sys
import time
from datetime import datetime
from pathlib import Path
import httpx

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
root=Path(__file__).resolve().parents[3]
email=sys.argv[1].strip().lower()
max_seconds=int(sys.argv[2]) if len(sys.argv)>2 else 180
base='https://wr-imap.cheapemail.cc'
account=None
for filename in ['Outlook_37_Account.txt','Hotmail_37_Account.txt']:
    path=root/filename
    if not path.exists(): continue
    for line in path.open(encoding='utf-8-sig'):
        if line.split('----',1)[0].strip().lower()==email:
            account=line.strip(); break
    if account: break
if account is None:
    print('CURRENT_ACCOUNT_NOT_FOUND'); sys.exit(2)
out=root/'Research/Notion/captures/manual/online-mail-check.private'
out.mkdir(parents=True,exist_ok=True)
with httpx.Client(base_url=base,timeout=60,trust_env=False) as client:
    response=client.post('/api/v1/session',json={'accounts':account,'junkWatching':True,'graphOnly':True})
    response.raise_for_status()
    data=response.json()
    if not data.get('ok'):
        print('ONLINE_IMPORT_FAILED='+json.dumps(data.get('error',{}),ensure_ascii=False)); sys.exit(3)
    session=data['data']['sessionToken']
    headers={'Authorization':'Bearer '+session}
    print('ONLINE_SESSION_OK accounts='+str(data['data']['bootstrap'].get('accountCount')))
    deadline=time.time()+max_seconds
    found=None
    attempt=0
    while time.time()<deadline:
        attempt+=1
        for folder in ['INBOX','Junk']:
            try:
                result=client.post('/api/v1/refresh',headers=headers,json={'email':email,'folder':folder}).json()
                (out/(folder.lower()+'-latest.private.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
                messages=(result.get('data') or []) if result.get('ok') else []
                print(f'ATTEMPT={attempt} FOLDER={folder} MESSAGES={len(messages)} LATEST=' + (messages[0].get('receivedAt','') if messages else ''))
                for message in messages:
                    if 'notion' in (str(message.get('from',''))+' '+str(message.get('subject',''))).lower() and message.get('code'):
                        found={'folder':folder,'receivedAt':message.get('receivedAt'),'code':message['code'],'subject':message.get('subject')}
                        break
                if found: break
            except Exception as exc:
                print(f'ONLINE_POLL_ERROR attempt={attempt} folder={folder} type={type(exc).__name__}')
        if found: break
        time.sleep(12)
    try:
        client.post('/api/v1/session/end',json={'sessionToken':session})
    except Exception:
        pass
if found:
    (out/'notion-code.private.json').write_text(json.dumps({'email':email,**found},ensure_ascii=False,indent=2),encoding='utf-8')
    print('ONLINE_CODE_FOUND folder='+found['folder']+' receivedAt='+str(found['receivedAt']))
else:
    print('ONLINE_CODE_NOT_FOUND')
