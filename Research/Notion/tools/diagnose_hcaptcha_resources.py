"""Read-only same-proxy resource diagnosis in a separate browser profile. No registration POSTs."""

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 YG
import json
from datetime import datetime
from pathlib import Path
import sys
import httpx
from cloakbrowser import launch_persistent_context
from capture_identity import fingerprint_seed

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
root=Path(__file__).resolve().parents[3]
host_arg=sys.argv[1]
out=root/'Research/Notion/captures/manual'/('hcaptcha-resources-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
out.mkdir(parents=True)
for index,line in enumerate((root/'proxies.txt').read_text(encoding='utf-8-sig').splitlines(),1):
    if line.startswith(host_arg+':'):
        host,port,user,password=line.strip().split(':',3)
        break
else:
    raise RuntimeError('Proxy not found')
proxy=str(httpx.URL('http://'+host+':'+port,username=user,password=password))
urls={
 'sdk':'https://js.hcaptcha.com/1/api.js?render=explicit&onload=__hcaptchaOnLoad',
 'iframe':'https://newassets.hcaptcha.com/captcha/v1/86591f996c36877668d253e353e36fac021db33b/static/hcaptcha.html',
 'logo':'https://325a7fb9f068.w.hcaptcha.com/logo.png'}
result={'proxyHost':host,'note':'Separate profile, same proxy as active capture; no active-page actions and no registration requests','httpx':{},'browser':{}}
print('DIAGNOSTIC_DIR='+str(out))
with httpx.Client(proxy=proxy,timeout=15,headers={'Referer':'https://app.notion.com/'}) as client:
    for name,url in urls.items():
        try:
            r=client.get(url)
            result['httpx'][name]={'status':r.status_code,'length':len(r.content)}
        except Exception as exc:
            result['httpx'][name]={'error':type(exc).__name__+': '+str(exc)}
print('HTTPX='+json.dumps(result['httpx']))
context=None
try:
    context=launch_persistent_context(str(out/'profile.private'),headless=True,proxy=proxy,
      args=[f'--fingerprint={fingerprint_seed(index,host,port)}','--log-net-log='+str(out/'netlog.private.json')])
    for name,url in urls.items():
        page=context.new_page()
        try:
            r=page.goto(url,wait_until='domcontentloaded',timeout=20000)
            result['browser'][name]={'status':r.status if r else None}
        except Exception as exc:
            result['browser'][name]={'error':str(exc).split('Call log:')[0].strip()}
        finally:
            page.close()
        print('BROWSER_'+name+'='+json.dumps(result['browser'][name]))
    page=context.new_page()
    try:
        page.goto('https://app.notion.com/signup',wait_until='domcontentloaded',timeout=30000)
        result['embeddedSdk']=page.evaluate('''url => new Promise(resolve => {
            const s=document.createElement('script'); s.src=url;
            const timer=setTimeout(()=>resolve('timeout'),15000);
            s.onload=()=>{clearTimeout(timer);resolve('loaded')};
            s.onerror=()=>{clearTimeout(timer);resolve('failed')};
            document.head.appendChild(s);
        })''',urls['sdk'])
    except Exception as exc:
        result['embeddedSdk']={'error':str(exc).split('Call log:')[0].strip()}
    print('EMBEDDED_SDK='+json.dumps(result.get('embeddedSdk')))
finally:
    if context:
        try: context.close()
        except Exception: pass
    (out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('DIAGNOSTIC_DONE')
