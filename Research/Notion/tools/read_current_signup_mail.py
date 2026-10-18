"""Read only the selected signup mailbox through the existing loopback viewer."""

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 YG
import json
from pathlib import Path
import sys
from datetime import datetime
import httpx

sys.stdout.reconfigure(encoding='utf-8',errors='replace',line_buffering=True)
root=Path(__file__).resolve().parents[3]
email=sys.argv[1].strip().lower()
run=Path(sys.argv[2])
private=run/'06-mail.private'
private.mkdir(exist_ok=True)
account=None
for filename in ['Outlook_37_Account.txt','Hotmail_37_Account.txt']:
    path=root/filename
    if not path.exists(): continue
    with path.open(encoding='utf-8-sig') as stream:
        for line in stream:
            if line.split('----',1)[0].strip().lower()==email:
                account=line.strip(); break
    if account: break
if account is None:
    print('CURRENT_ACCOUNT_NOT_FOUND');sys.exit(2)
parts=account.split('----')
print('CURRENT_ACCOUNT_FOUND='+email+'; fields='+str(len(parts)))
with httpx.Client(base_url='http://127.0.0.1:8787',timeout=45,trust_env=False) as client:
    health=client.get('/api/v1/health');health.raise_for_status()
    response=client.post('/api/v1/session',json={'accounts':account,'junkWatching':True,'graphOnly':True})
    response.raise_for_status()
    data=response.json()
    if not data.get('ok'):
        print('LOCAL_IMPORT_FAILED='+str(data.get('error',{}).get('code')));sys.exit(3)
    session=data['data']['sessionToken']
    (private/'local-session.private.json').write_text(json.dumps({'email':email,'sessionToken':session}),encoding='utf-8')
    headers={'Authorization':'Bearer '+session}
    report={'email':email,'checkedAt':datetime.now().astimezone().isoformat(),'folders':{}}
    for folder in ['INBOX','Junk']:
        try:
            response=client.post('/api/v1/refresh',headers=headers,json={'email':email,'folder':folder})
            result=response.json()
            (private/(folder.lower()+'-response.private.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            if result.get('ok'):
                messages=result.get('data') or []
                selected=[m for m in messages if 'notion' in (str(m.get('from',''))+' '+str(m.get('subject',''))).lower()]
                report['folders'][folder]={'ok':True,'messageCount':len(messages),'notionMessageCount':len(selected),'notionMessages':[{'receivedAt':m.get('receivedAt'),'hasCode':bool(m.get('code'))} for m in selected]}
                print(folder+'='+json.dumps(report['folders'][folder],ensure_ascii=False))
            else:
                error=result.get('error',{})
                report['folders'][folder]={'ok':False,'code':error.get('code'),'message':error.get('message')}
                print(folder+'='+json.dumps(report['folders'][folder],ensure_ascii=False))
        except Exception as exc:
            report['folders'][folder]={'ok':False,'errorType':type(exc).__name__}
            print(folder+'_ERROR='+type(exc).__name__)
    (private/'mail-check-summary.private.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('MAIL_CHECK_DONE')
