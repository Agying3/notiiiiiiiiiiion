import pathlib, random, re
from curl_cffi import requests as creq
ROOT=pathlib.Path(r"REPO_ROOT"); OUT=ROOT/"research"/"notion"/"captures"/"web"
lines=[l.strip() for l in (ROOT/"proxies.txt").read_text(encoding="utf-8",errors="ignore").splitlines() if l.strip()]
random.seed(2468); h,po,u,pw=random.choice(lines).split(":",3)
PX={"http":f"http://{u}:{pw}@{h}:{po}","https":f"http://{u}:{pw}@{h}:{po}"}
s=creq.Session(impersonate="chrome")
urls={
 "terms-post-trial":"https://notion.notion.site/Notion-s-Promotional-Offer-for-Business-Plan-Discount-27eefdeead05804ea4adff45330b86e9",
 "terms-business-30":"https://notion.notion.site/Notion-s-Promotional-Offers-for-Business-Plan-30cefdeead058070810bc31431b8e59d",
 "terms-edu-biz":"https://notion.notion.site/Notion-s-Education-Plan-Offer-for-Business-Plan-b1fe0de345ac4331b23b11c5ce0df62f",
}
for n,url in urls.items():
    try:
        r=s.get(url,proxies=PX,timeout=35)
        b=re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>"," ",r.text)
        b=re.sub(r"(?s)<[^>]+>"," ",b); b=re.sub(r"\s+"," ",b)
        (OUT/f"{n}.txt").write_text(b,encoding="utf-8",errors="ignore")
        print(f"## {n} {r.status_code} len={len(b)}")
        for m in re.finditer(r".{80}(trial|day|eligible|one per|workspace).{170}", b, re.I):
            print("   >", m.group(0).strip()[:250])
    except Exception as e: print(n,"ERR",repr(e)[:70])
