import pathlib, random
from curl_cffi import requests as creq
ROOT = pathlib.Path(r"REPO_ROOT")
lines=[l.strip() for l in (ROOT/"proxies.txt").read_text(encoding="utf-8",errors="ignore").splitlines() if l.strip()]
random.seed(555)
ok=0; bad=0
for line in random.sample(lines, 12):
    h,po,u,pw=line.split(":",3)
    PX={"http":f"http://{u}:{pw}@{h}:{po}","https":f"http://{u}:{pw}@{h}:{po}"}
    try:
        r=creq.Session(impersonate="chrome").get("https://app.notion.com/api/v3/ping",proxies=PX,timeout=12,
            headers={"Notion-Client-Version":"23.13.20261017.1134","Content-Type":"application/json"})
        print(f"{h}:{po} notion={r.status_code}"); ok+=1
    except Exception as e:
        # 再测一个通用站点判断代理是否整体挂了
        try:
            r2=creq.Session().get("https://api.ipify.org",proxies=PX,timeout=12)
            print(f"{h}:{po} notion=ERR ipify={r2.status_code}")
        except Exception as e2:
            print(f"{h}:{po} 完全不可用 {repr(e2)[:50]}")
        bad+=1
print("ok",ok,"bad",bad)
