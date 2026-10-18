import pathlib, random, re, json
from curl_cffi import requests as creq
ROOT = pathlib.Path(r"REPO_ROOT"); OUT = ROOT/"research"/"notion"/"captures"/"community"
lines=[l.strip() for l in (ROOT/"proxies.txt").read_text(encoding="utf-8",errors="ignore").splitlines() if l.strip()]
random.seed(2026); h,po,u,pw=random.choice(lines).split(":",3)
PX={"http":f"http://{u}:{pw}@{h}:{po}","https":f"http://{u}:{pw}@{h}:{po}"}
s=creq.Session(impersonate="chrome")
# redlib 公共实例
for host in ["redlib.catsarch.com","safereddit.com","redlib.perennialte.ch","l.opnxng.com","redlib.privacyredirect.com"]:
    url=f"https://{host}/r/Notion/search?q=AI+limit&restrict_sr=on&sort=relevance&t=year"
    try:
        r=s.get(url,proxies=PX,timeout=25)
        print(host, r.status_code, len(r.text))
        if r.status_code==200 and len(r.text)>3000:
            b=re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>"," ",r.text)
            b=re.sub(r"(?s)<[^>]+>"," ",b); b=re.sub(r"\s+"," ",b)
            (OUT/f"redlib-{host.split('.')[0]}.txt").write_text(b,encoding="utf-8")
            print("  TEXT:", b[:800])
            break
    except Exception as e:
        print(host,"ERR",repr(e)[:70])
# Notion 官方社区（forum）
for url in ["https://community.notion.so/search?q=AI%20limit","https://community.notion.so/"]:
    try:
        r=s.get(url,proxies=PX,timeout=30)
        print("community", r.status_code, len(r.text), url)
    except Exception as e: print("community ERR",repr(e)[:60])
