import pathlib, random, re
from curl_cffi import requests as creq
ROOT=pathlib.Path(r"REPO_ROOT"); OUT=ROOT/"research"/"notion"/"captures"/"web"
lines=[l.strip() for l in (ROOT/"proxies.txt").read_text(encoding="utf-8",errors="ignore").splitlines() if l.strip()]
random.seed(8888); h,po,u,pw=random.choice(lines).split(":",3)
PX={"http":f"http://{u}:{pw}@{h}:{po}","https":f"http://{u}:{pw}@{h}:{po}"}
s=creq.Session(impersonate="chrome")
for name,url in {
 "trial-help":"https://www.notion.com/help/trial",
 "start-trial":"https://www.notion.com/help/start-a-trial",
 "business-plan-trial":"https://www.notion.com/help/business-plan-trial",
 "understanding-block-usage":"https://www.notion.com/help/understanding-block-usage",
 "billing":"https://www.notion.com/help/billing",
}.items():
    try:
        r=s.get(url,proxies=PX,timeout=30)
        b=re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>"," ",r.text)
        b=re.sub(r"(?s)<[^>]+>"," ",b); b=re.sub(r"\s+"," ",b)
        (OUT/f"{name}.txt").write_text(b,encoding="utf-8",errors="ignore")
        print(f"{name:28s} {r.status_code} len={len(b)}")
    except Exception as e: print(name,"ERR",repr(e)[:70])
