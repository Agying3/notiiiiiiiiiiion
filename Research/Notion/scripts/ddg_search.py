import json, pathlib, random, re, time, urllib.parse
from curl_cffi import requests as creq
ROOT = pathlib.Path(r"REPO_ROOT")
OUT = ROOT/"research"/"notion"/"captures"/"community"; OUT.mkdir(parents=True, exist_ok=True)
lines=[l.strip() for l in (ROOT/"proxies.txt").read_text(encoding="utf-8",errors="ignore").splitlines() if l.strip()]
random.seed(8080); h,p_,u,pw=random.choice(lines).split(":",3)
PROXY={"http":f"http://{u}:{pw}@{h}:{p_}","https":f"http://{u}:{pw}@{h}:{p_}"}
s=creq.Session(impersonate="chrome")
H={"Accept":"application/json, text/plain, */*","Accept-Language":"en-US,en;q=0.9"}
# DuckDuckGo html 版
for q in ["notion ai complimentary responses limit",
          "site:reddit.com notion ai free plan limit",
          "notion ai credits how far do they go"]:
    try:
        r=s.post("https://html.duckduckgo.com/html/",data={"q":q},proxies=PROXY,headers=H,timeout=40)
        print("== DDG",q,r.status_code,len(r.text))
        if r.status_code==200:
            for m in re.finditer(r'(?is)result__a[^>]*>(.*?)</a>', r.text):
                t=re.sub(r"<[^>]+>","",m.group(1)).strip()
                if t: print("   *",t[:110])
            for m in re.finditer(r'(?is)result__snippet[^>]*>(.*?)</a>', r.text):
                t=re.sub(r"<[^>]+>","",m.group(1)).strip()
                if t: print("     -",t[:200])
    except Exception as e: print("DDG ERR",repr(e)[:90])
    time.sleep(1)
