import pathlib, random, re
from curl_cffi import requests as creq
ROOT = pathlib.Path(r"REPO_ROOT"); OUT = ROOT/"research"/"notion"/"captures"/"community"
lines=[l.strip() for l in (ROOT/"proxies.txt").read_text(encoding="utf-8",errors="ignore").splitlines() if l.strip()]
random.seed(31415); h,po,u,pw=random.choice(lines).split(":",3)
PX={"http":f"http://{u}:{pw}@{h}:{po}","https":f"http://{u}:{pw}@{h}:{po}"}
s=creq.Session(impersonate="chrome")
QS=[
 'notion ai "complimentary" how many responses',
 '"notion ai" free plan limit responses reddit',
 'notion ai credits worth it reddit 2026',
 'notion ai usage allowance reached upgrade',
]
for q in QS:
    try:
        r=s.get("https://search.marcia.cc/search",params={"q":q},proxies=PX,timeout=25)
        print("SearXNG",r.status_code,q)
    except Exception as e:
        print("searx err",repr(e)[:50]); break
# 直接用 bing 的 rss/news
for q in QS[:3]:
    try:
        r=s.get("https://www.bing.com/search",params={"q":q,"format":"rss"},proxies=PX,timeout=30)
        print("BING RSS",r.status_code,len(r.text))
        if r.status_code==200:
            for m in re.finditer(r"(?is)<item>.*?</item>",r.text):
                blk=m.group(0)
                t=re.search(r"(?is)<title>(.*?)</title>",blk)
                d=re.search(r"(?is)<description>(.*?)</description>",blk)
                clean=lambda x: re.sub(r"\s+"," ",re.sub(r"<[^>]+>","",x or "")).strip()
                print("   *", clean(t.group(1) if t else "")[:100])
                print("     ", clean(d.group(1) if d else "")[:220])
    except Exception as e: print("bingrss err",repr(e)[:60])
