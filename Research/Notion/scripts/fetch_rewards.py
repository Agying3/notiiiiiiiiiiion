import pathlib, random, re
from curl_cffi import requests as creq
ROOT = pathlib.Path(r"REPO_ROOT"); OUT=ROOT/"research"/"notion"/"captures"/"web"
lines=[l.strip() for l in (ROOT/"proxies.txt").read_text(encoding="utf-8",errors="ignore").splitlines() if l.strip()]
random.seed(555); h,p_,u,pw=random.choice(lines).split(":",3)
PROXY={"http":f"http://{u}:{pw}@{h}:{p_}","https":f"http://{u}:{pw}@{h}:{p_}"}
s=creq.Session(impersonate="chrome")
for name,url in {
 "startups-page":"https://www.notion.com/startups",
 "students":"https://www.notion.com/product/students",
 "edu":"https://www.notion.com/help/notion-for-education",
 "referral":"https://www.notion.com/help/notion-credits-referral",
}.items():
    try:
        r=s.get(url,proxies=PROXY,timeout=35)
        b=re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>"," ",r.text)
        b=re.sub(r"(?s)<[^>]+>"," ",b); b=re.sub(r"\s+"," ",b)
        (OUT/f"{name}.txt").write_text(b,encoding="utf-8",errors="ignore")
        print(f"## {name} {r.status_code} len={len(b)}")
        for m in re.finditer(r".{80}(free|credit|month|\$\d|student|startup|reward).{140}", b, re.I):
            print("   >", m.group(0).strip()[:200])
    except Exception as e: print(name,"ERR",repr(e)[:70])
