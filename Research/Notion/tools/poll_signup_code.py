"""Poll only the current signup mailbox for a fresh Notion code and store it privately."""

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
run=Path(sys.argv[2])
max_seconds=int(sys.argv[3]) if len(sys.argv)>3 else 150
private=run/'06-mail.private'
private.mkdir(exist_ok=True)
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
started=datetime.now().astimezone().isoformat()
found=None
with httpx.Client(base_url='http://127.0.0.1:8787',timeout=45,trust_env=False) as client:
    response=client.post('/api/v1/session',json={'accounts':account,'junkWatching':True,'graphOnly':True})
    response.raise_for_status()
    data=response.json()
    if not data.get('ok'):
        print('LOCAL_IMPORT_FAILED='+str(data.get('error',{}).get('code'))); sys.exit(3)
    session=data['data']['sessionToken']
    headers={'Authorization':'Bearer '+session}
    deadline=time.time()+max_seconds
    attempt=0
    while time.time()<deadline and not found:
        attempt+=1
        for folder in ['INBOX','Junk']:
            try:
                result=client.post('/api/v1/refresh',headers=headers,json={'email':email,'folder':folder}).json()
                messages=(result.get('data') or []) if result.get('ok') else []
                for message in messages:
                    received=message.get('receivedAt','')
                    if received>='2026-10-17T17:20:00Z' and 'notion' in (str(message.get('from',''))+' '+str(message.get('subject',''))).lower() and message.get('code'):
                        found={'email':email,'folder':folder,'receivedAt':received,'code':message['code'],
                               'confidence':message.get('confidence'),'subject':message.get('subject'),'foundAt':datetime.now().astimezone().isoformat()}
                        break
                if found: break
            except Exception as exc:
                print(f'POLL_ERROR attempt={attempt} folder={folder} type={type(exc).__name__}',flush=True)
        if not found:
            time.sleep(10)
    try:
        client.post('/api/v1/session/end',json={'sessionToken':session})
    except Exception:
        pass
summary={'email':email,'startedAt':started,'finishedAt':datetime.now().astimezone().isoformat(),'found':bool(found)}
if found:
    (private/'notion-code.private.json').write_text(json.dumps(found,ensure_ascii=False,indent=2),encoding='utf-8')
    print('CODE_FOUND folder='+found['folder']+' receivedAt='+found['receivedAt'])
else:
    print('CODE_NOT_FOUND after '+str(max_seconds)+'s')
