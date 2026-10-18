import pathlib, random, re
from curl_cffi import requests as creq
ROOT = pathlib.Path(r"REPO_ROOT"); OUT = ROOT/"research"/"notion"/"captures"/"web"
lines=[l.strip() for l in (ROOT/"proxies.txt").read_text(encoding="utf-8",errors="ignore").splitlines() if l.strip()]
random.seed(1234); h,p_,u,pw=random.choice(lines).split(":",3)
PROXY={"http":f"http://{u}:{pw}@{h}:{p_}","https":f"http://{u}:{pw}@{h}:{p_}"}
s=creq.Session(impersonate="chrome")
for name,url in {
 "complimentary":"https://www.notion.com/help/complimentary-ai-responses",
 "trial-business":"https://www.notion.com/help/try-notion-business",
 "what-is-notion-ai":"https://www.notion.com/help/what-is-notion-ai",
}.items():
    try:
        r=s.get(url,proxies=PROXY,timeout=35)
        b=re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>"," ",r.text)
        b=re.sub(r"(?s)<[^>]+>"," ",b); b=re.sub(r"\s+"," ",b)
        (OUT/f"{name}.txt").write_text(b,encoding="utf-8",errors="ignore")
        print(f"## {name} {r.status_code} len={len(b)}")
        for m in re.finditer(r".{90}\b(\d{1,3})\b.{110}", b):
            seg=m.group(0)
            if re.search(r"(response|AI|trial|day|credit|block)", seg, re.I):
                print("   >", seg.strip()[:210])
    except Exception as e: print(name,"ERR",repr(e)[:80])
